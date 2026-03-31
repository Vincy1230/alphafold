# Copyright 2021 DeepMind Technologies Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AlphaFold 完整蛋白质结构预测脚本。"""
import enum
import json
import os
import pathlib
import pickle
import random
import shutil
import sys
import time
from typing import Any, Dict, Union

from absl import app
from absl import flags
from absl import logging
from alphafold.common import confidence
from alphafold.common import protein
from alphafold.common import residue_constants
from alphafold.data import pipeline
from alphafold.data import pipeline_multimer
from alphafold.data import templates
from alphafold.data.tools import hhsearch
from alphafold.data.tools import hmmsearch
from alphafold.model import config
from alphafold.model import data
from alphafold.model import model
from alphafold.relax import relax
import jax.numpy as jnp
import numpy as np

# Internal import (7716).

logging.set_verbosity(logging.INFO)


@enum.unique
class ModelsToRelax(enum.Enum):
  ALL = 0
  BEST = 1
  NONE = 2


flags.DEFINE_list(
    'fasta_paths',
    None,
    'FASTA 文件路径列表，每个文件包含一个将依次进行预测的目标。'
    '如果某个 FASTA 文件包含多条序列，则会按多聚体处理。路径之间请用逗号分隔。'
    '所有 FASTA 路径的基础文件名必须唯一，因为它会用于命名各个预测的输出目录。',
)

flags.DEFINE_string('data_dir', None, '支持数据目录的路径。')
flags.DEFINE_string(
    'output_dir', None, '用于保存结果的目录路径。'
)
flags.DEFINE_string(
    'jackhmmer_binary_path',
    shutil.which('jackhmmer'),
    'JackHMMER 可执行文件的路径。',
)
flags.DEFINE_string(
    'hhblits_binary_path',
    shutil.which('hhblits'),
    'HHblits 可执行文件的路径。',
)
flags.DEFINE_string(
    'hhsearch_binary_path',
    shutil.which('hhsearch'),
    'HHsearch 可执行文件的路径。',
)
flags.DEFINE_string(
    'hmmsearch_binary_path',
    shutil.which('hmmsearch'),
    'hmmsearch 可执行文件的路径。',
)
flags.DEFINE_string(
    'hmmbuild_binary_path',
    shutil.which('hmmbuild'),
    'hmmbuild 可执行文件的路径。',
)
flags.DEFINE_string(
    'kalign_binary_path',
    shutil.which('kalign'),
    'Kalign 可执行文件的路径。',
)
flags.DEFINE_string(
    'uniref90_database_path',
    None,
    '供 JackHMMER 使用的 UniRef90 数据库路径。',
)
flags.DEFINE_string(
    'mgnify_database_path',
    None,
    '供 JackHMMER 使用的 MGnify 数据库路径。',
)
flags.DEFINE_string(
    'bfd_database_path', None, '供 HHblits 使用的 BFD 数据库路径。'
)
flags.DEFINE_string(
    'small_bfd_database_path',
    None,
    '与 "reduced_dbs" 预设配套使用的小型 BFD 数据库路径。',
)
flags.DEFINE_string(
    'uniref30_database_path',
    None,
    '供 HHblits 使用的 UniRef30 数据库路径。',
)
flags.DEFINE_string(
    'uniprot_database_path',
    None,
    '供 JackHMMER 使用的 UniProt 数据库路径。',
)
flags.DEFINE_string(
    'pdb70_database_path',
    None,
    '供 HHsearch 使用的 PDB70 数据库路径。',
)
flags.DEFINE_string(
    'pdb_seqres_database_path',
    None,
    '供 hmmsearch 使用的 PDB seqres 数据库文件完整路径'
    '（不是仅目录路径）。',
)
flags.DEFINE_string(
    'template_mmcif_dir',
    None,
    '模板 mmCIF 结构所在目录的路径，'
    '其中每个文件名形如 <pdb_id>.cif',
)
flags.DEFINE_string(
    'max_template_date',
    None,
    '纳入考虑的模板最大发布日期。'
    '在预测历史测试集时尤其重要。',
)
flags.DEFINE_string(
    'obsolete_pdbs_path',
    None,
    '包含已废弃 PDB ID 到其替代 PDB ID 映射关系文件的路径。',
)
flags.DEFINE_enum(
    'db_preset',
    'full_dbs',
    ['full_dbs', 'reduced_dbs'],
    '选择预设的 MSA 数据库配置：'
    '较小的遗传数据库配置（reduced_dbs）或'
    '完整的遗传数据库配置（full_dbs）',
)
flags.DEFINE_enum(
    'model_preset',
    'monomer',
    ['monomer', 'monomer_casp14', 'monomer_ptm', 'multimer'],
    '选择预设模型配置：单体模型、'
    '带额外集成的单体模型、带 pTM 头的单体模型，'
    '或多聚体模型',
)
flags.DEFINE_boolean(
    'benchmark',
    False,
    '多次运行 JAX 模型评估，'
    '以获得不包含编译时间的耗时统计，'
    '从而更能反映批量推理多个蛋白时所需的时间。',
)
flags.DEFINE_integer(
    'random_seed',
    None,
    '数据流水线使用的随机种子。'
    '默认情况下会随机生成。请注意，即使设置了该值，'
    'AlphaFold 仍可能不是确定性的，因为 GPU 推理等过程本身是非确定性的。',
)
flags.DEFINE_integer(
    'num_multimer_predictions_per_model',
    5,
    '每个模型要生成多少次预测'
    '（每次使用不同的随机种子）。例如如果这里设为 2，且有 5 个模型，'
    '那么每个输入会生成 10 个预测结果。'
    '注意：该参数仅在 model_preset=multimer 时生效',
)
flags.DEFINE_boolean(
    'use_precomputed_msas',
    False,
    '是否读取已经写入磁盘的 MSA，'
    '而不是重新运行 MSA 工具。MSA 文件会从输出目录中查找，'
    '因此如果要在多次运行之间复用 MSA，输出目录必须保持不变。'
    '警告：这不会检查序列、数据库或配置是否发生变化。',
)
flags.DEFINE_enum_class(
    'models_to_relax',
    ModelsToRelax.BEST,
    ModelsToRelax,
    '指定哪些模型执行最终弛豫步骤。'
    '如果为 `all`，则所有模型都会弛豫，可能比较耗时。'
    '如果为 `best`，则只弛豫置信度最高的模型。'
    '如果为 `none`，则不执行弛豫。关闭弛豫可能会导致预测结果中出现'
    '较明显的立体化学违规，但在弛豫阶段出现问题时可能有帮助。',
)
flags.DEFINE_boolean(
    'use_gpu_relax',
    None,
    '是否在 GPU 上执行弛豫。'
    'GPU 弛豫通常比 CPU 快很多，因此在条件允许时建议启用。'
    '如果启用该选项，则系统必须有可用 GPU。',
)
flags.DEFINE_integer(
    'jackhmmer_n_cpu',
    # Unfortunately, os.process_cpu_count() is only available in Python 3.13+.
    min(len(os.sched_getaffinity(0)), 8),
    'Jackhmmer 使用的 CPU 数量。默认为 min(cpu_count, 8)。'
    '超过 8 个 CPU 带来的额外加速通常非常有限。',
    lower_bound=0,
)
flags.DEFINE_integer(
    'hmmsearch_n_cpu',
    # Unfortunately, os.process_cpu_count() is only available in Python 3.13+.
    min(len(os.sched_getaffinity(0)), 8),
    'HMMsearch 使用的 CPU 数量。默认为 min(cpu_count, 8)。'
    '超过 8 个 CPU 带来的额外加速通常非常有限。',
    lower_bound=0,
)
flags.DEFINE_integer(
    'hhsearch_n_cpu',
    # Unfortunately, os.process_cpu_count() is only available in Python 3.13+.
    min(len(os.sched_getaffinity(0)), 8),
    'HHsearch 使用的 CPU 数量。默认为 min(cpu_count, 8)。'
    '超过 8 个 CPU 带来的额外加速通常非常有限。',
    lower_bound=0,
)

FLAGS = flags.FLAGS

MAX_TEMPLATE_HITS = 20
RELAX_MAX_ITERATIONS = 0
RELAX_ENERGY_TOLERANCE = 2.39
RELAX_STIFFNESS = 10.0
RELAX_EXCLUDE_RESIDUES = []
RELAX_MAX_OUTER_ITERATIONS = 3


def _check_flag(flag_name: str, other_flag_name: str, should_be_set: bool):
  if should_be_set != bool(FLAGS[flag_name].value):
    verb = 'be' if should_be_set else 'not be'
    raise ValueError(
        f'{flag_name} must {verb} set when running with '
        f'"--{other_flag_name}={FLAGS[other_flag_name].value}".'
    )


def _jnp_to_np(output: Dict[str, Any]) -> Dict[str, Any]:
  """递归地将 JAX 数组转换为 NumPy 数组。"""
  for k, v in output.items():
    if isinstance(v, dict):
      output[k] = _jnp_to_np(v)
    elif isinstance(v, jnp.ndarray):
      output[k] = np.array(v)
  return output


def _save_confidence_json_file(
    plddt: np.ndarray, output_dir: str, model_name: str
) -> None:
  confidence_json = confidence.confidence_json(plddt)

  # Save the confidence json.
  confidence_json_output_path = os.path.join(
      output_dir, f'confidence_{model_name}.json'
  )
  with open(confidence_json_output_path, 'w') as f:
    f.write(confidence_json)


def _save_mmcif_file(
    prot: protein.Protein,
    output_dir: str,
    model_name: str,
    file_id: str,
    model_type: str,
) -> None:
  """创建 mmCIF 字符串并保存到文件。

  Args:
    prot: Protein 对象。
    output_dir: 文件保存目录。
    model_name: 模型名称。
    file_id: 将用于 mmCIF 的文件 ID（通常为 PDB ID）。
    model_type: 单体或多聚体。
  """

  mmcif_string = protein.to_mmcif(prot, file_id, model_type)

  # Save the MMCIF.
  mmcif_output_path = os.path.join(output_dir, f'{model_name}.cif')
  with open(mmcif_output_path, 'w') as f:
    f.write(mmcif_string)


def _save_pae_json_file(
    pae: np.ndarray, max_pae: float, output_dir: str, model_name: str
) -> None:
  """检查预测结果中的 PAE 数据，如存在则保存为 JSON 文件。

  Args:
    pae: n_res x n_res 的 PAE 数组。
    max_pae: PAE 的最大可能值。
    output_dir: 文件保存目录。
    model_name: 模型名称。
  """
  pae_json = confidence.pae_json(pae, max_pae)

  # Save the PAE json.
  pae_json_output_path = os.path.join(output_dir, f'pae_{model_name}.json')
  with open(pae_json_output_path, 'w') as f:
    f.write(pae_json)


def predict_structure(
    fasta_path: str,
    fasta_name: str,
    output_dir_base: str,
    data_pipeline: Union[pipeline.DataPipeline, pipeline_multimer.DataPipeline],
    model_runners: Dict[str, model.RunModel],
    amber_relaxer: relax.AmberRelaxation,
    benchmark: bool,
    random_seed: int,
    models_to_relax: ModelsToRelax,
    model_type: str,
):
  """使用 AlphaFold 对给定序列进行结构预测。"""
  logging.info('正在预测 %s', fasta_name)
  timings = {}
  output_dir = os.path.join(output_dir_base, fasta_name)
  if not os.path.exists(output_dir):
    os.makedirs(output_dir)
  msa_output_dir = os.path.join(output_dir, 'msas')
  if not os.path.exists(msa_output_dir):
    os.makedirs(msa_output_dir)

  # Get features.
  t_0 = time.time()
  feature_dict = data_pipeline.process(
      input_fasta_path=fasta_path, msa_output_dir=msa_output_dir
  )
  timings['features'] = time.time() - t_0

  # Write out features as a pickled dictionary.
  features_output_path = os.path.join(output_dir, 'features.pkl')
  with open(features_output_path, 'wb') as f:
    pickle.dump(feature_dict, f, protocol=4)

  unrelaxed_pdbs = {}
  unrelaxed_proteins = {}
  relaxed_pdbs = {}
  relax_metrics = {}
  ranking_confidences = {}

  # Run the models.
  num_models = len(model_runners)
  for model_index, (model_name, model_runner) in enumerate(
      model_runners.items()
  ):
    logging.info('正在对 %s 运行模型 %s', fasta_name, model_name)
    t_0 = time.time()
    model_random_seed = model_index + random_seed * num_models
    processed_feature_dict = model_runner.process_features(
        feature_dict, random_seed=model_random_seed
    )
    timings[f'process_features_{model_name}'] = time.time() - t_0

    t_0 = time.time()
    prediction_result = model_runner.predict(
        processed_feature_dict, random_seed=model_random_seed
    )
    t_diff = time.time() - t_0
    timings[f'predict_and_compile_{model_name}'] = t_diff
    logging.info(
        'JAX 模型 %s 在 %s 上的总预测耗时（包含编译时间，参见'
        ' --benchmark）：%.1fs',
        model_name,
        fasta_name,
        t_diff,
    )

    if benchmark:
      t_0 = time.time()
      model_runner.predict(
          processed_feature_dict, random_seed=model_random_seed
      )
      t_diff = time.time() - t_0
      timings[f'predict_benchmark_{model_name}'] = t_diff
      logging.info(
          'JAX 模型 %s 在 %s 上的总预测耗时（不含编译时间）：'
          ' %.1fs',
          model_name,
          fasta_name,
          t_diff,
      )

    plddt = prediction_result['plddt']
    _save_confidence_json_file(plddt, output_dir, model_name)
    ranking_confidences[model_name] = prediction_result['ranking_confidence']

    if (
        'predicted_aligned_error' in prediction_result
        and 'max_predicted_aligned_error' in prediction_result
    ):
      pae = prediction_result['predicted_aligned_error']
      max_pae = prediction_result['max_predicted_aligned_error']
      _save_pae_json_file(pae, float(max_pae), output_dir, model_name)

    # Remove jax dependency from results.
    np_prediction_result = _jnp_to_np(dict(prediction_result))

    # Save the model outputs.
    result_output_path = os.path.join(output_dir, f'result_{model_name}.pkl')
    with open(result_output_path, 'wb') as f:
      pickle.dump(np_prediction_result, f, protocol=4)

    # Add the predicted LDDT in the b-factor column.
    # Note that higher predicted LDDT value means higher model confidence.
    plddt_b_factors = np.repeat(
        plddt[:, None], residue_constants.atom_type_num, axis=-1
    )
    unrelaxed_protein = protein.from_prediction(
        features=processed_feature_dict,
        result=prediction_result,
        b_factors=plddt_b_factors,
        remove_leading_feature_dimension=not model_runner.multimer_mode,
    )

    unrelaxed_proteins[model_name] = unrelaxed_protein
    unrelaxed_pdbs[model_name] = protein.to_pdb(unrelaxed_protein)
    unrelaxed_pdb_path = os.path.join(output_dir, f'unrelaxed_{model_name}.pdb')
    with open(unrelaxed_pdb_path, 'w') as f:
      f.write(unrelaxed_pdbs[model_name])

    _save_mmcif_file(
        prot=unrelaxed_protein,
        output_dir=output_dir,
        model_name=f'unrelaxed_{model_name}',
        file_id=str(model_index),
        model_type=model_type,
    )

  # Rank by model confidence.
  ranked_order = [
      model_name
      for model_name, confidence in sorted(
          ranking_confidences.items(), key=lambda x: x[1], reverse=True
      )
  ]

  # Relax predictions.
  if models_to_relax == ModelsToRelax.BEST:
    to_relax = [ranked_order[0]]
  elif models_to_relax == ModelsToRelax.ALL:
    to_relax = ranked_order
  elif models_to_relax == ModelsToRelax.NONE:
    to_relax = []

  for model_name in to_relax:
    t_0 = time.time()
    relaxed_pdb_str, _, violations = amber_relaxer.process(
        prot=unrelaxed_proteins[model_name]
    )
    relax_metrics[model_name] = {
        'remaining_violations': violations,
        'remaining_violations_count': sum(violations),
    }
    timings[f'relax_{model_name}'] = time.time() - t_0

    relaxed_pdbs[model_name] = relaxed_pdb_str

    # Save the relaxed PDB.
    relaxed_output_path = os.path.join(output_dir, f'relaxed_{model_name}.pdb')
    with open(relaxed_output_path, 'w') as f:
      f.write(relaxed_pdb_str)

    relaxed_protein = protein.from_pdb_string(relaxed_pdb_str)
    _save_mmcif_file(
        prot=relaxed_protein,
        output_dir=output_dir,
        model_name=f'relaxed_{model_name}',
        file_id='0',
        model_type=model_type,
    )

  # Write out relaxed PDBs in rank order.
  for idx, model_name in enumerate(ranked_order):
    ranked_output_path = os.path.join(output_dir, f'ranked_{idx}.pdb')
    with open(ranked_output_path, 'w') as f:
      if model_name in relaxed_pdbs:
        f.write(relaxed_pdbs[model_name])
      else:
        f.write(unrelaxed_pdbs[model_name])

    if model_name in relaxed_pdbs:
      protein_instance = protein.from_pdb_string(relaxed_pdbs[model_name])
    else:
      protein_instance = protein.from_pdb_string(unrelaxed_pdbs[model_name])

    _save_mmcif_file(
        prot=protein_instance,
        output_dir=output_dir,
        model_name=f'ranked_{idx}',
        file_id=str(idx),
        model_type=model_type,
    )

  ranking_output_path = os.path.join(output_dir, 'ranking_debug.json')
  with open(ranking_output_path, 'w') as f:
    label = 'iptm+ptm' if 'iptm' in prediction_result else 'plddts'
    f.write(
        json.dumps(
            {label: ranking_confidences, 'order': ranked_order}, indent=4
        )
    )

  logging.info('%s 的最终耗时统计：%s', fasta_name, timings)

  timings_output_path = os.path.join(output_dir, 'timings.json')
  with open(timings_output_path, 'w') as f:
    f.write(json.dumps(timings, indent=4))
  if models_to_relax != ModelsToRelax.NONE:
    relax_metrics_path = os.path.join(output_dir, 'relax_metrics.json')
    with open(relax_metrics_path, 'w') as f:
      f.write(json.dumps(relax_metrics, indent=4))


def main(argv):
  if len(argv) > 1:
    raise app.UsageError('命令行参数过多。')

  for tool_name in (
      'jackhmmer',
      'hhblits',
      'hhsearch',
      'hmmsearch',
      'hmmbuild',
      'kalign',
  ):
    if not FLAGS[f'{tool_name}_binary_path'].value:
      raise ValueError(
          f'找不到 "{tool_name}" 可执行文件的路径。请确认它已安装在系统中。'
      )

  use_small_bfd = FLAGS.db_preset == 'reduced_dbs'
  _check_flag(
      'small_bfd_database_path', 'db_preset', should_be_set=use_small_bfd
  )
  _check_flag('bfd_database_path', 'db_preset', should_be_set=not use_small_bfd)
  _check_flag(
      'uniref30_database_path', 'db_preset', should_be_set=not use_small_bfd
  )

  run_multimer_system = 'multimer' in FLAGS.model_preset
  model_type = 'Multimer' if run_multimer_system else 'Monomer'
  _check_flag(
      'pdb70_database_path',
      'model_preset',
      should_be_set=not run_multimer_system,
  )
  _check_flag(
      'pdb_seqres_database_path',
      'model_preset',
      should_be_set=run_multimer_system,
  )
  _check_flag(
      'uniprot_database_path', 'model_preset', should_be_set=run_multimer_system
  )

  if FLAGS.model_preset == 'monomer_casp14':
    num_ensemble = 8
  else:
    num_ensemble = 1

  # Check for duplicate FASTA file names.
  fasta_names = [pathlib.Path(p).stem for p in FLAGS.fasta_paths]
  if len(fasta_names) != len(set(fasta_names)):
    raise ValueError('所有 FASTA 路径都必须具有唯一的基础文件名。')

  if run_multimer_system:
    template_searcher = hmmsearch.Hmmsearch(
        binary_path=FLAGS.hmmsearch_binary_path,
        hmmbuild_binary_path=FLAGS.hmmbuild_binary_path,
        database_path=FLAGS.pdb_seqres_database_path,
        cpu=FLAGS.hmmsearch_n_cpu,
    )
    template_featurizer = templates.HmmsearchHitFeaturizer(
        mmcif_dir=FLAGS.template_mmcif_dir,
        max_template_date=FLAGS.max_template_date,
        max_hits=MAX_TEMPLATE_HITS,
        kalign_binary_path=FLAGS.kalign_binary_path,
        release_dates_path=None,
        obsolete_pdbs_path=FLAGS.obsolete_pdbs_path,
    )
  else:
    template_searcher = hhsearch.HHSearch(
        binary_path=FLAGS.hhsearch_binary_path,
        databases=[FLAGS.pdb70_database_path],
        cpu=FLAGS.hhsearch_n_cpu,
    )
    template_featurizer = templates.HhsearchHitFeaturizer(
        mmcif_dir=FLAGS.template_mmcif_dir,
        max_template_date=FLAGS.max_template_date,
        max_hits=MAX_TEMPLATE_HITS,
        kalign_binary_path=FLAGS.kalign_binary_path,
        release_dates_path=None,
        obsolete_pdbs_path=FLAGS.obsolete_pdbs_path,
    )

  monomer_data_pipeline = pipeline.DataPipeline(
      jackhmmer_binary_path=FLAGS.jackhmmer_binary_path,
      hhblits_binary_path=FLAGS.hhblits_binary_path,
      uniref90_database_path=FLAGS.uniref90_database_path,
      mgnify_database_path=FLAGS.mgnify_database_path,
      bfd_database_path=FLAGS.bfd_database_path,
      uniref30_database_path=FLAGS.uniref30_database_path,
      small_bfd_database_path=FLAGS.small_bfd_database_path,
      template_searcher=template_searcher,
      template_featurizer=template_featurizer,
      use_small_bfd=use_small_bfd,
      use_precomputed_msas=FLAGS.use_precomputed_msas,
      msa_tools_n_cpu=FLAGS.jackhmmer_n_cpu,
  )

  if run_multimer_system:
    num_predictions_per_model = FLAGS.num_multimer_predictions_per_model
    data_pipeline = pipeline_multimer.DataPipeline(
        monomer_data_pipeline=monomer_data_pipeline,
        jackhmmer_binary_path=FLAGS.jackhmmer_binary_path,
        uniprot_database_path=FLAGS.uniprot_database_path,
        use_precomputed_msas=FLAGS.use_precomputed_msas,
        jackhmmer_n_cpu=FLAGS.jackhmmer_n_cpu,
    )
  else:
    num_predictions_per_model = 1
    data_pipeline = monomer_data_pipeline

  model_runners = {}
  model_names = config.MODEL_PRESETS[FLAGS.model_preset]
  for model_name in model_names:
    model_config = config.model_config(model_name)
    if run_multimer_system:
      model_config.model.num_ensemble_eval = num_ensemble
    else:
      model_config.data.eval.num_ensemble = num_ensemble
    model_params = data.get_model_haiku_params(
        model_name=model_name, data_dir=FLAGS.data_dir
    )
    model_runner = model.RunModel(model_config, model_params)
    for i in range(num_predictions_per_model):
      model_runners[f'{model_name}_pred_{i}'] = model_runner

  logging.info(
      '共加载 %d 个模型：%s', len(model_runners), list(model_runners.keys())
  )

  amber_relaxer = relax.AmberRelaxation(
      max_iterations=RELAX_MAX_ITERATIONS,
      tolerance=RELAX_ENERGY_TOLERANCE,
      stiffness=RELAX_STIFFNESS,
      exclude_residues=RELAX_EXCLUDE_RESIDUES,
      max_outer_iterations=RELAX_MAX_OUTER_ITERATIONS,
      use_gpu=FLAGS.use_gpu_relax,
  )

  random_seed = FLAGS.random_seed
  if random_seed is None:
    random_seed = random.randrange(sys.maxsize // len(model_runners))
  logging.info('数据流水线使用的随机种子为 %d', random_seed)

  # Predict structure for each of the sequences.
  for i, fasta_path in enumerate(FLAGS.fasta_paths):
    fasta_name = fasta_names[i]
    predict_structure(
        fasta_path=fasta_path,
        fasta_name=fasta_name,
        output_dir_base=FLAGS.output_dir,
        data_pipeline=data_pipeline,
        model_runners=model_runners,
        amber_relaxer=amber_relaxer,
        benchmark=FLAGS.benchmark,
        random_seed=random_seed,
        models_to_relax=FLAGS.models_to_relax,
        model_type=model_type,
    )


if __name__ == '__main__':
  flags.mark_flags_as_required([
      'fasta_paths',
      'output_dir',
      'data_dir',
      'uniref90_database_path',
      'mgnify_database_path',
      'template_mmcif_dir',
      'max_template_date',
      'obsolete_pdbs_path',
      'use_gpu_relax',
  ])

  app.run(main)

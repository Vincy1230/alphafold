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

"""用于启动 AlphaFold Docker 镜像的脚本。"""

import os
import pathlib
import signal
from typing import Tuple

from absl import app
from absl import flags
from absl import logging
import docker
from docker import types


flags.DEFINE_bool('use_gpu', True, '启用 NVIDIA 运行时以使用 GPU。')
flags.DEFINE_enum(
    'models_to_relax',
    'best',
    ['best', 'all', 'none'],
    '指定哪些模型执行最终弛豫步骤。'
    '如果为 `all`，则所有模型都会弛豫，可能比较耗时。'
    '如果为 `best`，则只弛豫置信度最高的模型。'
    '如果为 `none`，则不执行弛豫。关闭弛豫可能会导致预测结果中出现'
    '较明显的立体化学违规，但在弛豫阶段出现问题时可能有帮助。',
)
flags.DEFINE_bool(
    'enable_gpu_relax', True, '如果启用了 GPU，则在 GPU 上执行弛豫。'
)
flags.DEFINE_string(
    'gpu_devices',
    'all',
    '传给 NVIDIA_VISIBLE_DEVICES 的设备列表，多个设备用逗号分隔。',
)
flags.DEFINE_list(
    'fasta_paths',
    None,
    'FASTA 文件路径列表，每个文件包含一个将依次进行预测的目标。'
    '如果某个 FASTA 文件包含多条序列，则会按多聚体处理。路径之间请用逗号分隔。'
    '所有 FASTA 路径的基础文件名必须唯一，因为它会用于命名各个预测的输出目录。',
)
flags.DEFINE_string(
    'output_dir',
    '/tmp/alphafold',
    '用于保存结果的目录路径。',
)
flags.DEFINE_string(
    'data_dir',
    None,
    '支持数据目录路径：包括 AlphaFold 参数以及遗传与模板数据库。'
    '请将其设置为 download_all_databases.sh 的目标目录。',
)
flags.DEFINE_string(
    'docker_image_name', 'alphafold', 'AlphaFold Docker 镜像名称。'
)
flags.DEFINE_string(
    'max_template_date',
    None,
    '纳入考虑的模板最大发布日期（ISO-8601 格式：YYYY-MM-DD）。'
    '在预测历史测试集时尤其重要。',
)
flags.DEFINE_enum(
    'db_preset',
    'full_dbs',
    ['full_dbs', 'reduced_dbs'],
    '选择预设的 MSA 数据库配置：较小的遗传数据库配置（reduced_dbs）'
    '或完整的遗传数据库配置（full_dbs）',
)
flags.DEFINE_enum(
    'model_preset',
    'monomer',
    ['monomer', 'monomer_casp14', 'monomer_ptm', 'multimer'],
    '选择预设模型配置：单体模型、带额外集成的单体模型、'
    '带 pTM 头的单体模型，或多聚体模型',
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
    'benchmark',
    False,
    '多次运行 JAX 模型评估，以获得不包含编译时间的耗时统计，'
    '从而更能反映批量推理多个蛋白时所需的时间。',
)
flags.DEFINE_boolean(
    'use_precomputed_msas',
    False,
    '是否读取已经写入磁盘的 MSA，而不是重新运行 MSA 工具。'
    'MSA 文件会从输出目录中查找，因此如果要在多次运行之间复用 MSA，'
    '输出目录必须保持不变。警告：这不会检查序列、数据库或配置是否发生变化。',
)
flags.DEFINE_string(
    'docker_user',
    f'{os.geteuid()}:{os.getegid()}',
    '用于运行 Docker 容器的 UID:GID。输出目录将归该用户:组所有。'
    '默认值为当前用户。有效格式为 uid 或 uid:gid；'
    '除非该用户已在容器内创建，否则 Docker 不识别非数字值。',
)

FLAGS = flags.FLAGS

_ROOT_MOUNT_DIRECTORY = '/mnt/'


def _create_mount(mount_name: str, path: str) -> Tuple[types.Mount, str]:
  """为模型使用到的每个文件和目录创建挂载点。"""
  path = pathlib.Path(path).absolute()
  target_path = pathlib.Path(_ROOT_MOUNT_DIRECTORY, mount_name)

  if path.is_dir():
    source_path = path
    mounted_path = target_path
  else:
    source_path = path.parent
    mounted_path = pathlib.Path(target_path, path.name)
  if not source_path.exists():
    raise ValueError(
        f'找不到要挂载到 Docker 容器中的源目录 "{source_path}"。'
    )
  logging.info('正在挂载 %s -> %s', source_path, target_path)
  mount = types.Mount(
      target=str(target_path),
      source=str(source_path),
      type='bind',
      read_only=True,
  )
  return mount, str(mounted_path)


def main(argv):
  if len(argv) > 1:
    raise app.UsageError('命令行参数过多。')

  # You can individually override the following paths if you have placed the
  # data in locations other than the FLAGS.data_dir.

  # Path to the Uniref90 database for use by JackHMMER.
  uniref90_database_path = os.path.join(
      FLAGS.data_dir, 'uniref90', 'uniref90.fasta'
  )

  # Path to the Uniprot database for use by JackHMMER.
  uniprot_database_path = os.path.join(
      FLAGS.data_dir, 'uniprot', 'uniprot.fasta'
  )

  # Path to the MGnify database for use by JackHMMER.
  mgnify_database_path = os.path.join(
      FLAGS.data_dir, 'mgnify', 'mgy_clusters_2022_05.fa'
  )

  # Path to the BFD database for use by HHblits.
  bfd_database_path = os.path.join(
      FLAGS.data_dir,
      'bfd',
      'bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt',
  )

  # Path to the Small BFD database for use by JackHMMER.
  small_bfd_database_path = os.path.join(
      FLAGS.data_dir, 'small_bfd', 'bfd-first_non_consensus_sequences.fasta'
  )

  # Path to the Uniref30 database for use by HHblits.
  uniref30_database_path = os.path.join(
      FLAGS.data_dir, 'uniref30', 'UniRef30_2021_03'
  )

  # Path to the PDB70 database for use by HHsearch.
  pdb70_database_path = os.path.join(FLAGS.data_dir, 'pdb70', 'pdb70')

  # Path to the PDB seqres database for use by hmmsearch.
  pdb_seqres_database_path = os.path.join(
      FLAGS.data_dir, 'pdb_seqres', 'pdb_seqres.txt'
  )

  # Path to a directory with template mmCIF structures, each named <pdb_id>.cif.
  template_mmcif_dir = os.path.join(FLAGS.data_dir, 'pdb_mmcif', 'mmcif_files')

  # Path to a file mapping obsolete PDB IDs to their replacements.
  obsolete_pdbs_path = os.path.join(FLAGS.data_dir, 'pdb_mmcif', 'obsolete.dat')

  alphafold_path = pathlib.Path(__file__).parent.parent
  data_dir_path = pathlib.Path(FLAGS.data_dir)
  if alphafold_path == data_dir_path or alphafold_path in data_dir_path.parents:
    raise app.UsageError(
        f'下载目录 {FLAGS.data_dir} 不应位于 AlphaFold 仓库目录之内。'
        '否则在构建镜像时会复制大型数据库，导致 Docker 构建速度很慢。'
    )

  mounts = []
  command_args = []

  # Mount each fasta path as a unique target directory.
  target_fasta_paths = []
  for i, fasta_path in enumerate(FLAGS.fasta_paths):
    mount, target_path = _create_mount(f'fasta_path_{i}', fasta_path)
    mounts.append(mount)
    target_fasta_paths.append(target_path)
  command_args.append(f'--fasta_paths={",".join(target_fasta_paths)}')

  database_paths = [
      ('uniref90_database_path', uniref90_database_path),
      ('mgnify_database_path', mgnify_database_path),
      ('data_dir', FLAGS.data_dir),
      ('template_mmcif_dir', template_mmcif_dir),
      ('obsolete_pdbs_path', obsolete_pdbs_path),
  ]

  if FLAGS.model_preset == 'multimer':
    database_paths.append(('uniprot_database_path', uniprot_database_path))
    database_paths.append(
        ('pdb_seqres_database_path', pdb_seqres_database_path)
    )
  else:
    database_paths.append(('pdb70_database_path', pdb70_database_path))

  if FLAGS.db_preset == 'reduced_dbs':
    database_paths.append(('small_bfd_database_path', small_bfd_database_path))
  else:
    database_paths.extend([
        ('uniref30_database_path', uniref30_database_path),
        ('bfd_database_path', bfd_database_path),
    ])
  for name, path in database_paths:
    if path:
      mount, target_path = _create_mount(name, path)
      mounts.append(mount)
      command_args.append(f'--{name}={target_path}')

  output_target_path = os.path.join(_ROOT_MOUNT_DIRECTORY, 'output')
  mounts.append(types.Mount(output_target_path, FLAGS.output_dir, type='bind'))

  use_gpu_relax = FLAGS.enable_gpu_relax and FLAGS.use_gpu

  command_args.extend([
      f'--output_dir={output_target_path}',
      f'--max_template_date={FLAGS.max_template_date}',
      f'--db_preset={FLAGS.db_preset}',
      f'--model_preset={FLAGS.model_preset}',
      f'--benchmark={FLAGS.benchmark}',
      f'--use_precomputed_msas={FLAGS.use_precomputed_msas}',
      f'--num_multimer_predictions_per_model={FLAGS.num_multimer_predictions_per_model}',
      f'--models_to_relax={FLAGS.models_to_relax}',
      f'--use_gpu_relax={use_gpu_relax}',
      '--logtostderr',
  ])

  client = docker.from_env()
  device_requests = (
      [docker.types.DeviceRequest(driver='nvidia', capabilities=[['gpu']])]
      if FLAGS.use_gpu
      else None
  )

  container = client.containers.run(
      image=FLAGS.docker_image_name,
      command=command_args,
      device_requests=device_requests,
      remove=True,
      detach=True,
      mounts=mounts,
      user=FLAGS.docker_user,
      environment={
          'NVIDIA_VISIBLE_DEVICES': FLAGS.gpu_devices,
          # The following flags allow us to make predictions on proteins that
          # would typically be too long to fit into GPU memory.
          'TF_FORCE_UNIFIED_MEMORY': '1',
          'XLA_PYTHON_CLIENT_MEM_FRACTION': '4.0',
      },
  )

  # Add signal handler to ensure CTRL+C also stops the running container.
  signal.signal(
      signal.SIGINT, lambda unused_sig, unused_frame: container.kill()
  )

  for line in container.logs(stream=True):
    logging.info(line.strip().decode('utf-8'))


if __name__ == '__main__':
  flags.mark_flags_as_required([
      'data_dir',
      'fasta_paths',
      'max_template_date',
  ])
  app.run(main)

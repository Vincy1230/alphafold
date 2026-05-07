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

"""AlphaFold Colab 笔记本的辅助方法。"""
from typing import AbstractSet, Any, Mapping, Optional, Sequence

from alphafold.common import residue_constants
from alphafold.data import parsers
from matplotlib import pyplot as plt
import numpy as np


def clean_and_validate_single_sequence(
    input_sequence: str, min_length: int, max_length: int
) -> str:
  """检查输入序列是否有效，并返回清洗后的版本。"""
  # Remove all whitespaces, tabs and end lines; upper-case.
  clean_sequence = input_sequence.translate(
      str.maketrans('', '', ' \n\t')
  ).upper()
  aatypes = set(residue_constants.restypes)  # 20 standard aatypes.
  if not set(clean_sequence).issubset(aatypes):
    raise ValueError(
        '输入序列包含非氨基酸字母：'
        f'{set(clean_sequence) - aatypes}。AlphaFold 仅支持 20 种标准氨基酸作为输入。'
    )
  if len(clean_sequence) < min_length:
    raise ValueError(
        f'输入序列过短：当前为 {len(clean_sequence)} 个氨基酸，'
        f'最小长度要求为 {min_length}'
    )
  if len(clean_sequence) > max_length:
    raise ValueError(
        f'输入序列过长：当前为 {len(clean_sequence)} 个氨基酸，'
        f'最大允许长度为 {max_length}。视你的资源情况'
        '（系统内存、GPU 显存）而定，可能可以改用完整 AlphaFold 系统运行。'
    )
  return clean_sequence


def clean_and_validate_input_sequences(
    input_sequences: Sequence[str],
    min_sequence_length: int,
    max_sequence_length: int,
) -> Sequence[str]:
  """校验并清洗输入序列。"""
  sequences = []

  for input_sequence in input_sequences:
    if input_sequence.strip():
      input_sequence = clean_and_validate_single_sequence(
          input_sequence=input_sequence,
          min_length=min_sequence_length,
          max_length=max_sequence_length,
      )
      sequences.append(input_sequence)

  if sequences:
    return sequences
  else:
    raise ValueError(
        '未提供任何输入氨基酸序列，请至少提供一条序列。'
    )


def merge_chunked_msa(
    results: Sequence[Mapping[str, Any]], max_hits: Optional[int] = None
) -> parsers.Msa:
  """将分块数据库命中的结果合并为完整数据库的命中结果。"""
  unsorted_results = []
  for chunk_index, chunk in enumerate(results):
    msa = parsers.parse_stockholm(chunk['sto'])
    e_values_dict = parsers.parse_e_values_from_tblout(chunk['tbl'])
    # Jackhmmer lists sequences as <sequence name>/<residue from>-<residue to>.
    e_values = [e_values_dict[t.partition('/')[0]] for t in msa.descriptions]
    chunk_results = zip(
        msa.sequences, msa.deletion_matrix, msa.descriptions, e_values
    )
    if chunk_index != 0:
      next(chunk_results)  # 只从第一个分块中保留查询序列（第一个命中）。
    unsorted_results.extend(chunk_results)

  sorted_by_evalue = sorted(unsorted_results, key=lambda x: x[-1])
  merged_sequences, merged_deletion_matrix, merged_descriptions, _ = zip(
      *sorted_by_evalue
  )
  merged_msa = parsers.Msa(
      sequences=merged_sequences,
      deletion_matrix=merged_deletion_matrix,
      descriptions=merged_descriptions,
  )
  if max_hits is not None:
    merged_msa = merged_msa.truncate(max_seqs=max_hits)

  return merged_msa


def show_msa_info(
    single_chain_msas: Sequence[parsers.Msa], sequence_index: int
):
  """打印信息并展示去重后的单链 MSA 图。"""
  full_single_chain_msa = []
  for single_chain_msa in single_chain_msas:
    full_single_chain_msa.extend(single_chain_msa.sequences)

  # Deduplicate but preserve order (hence can't use set).
  deduped_full_single_chain_msa = list(dict.fromkeys(full_single_chain_msa))
  total_msa_size = len(deduped_full_single_chain_msa)
  print(
      f'\n序列 {sequence_index} 总共找到 {total_msa_size} 条唯一序列\n'
  )

  aa_map = {res: i for i, res in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ-')}
  msa_arr = np.array(
      [[aa_map[aa] for aa in seq] for seq in deduped_full_single_chain_msa]
  )

  plt.rcParams['font.sans-serif'] = ['SimHei']
  plt.figure(figsize=(12, 3))
  plt.title(
      f'序列 {sequence_index} 的 MSA 中各残基位置非缺口氨基酸计数'
  )
  plt.plot(np.sum(msa_arr != aa_map['-'], axis=0), color='black')
  plt.ylabel('非缺口计数')
  plt.yticks(range(0, total_msa_size + 1, max(1, int(total_msa_size / 3))))
  plt.show()


def empty_placeholder_template_features(
    num_templates: int, num_res: int
) -> Mapping[str, np.ndarray]:
  return {
      'template_aatype': np.zeros(
          (
              num_templates,
              num_res,
              len(residue_constants.restypes_with_x_and_gap),
          ),
          dtype=np.float32,
      ),
      'template_all_atom_masks': np.zeros(
          (num_templates, num_res, residue_constants.atom_type_num),
          dtype=np.float32,
      ),
      'template_all_atom_positions': np.zeros(
          (num_templates, num_res, residue_constants.atom_type_num, 3),
          dtype=np.float32,
      ),
      'template_domain_names': np.zeros([num_templates], dtype=object),
      'template_sequence': np.zeros([num_templates], dtype=object),
      'template_sum_probs': np.zeros([num_templates], dtype=np.float32),
  }


def check_cell_execution_order(
    cells_ran: AbstractSet[int], cell_number: int
) -> None:
  """检查单元格执行顺序是否正确。

  Args:
    cells_ran: 已执行单元格编号的集合。
    cell_number: 调用本检查时所在的单元格编号。

  Raises:
    如果 <1:cell_number> 范围内有单元格未执行，则抛出错误。
  """
  previous_cells = set(range(1, cell_number))
  cells_not_ran = previous_cells - cells_ran
  if cells_not_ran != set():
    cells_not_ran_str = ', '.join([str(x) for x in sorted(cells_not_ran)])
    raise ValueError(
        f'你尚未执行以下单元格：{cells_not_ran_str}。你的 Colab '
        '运行时可能在执行过程中中断了。请重启运行时并从第一个单元格重新运行！'
    )

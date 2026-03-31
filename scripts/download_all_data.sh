#!/usr/bin/env bash
#
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
#
# 下载并解压 AlphaFold 所需的全部数据。
#
# 用法：bash download_all_data.sh /path/to/download/directory
set -e

if [[ $# -eq 0 ]]; then
  echo "错误：必须提供下载目录作为输入参数。"
  exit 1
fi

if ! command -v aria2c &> /dev/null ; then
  echo "错误：找不到 aria2c。请先安装 aria2c（sudo apt install aria2）。"
  exit 1
fi

if ! command -v rsync &> /dev/null ; then
    echo "错误：找不到 rsync。请先安装 rsync（sudo apt install rsync）。"
    exit 1
fi

DOWNLOAD_DIR="$(realpath "$1")"
DOWNLOAD_MODE="${2:-full_dbs}"  # 默认模式为 full_dbs。
if [[ "${DOWNLOAD_MODE}" != full_dbs && "${DOWNLOAD_MODE}" != reduced_dbs ]]
then
  echo "无法识别 DOWNLOAD_MODE ${DOWNLOAD_MODE}。"
  exit 1
fi

SCRIPT_DIR="$(dirname "$(realpath "$0")")"

echo "正在下载 AlphaFold 参数..."
bash "${SCRIPT_DIR}/download_alphafold_params.sh" "${DOWNLOAD_DIR}"

if [[ "${DOWNLOAD_MODE}" = reduced_dbs ]] ; then
  echo "正在下载 Small BFD..."
  bash "${SCRIPT_DIR}/download_small_bfd.sh" "${DOWNLOAD_DIR}"
else
  echo "正在下载 BFD..."
  bash "${SCRIPT_DIR}/download_bfd.sh" "${DOWNLOAD_DIR}"
fi

echo "正在下载 MGnify..."
bash "${SCRIPT_DIR}/download_mgnify.sh" "${DOWNLOAD_DIR}"

echo "正在下载 PDB70..."
bash "${SCRIPT_DIR}/download_pdb70.sh" "${DOWNLOAD_DIR}"

echo "正在下载 PDB mmCIF 文件..."
bash "${SCRIPT_DIR}/download_pdb_mmcif.sh" "${DOWNLOAD_DIR}"

echo "正在下载 Uniref30..."
bash "${SCRIPT_DIR}/download_uniref30.sh" "${DOWNLOAD_DIR}"

echo "正在下载 Uniref90..."
bash "${SCRIPT_DIR}/download_uniref90.sh" "${DOWNLOAD_DIR}"

echo "正在下载 UniProt..."
bash "${SCRIPT_DIR}/download_uniprot.sh" "${DOWNLOAD_DIR}"

echo "正在下载 PDB SeqRes..."
bash "${SCRIPT_DIR}/download_pdb_seqres.sh" "${DOWNLOAD_DIR}"

echo "全部数据下载完成。"

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
# 下载、解压并展平 AlphaFold 所需的 PDB 数据库。
#
# 用法：bash download_pdb_mmcif.sh /path/to/download/directory
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
    echo "错误：找不到 rsync。请先安装 rsync。"
    exit 1
fi

DOWNLOAD_DIR="$(realpath "$1")"
ROOT_DIR="${DOWNLOAD_DIR}/pdb_mmcif"
RAW_DIR="${ROOT_DIR}/raw"
MMCIF_DIR="${ROOT_DIR}/mmcif_files"

echo "正在运行 rsync 获取全部 mmCIF 文件（请注意，rsync 的进度估算可能并不准确）..."
echo "如果下载速度过慢，可以尝试改用以下镜像："
echo "  * rsync.ebi.ac.uk::pub/databases/pdb/data/structures/divided/mmCIF/（欧洲）"
echo "  * ftp.pdbj.org::ftp_data/structures/divided/mmCIF/（亚洲）"
echo "或者参见 https://www.wwpdb.org/ftp/pdb-ftp-sites 获取更多下载选项。"
mkdir --parents "${RAW_DIR}"
rsync --recursive --links --perms --times --compress --info=progress2 --delete --port=33444 \
  rsync.rcsb.org::ftp_data/structures/divided/mmCIF/ \
  "${RAW_DIR}"

echo "正在解压全部 mmCIF 文件..."
if command -v parallel >/dev/null 2>&1
then
   find "${RAW_DIR}/" -type f -iname "*.gz" -print0 | parallel -0 -j -1 --xargs gunzip
else
   find "${RAW_DIR}/" -type f -iname "*.gz" -exec gunzip {} +
fi

echo "正在展平全部 mmCIF 文件..."
mkdir --parents "${MMCIF_DIR}"
find "${RAW_DIR}" -type d -empty -delete  # 删除空目录。
for subdir in "${RAW_DIR}"/*; do
  mv "${subdir}/"*.cif "${MMCIF_DIR}"
done

# 删除空的下载目录结构。
find "${RAW_DIR}" -type d -empty -delete

aria2c "https://files.wwpdb.org/pub/pdb/data/status/obsolete.dat" --dir="${ROOT_DIR}"

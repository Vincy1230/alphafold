# AlphaFold 蛋白质结构数据库

## 简介

AlphaFold 的 UniProt 发布版本（2.14 亿条预测）托管在 [Google Cloud Public Datasets](https://console.cloud.google.com/marketplace/product/bigquery-public-data/deepmind-alphafold) 上，并依据 [CC-BY-4.0 许可证](http://creativecommons.org/licenses/by/4.0/legalcode)免费提供下载。数据集存放在 Cloud Storage 存储桶中，元数据可通过 BigQuery 获取。下载需要 Google Cloud 账号，但数据本身可依据 [CC-BY 4.0 许可证](http://creativecommons.org/licenses/by/4.0/legalcode)自由使用。

本文概述了在不同使用场景下访问和下载该数据集的方法。关于数据库中包含哪些蛋白以及版本更新日志，请参阅 [AlphaFold database FAQ](https://www.alphafold.com/faq)。

:ledger: **注意：完整数据集规模巨大，如无显著计算资源，将很难直接处理（总大小约 23 TiB，共 3 × 2.14 亿个文件）。**

除了下载完整数据集外，你还可以选择：

1.  通过我们的[下载页面](https://alphafold.ebi.ac.uk/download)下载预先整理好的子集（覆盖重要物种 / Swiss-Prot）。
2.  下载自定义数据子集，详见下文。

如果你确实需要下载完整数据集，请参见“批量下载”一节。关于如何避免使用 Google Cloud Public Datasets 时产生意外费用，请参阅下方“创建 Google Cloud 账号”一节。

## 许可证

数据可依据 [CC-BY-4.0 许可证](http://creativecommons.org/licenses/by/4.0/legalcode)用于学术和商业用途。

EMBL-EBI 希望你在使用其在线服务、数据库或软件时，按照良好的科学实践进行适当署名（例如在论文、服务或产品中）。

如果你使用了 AlphaFold 预测结果，请引用以下论文：

*   [Jumper, J et al. Highly accurate protein structure prediction with AlphaFold. Nature (2021).](https://www.nature.com/articles/s41586-021-03819-2)
*   [Varadi, M et al. AlphaFold Protein Structure Database: massively expanding the structural coverage of protein-sequence space with high-accuracy models. Nucleic Acids Research (2021).](https://academic.oup.com/nar/advance-article/doi/10.1093/nar/gkab1061/6430488)

AlphaFold 数据版权归 DeepMind Technologies Limited 所有（2022）。

## 免责声明

AlphaFold 数据及本网站提供的其他信息仅用于理论建模，使用时请务必谨慎。所有内容均按“现状”提供，不附带任何形式的明示或暗示担保。特别说明：我们不保证使用这些信息不会侵犯任何第三方权利。相关信息不能替代专业医学建议、诊断或治疗，也不构成医学或其他专业建议。

## 数据格式

数据集文件名以如下形式的蛋白标识符开头：`AF-[UniProt accession]-F[fragment number]`。

每个条目提供 3 个文件：

*   **model_v4.cif**：包含预测蛋白结构的原子坐标及部分元数据。该格式的参考资料可见 [ModelCIF](https://github.com/ihmwg/ModelCIF) 和 [PDBx/mmCIF](https://mmcif.wwpdb.org)。
*   **confidence_v4.json**：包含 AlphaFold 输出的置信度指标 pLDDT。它为每个残基提供一个数值，用于表示 AlphaFold 对该残基局部周围结构的置信度。pLDDT 的取值范围是 0 到 100，其中 100 表示置信度最高。该信息同时也保存在 CIF 文件中。
*   **predicted_aligned_error_v4.json**：包含 AlphaFold 输出的置信度指标 PAE。它为每一对残基提供一个数值；该值越小，表示 AlphaFold 对这两个残基相对位置越有信心。与 pLDDT 相比，PAE 更适合用于判断不同结构域相对排布的置信度。格式说明可见 [这里](https://alphafold.ebi.ac.uk/faq#faq-7)。

按 NCBI taxonomy ID 分组的预测结果可在同一存储桶中以 `proteomes/proteome-tax_id-[TAX ID]-[SHARD ID]_v4.tar` 的形式获取。

存储桶中还额外提供两个文件：

*   `accession_ids.csv`：包含 AlphaFold DB 中所有已有预测结果的 UniProt accession 列表。该 CSV 文件包含以下列（逗号分隔）：
    *   UniProt accession，例如 `A8H2R3`
    *   第一个残基索引（UniProt 编号），例如 `1`
    *   最后一个残基索引（UniProt 编号），例如 `199`
    *   AlphaFold DB 标识符，例如 `AF-A8H2R3-F1`
    *   最新版本号，例如 `4`
*   `sequences.fasta`：包含当前数据库版本中所有蛋白的 FASTA 序列。标识行以 `>AFDB` 开头，后接 AlphaFold DB 标识符和蛋白名称；序列行为对应的氨基酸序列。每条序列均单独占一行，不做换行折叠。

## 创建 Google Cloud 账号

如果你希望从 Google Cloud Public Datasets 下载数据（而不是从 AFDB 或 3D Beacons 获取），则需要一个 Google Cloud 账号。请参阅 [Google Cloud get started](https://cloud.google.com/docs/get-started) 页面，并了解其 [免费层使用限制](https://cloud.google.com/free)。

**重要：试用期结束（90 天）后，如需继续访问，你必须升级到可计费账号。即使你仍可继续使用免费层（包括访问 Public Datasets 存储桶），超出免费额度的使用仍会产生费用。因此请务必提前熟悉你所使用服务的计费方式。**

1.  打开 [https://cloud.google.com/datasets](https://cloud.google.com/datasets)。
2.  创建账号：
    1.  点击右上角的 “get started for free”。
    2.  同意所有服务条款。
    3.  按提示完成设置。请注意，系统会要求你提供支付方式，但除非你启用了计费，否则不会扣费。
    4.  访问 Google Cloud Public Datasets 存储桶本身始终免费，你也将拥有 [free tier](https://cloud.google.com/free/docs/gcp-free-tier#free-tier-usage-limits) 权限。
3.  设置项目：
    1.  点击左上角导航菜单（三横线图标）。
    2.  选择 “Cloud overview” -> “Dashboard”。
    3.  左上角会有一个项目菜单栏（通常显示 “My First Project”），点击后会弹出 “Select a Project” 对话框。
    4.  若要继续使用当前项目，点击对话框底部的 “Cancel”。
    5.  若要创建新项目，点击对话框顶部的 “New Project”：
        1.  选择项目名称。
        2.  对于 location，如果你的组织已有 Cloud 账号可选择该位置，否则保持默认即可。
4.  安装 `gsutil`：
    1.  按照[这里的说明](https://cloud.google.com/storage/docs/gsutil_install)进行安装。

## 访问数据集

数据可从以下位置获取：

*   GCS 数据存储桶：
    [gs://public-datasets-deepmind-alphafold-v4](https://console.cloud.google.com/storage/browser/public-datasets-deepmind-alphafold-v4)

## 批量下载

除非你确实需要在本地计算资源上处理完整数据集（例如学术高性能计算中心），否则我们并不推荐下载整个数据集。

我们估计，在 1 Gbps 网络条件下，下载完整数据库大约需要 2.5 天。

虽然我们不了解你的计算基础设施细节，但下面给出一些建议的下载方式。如有问题，请通过 [alphafold@deepmind.com](mailto:alphafold@deepmind.com) 联系我们。

推荐的整库下载方式，是使用下列命令下载 1,015,797 个按蛋白质组切分的 tar 分片文件。与逐个下载单文件相比，这种方式快得多，因为它能显著降低单文件固定延迟带来的开销。

```bash
gsutil -m cp -r gs://public-datasets-deepmind-alphafold-v4/proteomes/ .
```

下载完成后，你需要解包所有蛋白质组 tar 文件，并对其中的单个文件执行 gunzip。请注意，解包后大约会产生 6.44 亿个文件，因此请确认你的文件系统能够承受该规模。

### Storage Transfer Service

部分用户可能会觉得 [Storage Transfer Service](https://cloud.google.com/storage-transfer-service) 很方便，可用于在本存储桶与另一个存储桶或其他云服务之间建立传输。*使用该服务可能产生费用*。详情请参阅其 [pricing page](https://cloud.google.com/storage-transfer/pricing)，尤其是传输到其他云服务时的计费说明。

## 下载数据子集

### AlphaFold Database 搜索

对于较简单的查询，例如按蛋白名称、基因名称或 UniProt accession 搜索，你可以直接使用 [alphafold.ebi.ac.uk](https://alphafold.ebi.ac.uk) 的主搜索栏。

### 3D Beacons

[3D-Beacons](https://3d-beacons.org) 是一个国际合作项目，由多个蛋白结构数据提供方共同构建统一数据访问机制的联邦网络。3D-Beacons 平台允许用户从 AlphaFold DB 等数据提供方获取实验测定或理论预测蛋白模型的坐标文件和元数据。

关于如何通过 3D-Beacons 获取 AlphaFold 预测结果，详见 [3D-Beacons documentation](https://www.ebi.ac.uk/pdbe/pdbe-kb/3dbeacons/docs)。

### 其他预制物种子集

部分模式生物蛋白质组、全球健康相关蛋白质组和 Swiss-Prot 子集可在 [AFDB 网站](https://alphafold.ebi.ac.uk/download) 下载。这些数据基于 [reference proteomes](https://www.uniprot.org/help/reference_proteome) 生成。如果你需要其他物种，或者某一物种的 *全部* 蛋白，请继续阅读。

我们为所有物种提供了 1,015,797 个分片 tar 文件，地址为 [gs://public-datasets-deepmind-alphafold-v4/proteomes/](https://console.cloud.google.com/storage/browser/public-datasets-deepmind-alphafold-v4/proteomes/)。我们对每个蛋白质组进行了分片，保证每个分片最多包含 10,000 个蛋白（由于每个蛋白有 3 个文件，因此每个分片最多约 30,000 个文件）。如果你要下载某个蛋白质组，请按以下步骤操作：

1.  查找目标物种的 [NCBI taxonomy ID](https://www.ncbi.nlm.nih.gov/taxonomy)（`[TAX_ID]`）。
2.  运行 `gsutil -m cp gs://public-datasets-deepmind-alphafold-v4/proteomes/proteome-tax_id-[TAX_ID]-*_v4.tar .` 下载该蛋白质组的全部分片。
3.  解包所有下载的文件，并对内部单文件执行 gunzip。

### 文件清单

预制好的文件清单（manifest）可在 [gs://public-datasets-deepmind-alphafold-v4/manifests](https://console.cloud.google.com/storage/browser/public-datasets-deepmind-alphafold-v4/manifests/) 获取。请注意，这些文件名本身不包含存储桶前缀；下载到本地后，你可以自行补上。

你也可以定义自己的文件列表，例如通过 BigQuery 生成。之后可使用 `gsutil` 批量下载：

```bash
cat [manifest file] | gsutil -m cp -I .
```

这种方式会比下载按物种打包的 tar 文件慢得多，因为每个文件都有单独的固定开销。

### BigQuery

**重要：Google Cloud 的 [free tier](https://cloud.google.com/bigquery/pricing#free-tier) 包含 [BigQuery Sandbox](https://cloud.google.com/bigquery/docs/sandbox)，每月可免费处理 1 TB 查询数据。如果你在一个月内反复执行查询，可能超出该上限；若你已[升级为付费 Cloud Billing 账号](https://cloud.google.com/free/docs/gcp-free-tier#how-to-upgrade)，则可能产生费用。**

**通常这足以支持对元数据表执行若干次查询，但实际消耗仍取决于你查询与选择的列大小。更多细节请参阅 [BigQuery pricing page](https://cloud.google.com/bigquery/pricing)。**

**这部分费用由用户自行负责，因此请务必在控制台中持续关注你的计费设置与资源用量。**

BigQuery 是一种无服务器、高可扩展的分析工具，可用于对大型数据集执行 SQL 查询。UniProt 数据集对应的元数据约占 113 GiB，因此在本地处理和分析会比较困难。对应的数据表名如下：

*   BigQuery 元数据表：
    [bigquery-public-data.deepmind_alphafold.metadata](https://console.cloud.google.com/bigquery?project=bigquery-public-data&ws=!1m5!1m4!4m3!1sbigquery-public-data!2sdeepmind_alphafold!3smetadata)

通过 BigQuery SQL，你可以执行复杂查询，例如找出某一物种中所有高精度预测，甚至可以与其他数据集联结，例如通过 `uniprotSequence` 与实验数据集联结，或通过 `taxId` 与 NCBI taxonomy 联结。

如果你觉得元数据中还应增加其他有用信息，欢迎提交 GitHub issue。

#### 配置

请按照 [BigQuery Sandbox set up guide](https://cloud.google.com/bigquery/docs/sandbox) 完成配置。

#### 探索元数据

可使用以下查询查看可用列名及其数据类型：

```sql
SELECT column_name, data_type FROM bigquery-public-data.deepmind_alphafold.INFORMATION_SCHEMA.COLUMNS
WHERE table_name = 'metadata'
```

**列名**               | **数据类型**      | **说明**
---------------------- | ----------------- | -----------------
allVersions            | `ARRAY<INT64>`    | 该预测曾出现过的 AFDB 版本数组
entryId                | `STRING`          | AFDB 条目标识符，例如 `"AF-Q1HGU3-F1"`
fractionPlddtConfident | `FLOAT64`         | pLDDT 介于 70 到 90 的残基占比
fractionPlddtLow       | `FLOAT64`         | pLDDT 介于 50 到 70 的残基占比
fractionPlddtVeryHigh  | `FLOAT64`         | pLDDT 大于 90 的残基占比
fractionPlddtVeryLow   | `FLOAT64`         | pLDDT 小于 50 的残基占比
gene                   | `STRING`          | 基因名称（若已知），例如 `"COII"`
geneSynonyms           | `ARRAY<STRING>`   | 基因的其他别名
globalMetricValue      | `FLOAT64`         | 该预测的平均 pLDDT
isReferenceProteome    | `BOOL`            | 是否属于参考蛋白质组
isReviewed             | `BOOL`            | 是否经过人工审阅，即是否属于 Swiss-Prot
latestVersion          | `INT64`           | 该预测的最新 AFDB 版本
modelCreatedDate       | `DATE`            | 该条目的创建日期，例如 `"2022-06-01"`
organismCommonNames    | `ARRAY<STRING>`   | 物种常用名称列表
organismScientificName | `STRING`          | 物种学名
organismSynonyms       | `ARRAY<STRING>`   | 物种别名列表
proteinFullNames       | `ARRAY<STRING>`   | 蛋白全名列表
proteinShortNames      | `ARRAY<STRING>`   | 蛋白简称列表
sequenceChecksum       | `STRING`          | 序列的 [CRC64 hash](https://www.uniprot.org/help/checksum)，可用于成本更低的查找
sequenceVersionDate    | `DATE`            | UniProt 中该序列最近修改日期
taxId                  | `INT64`           | 来源物种的 NCBI taxonomy ID
uniprotAccession       | `STRING`          | UniProt accession ID
uniprotDescription     | `STRING`          | UniProt 联盟推荐名称
uniprotEnd             | `INT64`           | 该条目在 UniProt 条目中的最后一个残基编号。若非蛋白片段，则通常等于蛋白长度
uniprotId              | `STRING`          | UniProt EntryName 字段
uniprotSequence        | `STRING`          | 该预测对应的氨基酸序列
uniprotStart           | `INT64`           | 该条目在 UniProt 条目中的第一个残基编号。若非蛋白片段，则通常为 1

#### 生成汇总统计

下面的查询可给出每个物种在不同置信度区间上的平均预测占比：

```sql
SELECT
 organismScientificName AS name,
 SUM(fractionPlddtVeryLow) / COUNT(fractionPlddtVeryLow) AS mean_plddt_very_low,
 SUM(fractionPlddtLow) / COUNT(fractionPlddtLow) AS mean_plddt_low,
 SUM(fractionPlddtConfident) / COUNT(fractionPlddtConfident) AS mean_plddt_confident,
 SUM(fractionPlddtVeryHigh) / COUNT(fractionPlddtVeryHigh) AS mean_plddt_very_high,
 COUNT(organismScientificName) AS num_predictions
FROM bigquery-public-data.deepmind_alphafold.metadata
GROUP by name
ORDER BY num_predictions DESC;
```

#### 生成文件列表

我们预计，元数据最重要的用途之一，是按不同条件筛选蛋白子集，以便用户只复制数据集中 2.14 亿个蛋白中的一小部分。下面给出一个示例查询：

```sql
with file_rows AS (
  with file_cols AS (
    SELECT
      CONCAT(entryID, '-model_v4.cif') as m,
      CONCAT(entryID, '-predicted_aligned_error_v4.json') as p
    FROM bigquery-public-data.deepmind_alphafold.metadata
    WHERE organismScientificName = "Homo sapiens"
      AND (fractionPlddtVeryHigh + fractionPlddtConfident) > 0.5
  )
  SELECT * FROM file_cols UNPIVOT (files for filetype in (m, p))
)
SELECT CONCAT('gs://public-datasets-deepmind-alphafold-v4/', files) as files
from file_rows
```

在这个例子中，列表被筛选为仅包含 *Homo sapiens*（人类）中“超过一半残基置信度达到 confident 或更高（>70 pLDDT）”的蛋白。

该查询会生成一个名为 `"files"` 的单列表格，其中每一行都是该蛋白对应的两个文件类型之一在云端的位置。除此之外，还有一个额外的 `confidence_v4.json` 文件，里面保存了每残基 pLDDT 信息。虽然这些信息已经存在于 CIF 文件中，但如果你只需要该项信息，也可以优先使用这个 JSON。

这样，用户就能只下载自己真正需要的蛋白，而无需下载整个数据集。你也可以利用其他列来筛选蛋白子集；有关更多筛选方式，请参阅 [BigQuery documentation](https://cloud.google.com/bigquery/docs)。下载这些子集到本地时，也建议遵循官方文档，因为最佳方案通常取决于文件大小。在某些情况下，使用 [Colab](https://colab.research.google.com/) 下载大型文件可能更方便（例如借助 pandas 的 `to_csv`）。

#### 历史版本

AFDB 的历史版本会继续保留在 [gs://public-datasets-deepmind-alphafold](https://console.cloud.google.com/storage/browser/public-datasets-deepmind-alphafold) 中，以支持可复现研究。我们建议优先使用最新版本（v4）。

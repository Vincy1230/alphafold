# AlphaFold Server 作业的 JSON 文件格式

你可以[在这里下载示例 JSON 文件](https://github.com/google-deepmind/alphafold/blob/main/server/example.json)；下面将说明该示例 JSON 文件的内容。

这个 JSON 文件由一个字典列表组成（即使只有一个字典，也必须放在单元素列表中），列表中的每个字典都包含一个作业描述。因此，你可以在一个 JSON 文件中定义多个作业。

每个作业描述都包含一个作业名称、一组 PRNG 种子（也可以为空列表，表示自动分配随机种子），以及一个待建模实体（分子）的列表。

AlphaFold Server 的 JSON 文件特别适合自动化重复性的建模任务（例如筛选一个蛋白与少量其他蛋白之间的相互作用）。构建初始 JSON 文件最简单的方法，是先通过 AlphaFold Server 图形界面运行一次建模作业，并将其作为模板。AlphaFold Server 会生成一个包含建模结果的 zip 文件；在 zip 文件中，你会找到一个名为 `<job_name>_job_request.json` 的 JSON 文件，其中包含作业输入。这些文件非常适合作为生成新作业的起点，因为它们既可在标准文本编辑器中方便地修改，也可在 Google Colab 笔记本等编程环境中编辑。

请注意，JSON 文件中不允许出现注释。

## 作业名称、种子与序列

*   `name`：字符串类型，表示作业名称。这也是该作业在作业历史表中显示的名称。
*   `modelSeeds`：uint32 种子值字符串列表（例如 `["1593933729", "4273"]`）。这些种子用于建模运行。我们建议提供空列表，此时系统会使用一个随机种子；这是推荐做法。
*   `sequences`：一个字典列表，用于描述参与建模的实体（分子）。

```json
{
  "name": "测试折叠任务一",
  "modelSeeds": [],
  "sequences": [...],
  "dialect": "alphafoldserver",
  "version": 1
}
```

## 实体类型

有效的实体类型与 AlphaFold Server Web 界面中可用的类型保持一致：

*   `proteinChain`：用于蛋白质
*   `dnaSequence`：用于 DNA（单链）
*   `rnaSequence`：用于 RNA（单链）
*   `ligand`：用于允许的配体
*   `ion`：用于允许的离子
*   `dialect`：输入 JSON 的方言类型，应设置为 `alphafoldserver`
*   `version`：输入 JSON 的版本号，应设置为 1。更多信息见下方[版本](#版本)一节。

## 版本

顶层 `version` 字段（针对 `alphafoldserver` 方言）可以是 `undefined` 或 `1`。不同版本中新增的特性如下：

*   未设置：AlphaFold Server 最初的输入格式。
*   `1`：新增了通过 `maxTemplateDate` 和 `useStructureTemplate` 字段指定外部模板的能力。

### 蛋白链

`sequence` 是一个包含蛋白质序列的字符串；限制条件与界面中一致，例如只允许使用 IUPAC 定义的氨基酸字母。目前仅支持 20 种标准氨基酸类型。

`count` 是该蛋白链的拷贝数量（整数）。

`glycans` 是一个可选字典列表，用于描述蛋白糖基化。

*   `residues`：定义聚糖的字符串。具体格式及允许的聚糖请参见 [FAQ](https://alphafoldserver.com/faq)。
*   `position`：聚糖连接到的氨基酸位置（整数，1 起始计数）。

`modifications` 是一个可选字典列表，用于描述翻译后修饰。

*   `ptmType`：字符串，表示修饰对应的 [CCD 代码](https://www.wwpdb.org/data/ccd)；允许的代码与界面一致。
*   `position`：被修饰氨基酸的位置（整数）。
*   允许的修饰：`CCD_SEP`、`CCD_TPO`、`CCD_PTR`、`CCD_NEP`、`CCD_HIP`、`CCD_ALY`、`CCD_MLY`、`CCD_M3L`、`CCD_MLZ`、`CCD_2MR`、`CCD_AGM`、`CCD_MCS`、`CCD_HYP`、`CCD_HY3`、`CCD_LYZ`、`CCD_AHB`、`CCD_P1L`、`CCD_SNN`、`CCD_SNC`、`CCD_TRF`、`CCD_KCR`、`CCD_CIR`、`CCD_YHA`

`useStructureTemplate` 是可选布尔值，表示模型是否应使用 PDB 模板，默认值为 `true`。

`maxTemplateDate` 是可选的 ISO 8601 日期字符串（YYYY-MM-DD），用于指定考虑 PDB 模板时的日期上限。只有在该日期或之前发布的模板会被使用。该日期的最小值为 1976-01-01（相当于切断所有模板），当前可设置的最大日期为 2025-02-03（用于生成模板时从 PDB 下载数据的最后日期）。

```json
{
  "proteinChain": {
    "sequence": "PREACHINGS",

    "glycans": [
      {
        "residues": "NAG(NAG)(BMA)",
        "position": 8
      },
      {
        "residues": "BMA",
        "position": 10
      }
    ],

    "modifications": [
      {
        "ptmType": "CCD_HY3",
        "ptmPosition": 1
      },
      {
        "ptmType": "CCD_P1L",
        "ptmPosition": 5
      }
    ],

    "count": 1,
    "maxTemplateDate": "2018-01-20"
  }
},
{
  "proteinChain": {
    "sequence": "REACHER",
    "count": 1,
    "useStructureTemplate": false
  }
}
```

### DNA 链

请注意，`dnaSequence` 类型指的是单链 DNA。如果你希望建模双链 DNA，请再添加一个 `"dnaSequence"`，并填写互补链的反向互补序列。

`sequence` 是 DNA 序列字符串；限制条件与界面一致，即只允许字母 A、T、G、C。

`count` 是该 DNA 链的拷贝数量（整数）。

`modifications` 是一个可选字典列表，用于描述 DNA 的化学修饰。

*   `modificationType`：字符串，表示修饰对应的 [CCD 代码](https://www.wwpdb.org/data/ccd)；允许的代码与界面一致。
*   `basePosition`：被修饰核苷酸的位置（整数）。
*   允许的修饰：`CCD_5CM`、`CCD_C34`、`CCD_5HC`、`CCD_6OG`、`CCD_6MA`、`CCD_1CC`、`CCD_8OG`、`CCD_5FC`、`CCD_3DR`

```json
{
  "dnaSequence": {
    "sequence": "GATTACA",

    "modifications": [
      {
        "modificationType": "CCD_6OG",
        "basePosition": 1
      },
      {
        "modificationType": "CCD_6MA",
        "basePosition": 2
      }
    ],

    "count": 1
  }
},
{
  "dnaSequence": {
    "sequence": "TGTAATC",
    "count": 1
  }
}
```

### RNA 链

`sequence` 是 RNA 序列字符串（单链）；限制条件与界面一致，例如只允许字母 A、U、G、C。

`count` 是该 RNA 链的拷贝数量（整数）。

`modifications` 是一个可选字典列表，用于描述 RNA 的化学修饰。

*   `modificationType`：字符串，表示修饰对应的 [CCD 代码](https://www.wwpdb.org/data/ccd)；允许的代码与界面一致。
*   `basePosition`：被修饰核苷酸的位置（整数）。
*   允许的修饰：`CCD_PSU`、`CCD_5MC`、`CCD_OMC`、`CCD_4OC`、`CCD_5MU`、`CCD_OMU`、`CCD_UR3`、`CCD_A2M`、`CCD_MA6`、`CCD_6MZ`、`CCD_2MG`、`CCD_OMG`、`CCD_7MG`、`CCD_RSQ`

```json
{
  "rnaSequence": {
    "sequence": "GUAC",
    "modifications": [
      {
        "modificationType": "CCD_2MG",
        "basePosition": 1
      },
      {
        "modificationType": "CCD_5MC",
        "basePosition": 4
      }
    ],
    "count": 1
  }
}
```

### 配体

`ligand` 是一个字符串，表示该配体的 [CCD 代码](https://www.wwpdb.org/data/ccd)；允许的代码与界面中一致。

`count` 是该配体的拷贝数量（整数）。

允许的配体包括：`CCD_ADP`、`CCD_ATP`、`CCD_AMP`、`CCD_GTP`、`CCD_GDP`、`CCD_FAD`、`CCD_NAD`、`CCD_NAP`、`CCD_NDP`、`CCD_HEM`、`CCD_HEC`、`CCD_PLM`、`CCD_OLA`、`CCD_MYR`、`CCD_CIT`、`CCD_CLA`、`CCD_CHL`、`CCD_BCL`、`CCD_BCB`

```json
{
  "ligand": {
    "ligand": "CCD_ATP",
    "count": 1
  }
},
{
  "ligand": {
    "ligand": "CCD_HEM",
    "count": 2
  }
}
```

### 离子

`ion` 是一个字符串，表示该离子的 [CCD 代码](https://www.wwpdb.org/data/ccd)；允许的代码与界面中一致。离子的电荷由 CCD 代码隐式指定。

`count` 是该离子的拷贝数量（整数）。

允许的离子包括：`MG`、`ZN`、`CL`、`CA`、`NA`、`MN`、`K`、`FE`、`CU`、`CO`

```json
{
  "ion": {
    "ion": "MG",
    "count": 2
  }
},
{
  "ion": {
    "ion": "NA",
    "count": 3
  }
}
```

# 其他建模任务

你可以在一个 JSON 文件中定义多个作业。下面是一个简单示例：一个蛋白链以及两份回文 DNA 序列的作业请求：

```json
{
  "name": "测试折叠任务二",
  "modelSeeds": [],
  "sequences": [
    {
      "proteinChain": {
        "sequence": "TEACHINGS",
        "count": 1
      }
    },
    {
      "dnaSequence": {
        "sequence": "TAGCTA",
        "count": 2
      }
    }
  ],
  "dialect": "alphafoldserver",
  "version": 1
}
```

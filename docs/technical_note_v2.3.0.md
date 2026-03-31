# AlphaFold v2.3.0

更新（2026-03-11）：补充了关于聚类过滤变更的说明。

本文技术说明介绍了为生成 AlphaFold v2.3.0 所做的代码与模型权重更新，其中包含更新后的训练数据。

我们在保持模型架构不变的前提下，使用新的训练截断日期 2021-09-30 对 AlphaFold-Multimer 的新权重进行了微调。此前发布的 AlphaFold 和 AlphaFold-Multimer 版本，训练时都只使用发布日期早于 2018-04-30 的 PDB 结构，该截断日期是为了与 2018 年 CASP13 评测开始时间对应。新的训练截断日期意味着训练数据量大约增加了 30%，更重要的是，它包含了更多大型蛋白复合物的数据。新的训练截止集包含的电子显微镜结构数量增加到了原来的 4 倍，而大型结构（超过 2,000 个残基）的总量也翻了一倍[^1]。由于大型结构数量显著增加，我们还可以把训练 crop（即用于训练 AlphaFold 的结构子集）大小从 384 个残基提高到 640 个残基。尽管我们沿用了先前 AlphaFold-Multimer 论文中的模型架构和训练方法，这些新的 AlphaFold-Multimer 模型预期会在大型蛋白复合物上显著提升准确率。

AlphaFold v2.3.0 的训练相较于之前的 AF-Multimer 版本，也采用了修改后的自蒸馏数据集。原始 AF-Multimer 自蒸馏集是基于聚类后的 MGnify 数据集构建的，并只保留了包含超过 10 条序列的聚类。对于 v2.3.0，仍然使用同一份聚类后的 MGnify 数据集，但过滤条件调整为保留包含超过 2 条序列的聚类。

这些模型最初是为了响应 CASP 组织方的请求而开发的，目的是更好地理解 CASP15 结构预测进展中的基线表现。由于它们在大型目标上的准确率显著提升，我们将其作为默认的多聚体模型发布。由于这些模型是作为基线开发的，因此我们在适配更大复合物的同时，尽量减少对既有 AlphaFold-Multimer 系统的改动。具体来说，我们将训练时使用的链数从 8 提高到 20，并将 5 个 AlphaFold-Multimer 模型中的 3 个模型的最大 MSA 序列数从 1,152 提高到 2,048。

对于 CASP15 基线，我们还采用了成本略高、但已被外部研究发现能提升 AlphaFold 准确率的推理设置。我们将每个模型的随机种子数量提高到 20[^2]，并把最大 recycle 次数提高到 20，同时启用提前停止[^3]。对于非常大或较困难的目标，推荐将随机种子数量增加到 20；但由于计算时间增加，这并不是默认设置。

总体来说，只要复合物的化学计量比已知，包括已知为单体的结构，我们预计这些新模型都会成为更优选择。而在化学计量比未知的场景下，例如全基因组规模预测，除非链长度达到数千个残基，否则平均而言单链 AlphaFold 可能会更准确。

用于 CASP15 基线的预测结构可在[这里](https://github.com/deepmind/alphafold/blob/main/docs/casp15_predictions.zip)获取。

[^1]: wwPDB Consortium. "Protein Data Bank: the single global archive for 3D
  macromolecular structure data." Nucleic Acids Res. 47, D520–D528 (2018).

[^2]: Johansson-Åkhe, Isak, and Björn Wallner. "Improving peptide-protein
  docking with AlphaFold-Multimer using forced sampling." Frontiers in
  bioinformatics 2 (2022): 959160-959160.

[^3]: Gao, Mu, et al. "AF2Complex predicts direct physical interactions in
  multimeric proteins with deep learning." Nature communications 13.1 (2022):
  1-13.

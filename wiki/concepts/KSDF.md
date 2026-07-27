---
title: "k-SDF"
type: concept
tags: [3d-rendering, neural-rendering]
---
# k-SDF

k-SDF (k-Signed Distance Function) 是 Volumetric Surfaces 提出的多层隐式几何表示。与传统单 SDF 不同，k-SDF 将场景建模为 k 个独立的有符号距离函数 {d₁,...,dₖ}，每个层代表一个表面壳，通过透明度场 α 实现半透明混合。

渲染方程为：

$$\mathcal{R}(\mathbf{r}) = \sum_{i=1}^{k} \mathcal{C}_i(\mathbf{r}) \, \mathcal{A}_i(\mathbf{r}) \, w_i$$

其中 $w_i = \prod_{j=1}^{i}(1 - \mathcal{A}_j(\mathbf{r}))$。

**壳层结构**：使用一个主表面 SDF d 和 k−1 个支持层作为可学习的偏移场。正偏移表示内部表面，负偏移表示外部表面。

**关键特性**：
- 排序无关渲染 — 壳层结构确保固定渲染顺序
- 自适应层间距 — 偏移量通过梯度优化自动学习
- 训练后烘焙为轻量网格 — marching cubes 提取零等值面后简化

详见 [[VolumetricSurfaces]]。
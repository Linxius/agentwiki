---
title: "Volumetric Surfaces: Representing Fuzzy Geometries with Layered Meshes"
type: source
tags: [paper]
date: 2026-07-28
source_file: raw/papers/arxiv-240902482-7d990975.md
url: "https://arxiv.org/abs/2409.02482"
venue: ""
published: 2024
links: []
---

## Summary

本文提出 Volumetric Surfaces（体积表面），一种用 k 个半透明网格壳层表示模糊几何的实时视图合成方法。核心思想是将体积渲染的"沿射线密集采样"问题转化为"仅在 k 个已知表面上采样"——每条射线只需与 3–9 个壳层相交（通过光栅化定位采样点），再按固定顺序混合，无需空空间跳过或深度排序。在 Samsung A52s 智能手机上 7-Mesh 达到 42 FPS（720p），Shelly 数据集 PSNR 34.50，显著优于单表面方法 [[MobileNeRF]]（29.30），渲染速度远超 [[3DGS]]。

## 原始出处

- 原始文件: [../../raw/papers/arxiv-240902482-7d990975.md](../../raw/papers/arxiv-240902482-7d990975.md)
- 原文链接: [https://arxiv.org/abs/2409.02482](https://arxiv.org/abs/2409.02482)
- 作者: Stefano Esposito, Anpei Chen, Christian Reiser, Samuel Rota Bulò, Lorenzo Porzi, Katja Schwarz, Christian Richardt, Michael Zollhöfer, Peter Kontschieder, Andreas Geiger
- 机构: University of Tübingen, Meta Reality Labs

## Key Contributions

- **k-SDF 多层表示**：将场景建模为 k 个独立的 SDF，每个层代表一个表面壳，层间距通过梯度优化自适应学习而非均匀间距
- **排序无关渲染**：支持层建模为壳层结构，所有网格按固定顺序从外到内光栅化，无需空空间跳过或深度排序
- **视角依赖透明度**：每层透明度随视角方向变化，在少量层数下增加表达力
- **混合分辨率纹理烘焙**：基色 2048² 纹理 + 高阶 SH 256² 纹理，约 14 MB/网格
- **移动端实时渲染**：7-Mesh 在 Samsung A52s 上 42 FPS（720p），Dell XPS 13 上 70 FPS

## Method

### 整体架构概览

![k-SDF 高层架构](https://arxiv.org/html/2409.02482v2/extracted/6298806/figures/model.png)

**图 3(a)** 展示了 k-SDF 网络架构：输入 3D 坐标，预测主 SDF 距离 d 和几何特征 z，通过多个小型 MLP 头预测相对偏移，累积求和得有序绝对偏移，输出 k 个距离值。

### k-SDF 几何表示

**整体思路**：单层 SDF 只能表示一个光滑表面，无法建模毛发等模糊材质的半透明效果。k-SDF 将场景建模为 k 个独立 SDF {d₁,...,dₖ}，每个层是一个表面壳，通过透明度场 α 实现半透明混合。

渲染方程推广为：

$$\mathcal{R}_\beta(\mathbf{r} \mid d_{1:k}, \alpha, \boldsymbol{\xi}) = \sum_{i=1}^{k} \mathcal{R}_\beta(\mathbf{r} \mid d_i, \boldsymbol{\xi}) \, \mathcal{R}_\beta(\mathbf{r} \mid d_i, \alpha) \, w_i$$

其中混合权重 $w_i = \prod_{j=1}^{i}(1 - \mathcal{R}_\beta(\mathbf{r} \mid d_j, \alpha))$，密度场由 logistic 分布函数 $\phi_\beta(d) = \beta e^{-\beta d} / (1 + e^{-\beta d})^2$ 从 SDF 距离推导。

**壳层结构**：使用一个主表面 SDF d 和 k−1 个支持层作为偏移场 {o₂,...,oₖ}。正偏移表示表面在主表面内部，负偏移在外部。对预测的相对偏移分别对正负方向做累积求和，得到有序的绝对偏移。

**每个表面的渲染**：对表面 j，分别渲染其颜色和透明度：

$$\mathcal{C}_j(\mathbf{r}) = \sum_{i=1}^{n} w_{i,j} \, \boldsymbol{\xi}(\mathbf{x}_i, \mathbf{v}, \mathbf{n}_{i,j}, \mathbf{z}_i)$$

$$\mathcal{A}_j(\mathbf{r}) = \sum_{i=1}^{n} w_{i,j} \, \alpha(\mathbf{x}_i, \mathbf{v}, \mathbf{n}_{i,j}, \mathbf{z}_i)$$

RGB 和透明度场 ($\boldsymbol{\xi}$, $\alpha$) 以样本位置、视角方向、SDF 法线和特征向量为条件。

### 表面混合与透明度衰减

**固定顺序混合**：渲染结果改写为固定顺序的 alpha 混合：

$$\mathcal{R}(\mathbf{r}) = \sum_{i=1}^{k} \mathcal{C}_i(\mathbf{r}) \, \mathcal{A}_i(\mathbf{r}) \, w_i,\quad w_i = \prod_{j=1}^{i}(1 - \mathcal{A}_j(\mathbf{r}))$$

**透明度衰减**：不同硬表面混合时在边界处产生截断伪影。将透明度乘以视角-法线夹角权重 $\alpha_\text{w} = 2 \cdot \text{Sigmoid}(10 \cdot |\mathbf{v} \cdot \mathbf{n}|) - 1$，在掠射角处降低贡献，避免边界伪影。

## Training

训练分为两个主要阶段：

### 阶段 1：隐式表面优化

1. **NeuS 预训练**：训练标准 NeuS 模型 100k 迭代，β 从宽密度指数调度到窄密度，防止额外几何被预测为完全透明
2. **k-SDF 训练**：从预训练表面初始化，均匀间距 Δo 设置支持层。Δo 由 logistic 分布标准差确定，确保密度仅部分重叠。训练 50k 迭代，直到所有表面建模为峰化密度，渲染退化为硬表面混合
3. **损失函数**：$\mathcal{L} = \mathcal{L}_\text{c} + \lambda_\text{e} \mathcal{L}_\text{e} + \lambda_\text{s} \mathcal{L}_\text{s}$，$\lambda_\text{e}=0.04$（Eikonal 损失），$\lambda_\text{s}=0.65$（曲率损失）
4. **占用网格**：256³ 分辨率，用于加速体渲染采样
5. **重要性采样**：扩展 NeuS 的分层采样到多表面情况，从 k 个 SDF 的 CDF 求和分布中采样

### 阶段 2：网格烘焙与纹理优化

1. **网格提取**：marching cubes 从 k-SDF 零等值面提取高分辨率网格，简化到 0.02% 原始三角数（约 2 MB/网格）
2. **UV 生成**：使用 xatlas 生成 UV 展开图
3. **神经纹理训练**：15k 迭代，每个表面训练视角相关外观模型。神经纹理实现为 2D hash-grid + 小型 MLP 解码器，输出 SH 系数
4. **混合分辨率**：基色（degree 0）2048²，最高 SH 阶 256²，约 14 MB/网格。低阶系数用高分辨率，高阶系数用低分辨率
5. **量化与烘焙**：Sigmoid 压缩至 [0,1]，round(255x)/255 量化到 [0,255]，再缩放至 [-15,15]。输出为 PNG 图像序列

## Results & Comparisons

**Shelly 数据集 — 移动端实时性能**

| 方法 | FPS (A52s) | FPS (XPS 13) | PSNR | 内存 |
|------|-----------|-------------|------|------|
| MobileNeRF | 24 | 35 | 29.30 | 194 MB |
| 3DGS | 8 | 18 | 35.44 | 57 MB |
| 3-Mesh | 65 | 145 | 33.39 | 46 MB |
| **7-Mesh** | **42** | **70** | **34.50** | **110 MB** |
| 9-Mesh | 35 | 55 | 34.38 | 140 MB |

**数据集综合对比**

| 方法 | Shelly PSNR | Custom PSNR | DTU PSNR |
|------|------------|------------|----------|
| 3DGS | 35.44 | 37.34 | 38.06 |
| AdaptiveShells | 36.02 | — | — |
| MobileNeRF | 29.30 | 30.89 | — |
| 7-Mesh | 34.50 | 35.63 | 36.77 |
| 9-Mesh | 34.38 | 35.74 | 37.17 |

**关键发现**：
- 7-Mesh 在质量与速度之间达到最佳平衡，9-Mesh 因深层表面梯度减小导致优化退化
- 在低端手机和笔记本上均满足实时渲染要求（>30 FPS）
- 质量落后于最新体素方法（3DGS）但在速度上有数量级优势
- 3DGS 在移动端无法满足实时要求（8 FPS），即使限制高斯数量也导致质量大幅下降

## Related Work Analysis

**实时视图合成**：本文定位于体渲染（[[3DGS]]、[[InstantNGP]]、[[SMERF]]）和表面渲染（[[MobileNeRF]]、[[BakedSDF]]）之间。体渲染需要大量采样点，表面渲染无法处理模糊几何。

**模糊几何表示**：[[PermutoSDF]] 通过多面体细分扩展 SDF 表示能力，但推理缓慢。[[AdaptiveShells]] 用窄带 SDF 和自适应空间变化核大小加快渲染速度，但仍需沿射线密集采样。本文通过将采样点固定到 k 个已知表面，从根本上减少了计算量。

**移动端实时渲染**：[[MobileNeRF]] 率先将 NeRF 烘焙为网格+纹理实现移动端渲染，但单表面无法表示毛发、植被等模糊材质。本文扩展为多层网格表示，在不增加渲染路径数量的情况下大幅提升模糊几何表现力。

**纹理烘焙技术**：继承自 [[MERF]] 的量化策略和 [[BakedSDF]] 的网格提取管线，创新性地提出混合分辨率 SH 纹理，将内存占用从 0.5 GB/网格降至 14 MB/网格。

## Ablations

| 消融项 | 5-SDF PSNR | 5-Mesh PSNR |
|--------|-----------|------------|
| Full | 32.05 | 34.25 |
| 1) 无视角依赖 α | 31.75 | 32.71 |
| 2) 无曲率损失 | 33.02 | 33.41 |
| 3) 无透明度衰减 | 32.11 | 33.96 |
| 4) 固定偏移 Δo | — | 30.09 |
| 5) 外部初始化 | — | 30.85 |

**关键结论**：
1. **视角依赖透明度**：移除后质量下降，因为降低了模型表达力
2. **曲率损失**：隐式阶段移除后 PSNR 上升（表面可重建高频细节），但烘焙后质量下降（网格与隐式表面对齐差）。曲率损失推动 k-SDF 重建更平滑表面，使网格更好地匹配隐式表面
3. **透明度衰减**：掠射角处无衰减时边界渲染误差显著增加
4. **固定偏移**：PSNR 大幅下降至 30.09，证明可训练的偏移对于适应场景层间距至关重要
5. **外部初始化**：几何膨胀超出物体轮廓，测试视角泛化差。内部初始化使表面更紧凑，防止不必要扩张

## Limitations

1. **掠射角伪影**：纹理壳层在掠射角处仍存在伪影，尤其是测试视角超出训练覆盖范围时。增加壳层数可缓解但增加计算和内存开销
2. **稀疏视角退化**：在稀疏采样场景中表现不佳，模型倾向于用视角依赖性解释观测而非多视图一致的几何
3. **薄结构困难**：底层 SDF 几何表示对薄结构处理能力有限
4. **实心表面优势有限**：对完全实心的表面相比单表面方法无显著优势

## Connections

- [[AdaptiveShells]]：同属高效渲染方法，AdaptiveShells 用窄带加速密集采样，VolumetricSurfaces 用 k 个固定表面替代密集采样
- [[3DGS]]：主要对比基线，3DGS 质量更高但在移动端无法实时（8 FPS vs 42 FPS）
- [[MobileNeRF]]：最直接的对比方法，同属移动端网格+纹理管线，但仅支持单表面
- [[PermutoSDF]]：SDF 扩展方法对比基线
- [[InstantNGP]]：通过 hash-grid 加速 NeRF
- [[MERF]]：继承了量化烘焙策略
- [[MetaRealityLabs]]：作者所属机构

## Contradictions

- 7-Mesh 在 Shelly 上质量低于 3DGS（34.50 vs 35.44），但移动端渲染速度大幅领先（42 FPS vs 8 FPS）
- 5-Mesh 烘焙后质量（34.25）显著高于 5-SDF 隐式阶段（32.05），说明固定几何+表面约束外观模型优于随机采样的 SDF
- 移除曲率损失在隐式阶段反而提升 PSNR（33.02 vs 32.05），但在烘焙后降低（33.41 vs 34.25），体现训练目标与最终部署目标的差异
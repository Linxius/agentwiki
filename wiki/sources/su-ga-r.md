---
title: "SuGaR: Surface-Aligned Gaussian Splatting for Efficient 3D Mesh Reconstruction and High-Quality Mesh Rendering"
type: source
tags: [paper]
date: 2026-07-28
source_file: raw/papers/arxiv-231112775-6b1b0a2c.md
url: "https://arxiv.org/abs/2311.12775"
venue: "SIGGRAPH Asia 2024"
published: 2024
links: ["https://github.com/Anttwo/SuGaR"]
---

## Summary

SuGaR 提出从 [[3D Gaussian Splatting]] 表示中高效提取高质量网格的方法。核心贡献包括：(1) 正则化项，促使 3D 高斯体沿场景表面排列并均匀分布；(2) 基于深度图的水平集采样 + [[Poisson表面重建]] 的快速网格提取算法，在数分钟内完成而非数小时；(3) 将新高斯体绑定到网格三角形上的联合优化策略，实现可编辑的高质量渲染。SuGaR 在保持实时渲染速度的同时，网格重建质量和渲染质量均优于依赖 [[神经隐式表面|Neural SDF]] 的同类方法（训练仅需 15-45 分钟，网格提取 5-10 分钟）。

## 原始出处

- 原始文件: [raw/papers/arxiv-231112775-6b1b0a2c.md](../../raw/papers/arxiv-231112775-6b1b0a2c.md)
- 原文链接: [https://arxiv.org/abs/2311.12775](https://arxiv.org/abs/2311.12775)
- 作者: Antoine Guedon, Vincent Lepetit (LIGM, Ecole des Ponts, Univ Gustave Eiffel, CNRS, France)
- 发表会议: SIGGRAPH Asia 2024
- 代码: [https://github.com/Anttwo/SuGaR](https://github.com/Anttwo/SuGaR)

## Key Contributions

1. **表面对齐正则化**：从高斯体导出一个 SDF，通过最小化理想 SDF 与真实 SDF 之间的差异以及法线一致性损失，促使高斯体沿表面排列、扁平化、不透明度接近二值化。
2. **高效网格提取**：利用训练视角的深度图采样水平集上的 3D 点，使用线性插值精确定位等值面，结合点法线进行 [[Poisson表面重建]]，避免 Marching Cubes 在高稀疏密度场中的失败问题。
3. **网格绑定高斯体联合优化（可选）**：将薄高斯体绑定到网格三角形上（用重心坐标和平面参数化），联合优化网格顶点和高斯参数，通过高斯泼溅渲染提升网格渲染质量，并支持网格编辑工具操作高斯场景。

## Method

### 整体架构概览

![方法概述](https://arxiv.org/html/2311.12775v3/assets/x2.png)
*图2：SuGaR 管线概览。首先在 3DGS 优化中加入正则化项使高斯体对齐表面；然后从深度图中采样水平集点，经 Poisson 重建提取网格；最后将新高斯体绑定到网格上联合优化。*

SuGaR 的核心思路是：既然 3D 高斯泼溅渲染速度快、质量高，但它产生的数百万高斯体无序分布无法直接提取网格，那么能否引导高斯体在学习渲染的同时也学会排列在表面上？本文从三个步骤解决这一挑战：(1) 在优化过程中施加正则化，使高斯体沿表面对齐；(2) 利用对齐后的高斯体系数场快速找到表面位置；(3) 将网格变成高斯体的载体，实现可编辑的高质量渲染。

### 4.1 表面对齐正则化

**直觉**：未经正则化的 3DGS 优化后，高斯体散落在空间中（如图 3 所示），密度场没有明确的结构。如果高斯体扁平、沿表面排列、彼此少重叠，那么密度场就会接近一个理想化的表面密度函数。因此可以构造一个"理想 SDF"，通过最小化当前密度场对应的 SDF 与理想 SDF 的差异来促使高斯体对齐。

**细节**：

高斯体的密度函数定义为：

$$d(p)=\sum_{g}\alpha_{g}\exp\left(-\frac{1}{2}(p-\mu_{g})^{T}\Sigma^{-1}_{g}(p-\mu_{g})\right)$$  (Eq. 1)

在理想情况下（高斯体扁平、沿表面对齐、$\alpha_g=1$），密度可由最近高斯体主导：

$$\bar{d}(p)=\exp\left(-\frac{1}{2s_{g^{*}}^{2}}\langle p-\mu_{g^{*}},n_{g^{*}}\rangle^{2}\right)$$  (Eq. 5)

定义理想距离函数：

$$f(p)=\pm s_{g*}\sqrt{-2\log\left(d(p)\right)}$$  (Eq. 7)

正则化项：

$$\mathcal{R}=\frac{1}{|\mathcal{P}|}\sum_{p\in\mathcal{P}}|\hat{f}(p)-f(p)|$$  (Eq. 8)

其中 $\hat{f}(p)$ 是通过深度图估计的点到表面距离（从训练视角渲染高斯体深度图，$\hat{f}(p)$ 为点 $p$ 的深度与深度图投影点深度的差值）。

此外加入法线一致性正则化：

$$\mathcal{R}_{\text{Norm}}=\frac{1}{|\mathcal{P}|}\sum_{p\in\mathcal{P}}\left\|\frac{\nabla f(p)}{\|\nabla f(p)\|_{2}}-n_{g^{*}}\right\|_{2}^{2}$$  (Eq. 10)

采样策略：沿高斯分布采样 3D 点，使梯度主要集中在高斯体附近。

### 4.2 高效网格提取

**直觉**：对齐后的高斯体产生一个在表面附近有明确结构的密度场。水平集 $\{p: d(p)=\lambda\}$ 对应了表面位置。Marching Cubes 在稀疏密度场上失败（因为大部分区域密度接近 0），因此本文改用：从深度图出发，沿视线搜索水平集交点 → 线性插值精确定位 → Poisson 重建。

**细节**：

![水平集采样](https://arxiv.org/html/2311.12775v3/assets/x6.png)
*图6：水平集点采样方法。左图：从深度图采样像素点，沿视线搜索密度从低于$\lambda$跨越到高于$\lambda$的位置，通过线性插值找到精确水平集位置。右图：有无联合优化的网格对比。*

1. 从每个训练视角的深度图中随机采样像素
2. 对每个像素 $m$，沿视线方向 $v$ 在 $[-3\sigma_g(v), 3\sigma_g(v)]$ 范围内均匀采样 $n$ 个点 $p+t_i v$
3. 计算这些点的密度值 $d_i$，若存在 $i,j$ 使 $d_i < \lambda < d_j$，则判定存在水平集交点
4. 通过线性插值计算精确交点位置 $t^*$
5. 法线取为密度梯度的归一化方向 $\frac{\nabla d(\hat{p})}{\|\nabla d(\hat{p})\|_{2}}$
6. 对全部采样点运行 Poisson 重建（depth=10），得到三角网格
7. 使用二次误差度量进行网格简化

默认参数：$\lambda=0.3$，Poisson depth=10，网格提取耗时 5-10 分钟。

### 4.3 网格绑定高斯体联合优化

**直觉**：直接从高斯体提取的网格虽然质量高，但渲染时丢失了高斯体的细节表现能力。因此将高斯体绑定到网格三角形上，联合优化网格顶点和高斯参数，既保留了网格的拓扑结构，又保持了高斯泼溅的高质量渲染。

**细节**：

![网格绑定高斯体](https://arxiv.org/html/2311.12775v3/assets/x9.png)
*图7：联合优化示意图。左：将高斯体绑定到网格三角形上（用预定义重心坐标采样）。右：联合优化前后的网格对比。*

1. 对每个三角形采样 $n$ 个薄高斯体，其均值由三角形顶点和固定的重心坐标决定
2. 高斯体参数化修改：仅 2 个可学习缩放因子（原为 3），1 个可学习 2D 旋转（复数编码，替代四元数），保持高斯体扁平且贴合三角形
3. 同时优化网格顶点位置和高斯参数（不透明度、球谐系数）
4. 训练后移除不透明度低于 0.5 的高斯体，再执行 6000 次迭代含正则化项
5. 联合优化迭代次数可选 2000/7000/15000，耗时数分钟到 1 小时

## Training

- **三阶段训练流程**：
  1. 标准 3DGS 训练 7000 次迭代（无正则化），让高斯体自由定位
  2. 附加不透明度熵损失训练 2000 次迭代，促使 $\alpha_g$ 二值化
  3. 移除 $\alpha<0.5$ 的高斯体后，加入表面对齐正则化继续训练 6000 次迭代
- 密度计算时仅考虑每个点的 16 个最近高斯体，每 500 次迭代更新邻居列表
- 全部优化在单张 NVIDIA Tesla V100 (32GB) 上完成，总训练时间 15-45 分钟
- 网格提取使用 $\lambda=0.3$，Poisson depth=10，耗时 5-10 分钟

## Results & Comparisons

### Mip-NeRF360 数据集渲染质量

| 方法 | PSNR | SSIM | LPIPS |
|------|------|------|-------|
| 3DGS (vanilla) | 27.21 | 0.815 | 0.214 |
| SuGaR + 网格绑定（15K 迭代） | 27.50 | 0.838 | 0.174 |
| MobileNeRF | 23.33 | 0.630 | 0.471 |
| BakedSDF | 24.84 | 0.725 | 0.348 |

SuGaR 在使用网格的方法中表现最佳，且 R-SuGaR（联合优化后）在某些场景 PSNR 甚至超过 3DGS 基线。

### 网格提取质量对比（DTU 数据集）

| 方法 | Chamfer |
|------|---------|
| SuGaR ($\lambda=0.3$) | 0.81 |
| NeuS | 0.81 |
| VolSDF | 0.91 |
| Marching Cubes on 3DGS 密度场 | 2.53 |

SuGaR 的网格质量与 SOTA 神经 SDF 方法相当，但训练时间从 24+ 小时缩减到 30 分钟内。

### 速度对比

| 方法 | 训练时间 | 网格提取时间 |
|------|----------|-------------|
| BakedSDF | 48 小时 | 集成在训练中 |
| NeRFMeshing | ~8 小时 (8xV100) | ~1 小时 |
| **SuGaR** | **15-45 分钟** | **5-10 分钟** |

## Related Work Analysis

### vs [[Adaptive Shells|Adaptive Shells for Efficient NeRF Rendering]]

两者目标都是加速从一个已训练的场景表示中提取表面，但出发点和路径不同：
- Adaptive Shells 基于 NeRF/NeuS 的隐式 SDF，通过水平集演化提取自适应窄带，窄带内采样加速渲染。SuGaR 则基于 3DGS 的显式高斯体，通过正则化使其对齐表面，利用深度图采样水平集。
- Adaptive Shells 的核心优势是渲染加速（5x），SuGaR 的核心优势是网格提取速度（分钟级 vs 小时级）和编辑能力。
- 共同点：都利用深度图或 SDF 水平集来定位表面位置。

### vs [[Volumetric Surfaces|Volumetric Surfaces: Representing Fuzzy Geometries with Layered Meshes]]

- Volumetric Surfaces 用多层透明网格表示模糊几何，渲染时用少量采样点（3-9 个）实现实时视图合成，面向的是模糊/半透明物体的表示。SuGaR 面向的是固体表面的精确网格重建和高质量渲染。
- 两者都强调网格的可编辑性，但 SuGaR 的网格更适用于需要精确几何的场景。

### vs BakedSDF / NeRFMeshing

- 这些方法先从 NeRF/SDF 训练再"烘焙"到网格上，训练时间很长（24-48 小时）。SuGaR 直接从 3DGS 出发，训练+提取在 30 分钟内完成。
- SuGaR 的渲染质量（PSNR 27.50）显著高于 BakedSDF (24.84) 和 MobileNeRF (23.33)，因为高斯体保留了比传统纹理贴图更丰富的视差外观信息。

## Ablations

1. **正则化项的必要性**：无正则化时，Marching Cubes 完全无法提取可用网格；深度图采样+Poisson 重建虽可得到网格，但质量较差（噪声多、缺失细节）。
2. **$\lambda$ 参数影响**：$\lambda=0.3$ 效果最佳（Chamfer 距离最低）；$\lambda$ 过小导致网格偏离表面，过大导致网格内缩。
3. **SDF 损失 vs 密度损失**：使用 SDF 损失（Eq. 8）比直接用密度差异损失对齐效果更好，网格质量更高。
4. **联合优化迭代数**：2000 次迭代即可显著提升渲染质量；7000-15000 次迭代进一步提升但收益递减。
5. **网格分辨率**：从 200K 到 1M 顶点，渲染质量稳步提升，但收益呈递减趋势。

## Limitations

- 模糊/半透明区域的处理不如纯 NeRF 方法：正则化强制高斯体二值化和扁平化，降低了表示半透明效果的能力。
- 网格提取依赖训练视角的深度图，对视角覆盖不充分的区域（如物体底部）可能产生不完整的网格。
- 联合优化阶段的计算量较大（最长 1 小时），虽然相比 NeRF 方法仍然很快。
- 网格编辑后的效果依赖于重新渲染时的视差外观模型，极端编辑下可能出现伪影。

## Connections

- [[3D Gaussian Splatting]] — SuGaR 直接构建在 3DGS 之上，修改其优化目标和渲染管线
- [[Poisson表面重建|Poisson Surface Reconstruction]] — 核心网格提取算法
- [[Adaptive Shells]] — 同为从辐射场中提取表面用于加速/编辑的方法，但基于 NeRF 而非 3DGS
- [[Volumetric Surfaces]] — 同为网格+体积混合表示，但面向模糊几何
- [[神经隐式表面|Neural SDF]] — SuGaR 在表面提取质量上与之相当，但速度快两个数量级
- Antoine Guedon — 第一作者
- Vincent Lepetit — 通讯作者，LIGM，Ecole des Ponts

## Contradictions

- SuGaR 声称从 3DGS 提取网格的速度和精度可以匹敌甚至超越 [[神经隐式表面|Neural SDF]] 方法（NeuS/VolSDF），但这是以牺牲半透明和模糊区域的建模能力为代价的。这意味着 SuGaR 的"网格提取精度"与 Neural SDF 方法测量的并非完全相同的质量维度。

---
title: "RaDe-GS: Rasterizing Depth in Gaussian Splatting"
type: source
tags: [paper]
date: 2026-07-30
source_file: raw/papers/RaDe-GS-Rasterizing-Depth-in-Gaussian-Splatting.md
url: "https://arxiv.org/abs/2406.01467"
venue: ""
published: 2024
links: []
---

## Summary

RaDe-GS 提出一种在通用 3D 高斯泼溅（3D-GS）上栅格化计算逐像素深度与法线的方法，使 3D-GS 既能保持实时新视角合成，又能高精度重建三维表面并提取网格。其核心利用透视投影下光线与 3D 高斯"交点"的闭式解，以及 GS 局部仿射投影下交点近似共面的性质，将深度计算转化为可栅格化的线性形式，避免了 3D-GS 原始方法中用中心深度近似几何的粗糙问题。

## 原始出处

- 原始文件: [raw/papers/RaDe-GS-Rasterizing-Depth-in-Gaussian-Splatting.md](../../raw/papers/RaDe-GS-Rasterizing-Depth-in-Gaussian-Splatting.md)
- 原文链接: [https://arxiv.org/abs/2406.01467](https://arxiv.org/abs/2406.01467)
- Brief 条目: [brief.md 2026-07-29 > RaDe-GS: Rasterizing Depth in Gaussian Splatting](../../raw/digest/brief.md)
- 深度阅读报告: N/A

## Key Contributions

- 推导透视投影下光线与 3D 高斯"交点"的闭式解（t* 为高斯值最大处）
- 利用 GS 局部仿射投影证明光线空间交点近似共面，将深度表达为可栅格化的线性形式 $d = z_c + \mathbf{p} \cdot (\Delta u, \Delta v)$
- 由共面方程求光线空间法线，再通过仿射变换矩阵 J 变换回相机空间得到逐像素 3D 法线
- 训练后融合各视角深度图至 TSDF 体，用 Marching Cubes 提取网格

## Method

RaDe-GS 的核心思想是让通用 3D 高斯具备可栅格化的深度/法线计算能力，像传统光栅化一样逐像素算几何，而不是用慢速光线追踪或粗糙的中心深度近似。

### 整体架构概览

3D-GS 原始方法用高斯中心深度 $z_c$ 近似几何，导致表面粗糙噪声。RaDe-GS 的做法是：推导光线与每个高斯的精确"交点"，利用局部仿射投影下这些交点近似共面的性质，将深度计算转化为可在光栅化管线中高效计算的形式。

### 逐像素深度栅格化

**直觉**：传统 3D-GS 渲染时每个高斯贡献一个颜色，但几何信息只用中心深度 $z_c$ 近似，精度低。RaDe-GS 推导光线与高斯的精确交点，并证明在光线空间中这些交点近似共面，因此可以用线性公式表达深度。

**细节**：

1. **闭式解交点**：在透视投影下，光线与 3D 高斯的"交点"定义为高斯值最大处，可得闭式解 $t^*$。

2. **线性深度公式**：利用 GS 的局部仿射投影，证明在光线空间中交点近似共面，得到深度公式：
   $$d = z_c + \mathbf{p} \begin{pmatrix} \Delta u \\ \Delta v \end{pmatrix}$$
   其中 $z_c$ 是高斯中心深度，$\mathbf{p}$ 是空间变化深度参数，$(\Delta u, \Delta v)$ 是相对像素位置。该形式可直接光栅化。

3. **补充推导**（附录）：证明 $z_c$ 项来源于 $\hat{\mathbf{p}}(0,0,t_c)^\top$ 的简化，其中 $\hat{\mathbf{p}}$ 包含高斯协方差在光线空间的信息。

### 逐像素法线计算

**直觉**：有了共面深度公式后，法线就是该平面的法向。在光线空间求法线后再变换回相机空间，得到逐像素 3D 法线。

**细节**：

1. 由共面方程 $d = z_c + \mathbf{p} \cdot (\Delta u, \Delta v)$ 对 $(\Delta u, \Delta v)$ 求偏导，得到光线空间法线。

2. 通过仿射变换矩阵 J（GS 的局部投影矩阵）将光线空间法线变换回相机空间，得到逐像素 3D 法线。

3. 法线用于几何一致性损失和网格提取。

### 网格提取

训练完成后，渲染各视角深度图，融合进 TSDF（Truncated Signed Distance Function）体，用 Marching Cubes 提取三角网格。

## Training

- **损失函数**：
  - 光度损失 $L_c$（标准 3D-GS L1 + SSIM）
  - 深度畸变损失 $L_d$：约束渲染深度与几何一致性
  - 法线一致性损失 $L_n$：约束渲染法线与几何法线一致
  - 总损失：$L = L_c + \lambda_d L_d + \lambda_n L_n$

- **训练策略**：在标准 3D-GS 训练流程上增加深度和法线约束，不需要额外数据。

- **数据需求**：多视角图像（与 3D-GS 相同），不需要深度或法线标注。

## Results & Comparisons

**DTU 表面重建**（Chamfer Distance，越小越好）：

| 方法 | CD (mm) |
|------|---------|
| RaDe-GS | 0.68 |
| GOF | 0.74 |
| 2D GS | 0.80 |
| Neuralangelo | 0.61 |

RaDe-GS 优于 GOF 和 2D GS，与 Neuralangelo 接近。

**Tanks&Temples F1**（TSDF 融合类）：0.40，达到该类方法最优。

**新视角合成质量**：
- Synthetic-NeRF PSNR: 33.60（最优）
- Mip-NeRF360 LPIPS: 最优

**训练速度**：DTU 约 8.3 分钟，Tanks&Temples 约 11.5 分钟，远快于 NeRF 类方法（12+ 小时）。

**对比 3D-GS**：3D-GS 本身不能提取高质量网格（需后处理 TSDF 融合），RaDe-GS 在保持 3D-GS 实时渲染的同时，表面重建精度接近隐式方法（Neuralangelo）。

**对比 GOF/GSDF**：GOF 和 GSDF 用光线追踪计算几何，计算开销大；RaDe-GS 用栅格化替代光线追踪，速度更快。

## Ablations

- **深度栅格化 vs 中心深度近似**：去掉深度栅格化（退化为原始 3D-GS），DTU CD 从 0.68 上升到 0.80+（与 2D GS 相当），证明栅格化深度对表面重建至关重要。
- **法线一致性损失**：去掉 $L_n$ 后网格法线质量下降，Marching Cubes 提取的网格表面更粗糙。
- **TSDF 融合分辨率**：高分辨率 TSDF 体可获得更精细网格，但受显存限制。

## Limitations

- 大规模场景 TSDF 融合受显存限制，只能用低分辨率体素，影响网格精细度
- 对高反射表面处理仍困难（与 3D-GS 共同局限），作者建议结合多分辨率 TSDF 与 GaussianShader 类着色改进
- 深度/法线计算依赖局部仿射投影假设，极端透视下精度下降

## 评论与启示

- RaDe-GS 巧妙地将 3D-GS 从"仅支持新视角合成"扩展到"同时支持高精度表面重建"，在不牺牲渲染速度的前提下填补了 3D-GS 在几何重建方面的短板
- 栅格化深度计算的思想可以推广到其他 3D-GS 变体（如 2D-GS、3DGS-MCMC 等）
- 与 SuGaR 不同：SuGaR 从 3D-GS 提取网格时牺牲了渲染质量，RaDe-GS 在训练过程中就约束几何，保持渲染质量不变
- 与 SDFRaster 对比：SDFRaster 用可光栅化 SDF 端到端重建网格，RaDe-GS 在已有 3D-GS 上增加深度栅格化，后者更轻量但精度略低

## Connections

- [[SuGaR: Surface-Aligned Gaussian Splatting]] — SuGaR 从 3D-GS 提取网格但牺牲渲染质量；RaDe-GS 在训练中约束几何保持画质
- [[SDFRaster]] — 用可光栅化 SDF 端到端重建网格，与 RaDe-GS 的栅格化深度思想相通
- [[Ref-DGS: Reflective Dual Gaussian Splatting]] — Ref-DGS 处理镜面反射表面重建，RaDe-GS 对高反射表面处理困难
- [[GS-2M: Material-aware Gaussian Splatting for High-fidelity Mesh Reconstruction]] — GS-2M 用材料感知联合优化实现反射表面高质量网格重建

## Contradictions

- (none)

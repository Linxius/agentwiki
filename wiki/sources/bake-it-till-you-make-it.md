---
title: "Bake It Till You Make It: Ultrafast Spatial Texture-Atlas Splatting"
type: source
tags: [paper]
date: 2026-07-28
source_file: raw/papers/Bake-It-Till-You-Make-It-Ultrafast-Spatial-Texture-Atlas-Splatting.md
url: "https://arxiv.org/abs/2607.13808"
venue: ""
published: 2026
links: []
---

## Summary

本文提出一种基于纹理图集的高效新视角合成方法，将视图无关的神经哈希网格烘焙为紧凑 RGB 纹理图集，实现超快速光栅化渲染。核心思路：将场景外观分解为**每原语的视角相关颜色**（球面 Voronoi）+ **视图无关的高频纹理残差**（多分辨率哈希网格 + MLP）。训练后通过烘焙将哈希网格转为纹理图集，推理时仅需硬件加速的 2D 纹理查找，消除了神经场查询的计算瓶颈。引入衰减减少正则化器（Falloff Reduction）进一步优化几何稀疏性。在消费级硬件上实现 4K@60FPS 实时渲染，比 [[3DGS]] 快 5 倍。

## 原始出处

- 原始文件: [raw/papers/Bake-It-Till-You-Make-It-Ultrafast-Spatial-Texture-Atlas-Splatting.md](../../raw/papers/Bake-It-Till-You-Make-It-Ultrafast-Spatial-Texture-Atlas-Splatting.md)
- 原文链接: [https://arxiv.org/abs/2607.13808](https://arxiv.org/abs/2607.13808)

## Key Contributions

1. **视图无关神经场 + 稀疏优化**：用多分辨率哈希网格编码视图无关颜色，产生紧凑 surfel 集合
2. **纹理烘焙管线**：将哈希网格烘焙为 RGB 纹理图集（BC7 压缩），利用 GPU 原生纹理采样
3. **衰减减少正则化器**：约束 Beta 核的 falloff，降低碎片重绘和几何体素数量
4. **高性能渲染**：实现 4K@60FPS（MacBook M3 Pro）和 720p（Samsung Galaxy S24 Ultra）

## Method

![方法总览](images/bake-it-till-you-make-it/fig1.png)

### 整体思路

近期方法（[[NeST-Splatting]]、[[Hybrid Latents]]）使用哈希网格 + 每原语特征解耦几何与外观，大幅减少原语数量。但推理时每个片段都要查询神经场和 MLP，成为计算瓶颈。本文的关键洞察：**将视图无关的纹理残差在训练后烘焙为纹理图集**，推理时只需硬件纹理采样，消除神经查询开销。

### 可微 Surfel 溅射

基于 [[2D Gaussian Splatting (2DGS)]] 的平面 surfel 表示。每个 surfel $i$ 由位置 $\mu_i$、旋转 $q_i$、二维缩放 $s_i$ 和不透明度 $o_i$ 参数化：[[]]

$$C=\sum_{i=1}^{N}c_i(x)\sigma_i\prod_{j=1}^{i-1}(1-\sigma_j),\quad \sigma_i=\alpha_i G(x)$$

### 可变形 Beta 核

替换标准高斯核为 [[Beta 分布]]，通过可学习参数 $b$ 在高斯分布和不透明平面盘之间变形：

$$\mathcal{B}(x;b)=(1-x)^{\beta(b)},\quad \beta(b)=4\sigma(b),\quad x\in[0,1]$$

大 $b$：软 Gaussian 元素；小 $b$：硬边平面盘，减少重绘。

### 空间纹理图集溅射

外观分解为两个组件：

1. **每原语视角相关颜色** $f_{SV}(\mathbf{d})$：使用软球面 Voronoi 表示，$K$ 个方向站点 $s_k$ 存储可学习颜色 $c_k$
2. **视图无关纹理残差** $\boldsymbol{\rho}(\mathbf{x})=f_\phi(E_\theta(\mathbf{x}))$：多分辨率哈希网格 $E_\theta$ + 视无关 MLP $f_\phi$

最终颜色：
$$\mathbf{c}(\mathbf{x},\mathbf{d})=\mathrm{ReLU}\big(\mathrm{ReLU}(f_{SV}(\mathbf{d})+b_{SV})+f_\phi(E_\theta(\mathbf{x}))\big)$$

### 纹理烘焙

训练后，哈希网格在每个 surfel 表面采样，烘焙到全局 RGB 纹理图集：

1. **各向异性 UV 分辨率**：$r_{g,a}=\mathrm{clamp}\left(2^{\lceil\log_2(4es_{g,a}/\delta)\rceil}, r_{\min}, r_{\max}\right)$，各向异性节省约 30% 图集面积
2. **图集打包**：Shelf-First-Fit-Decreasing 算法，$W=4096$，$H$ 自适应增长
3. **BC7 块压缩**：1 字节/纹素，平均图集 ~638MB

推理时硬件纹理单元直接采样 BC7 块，反量化后加到视角相关颜色上。

## Optimization

### 多视角误差优化

采用 FastGS 的视角一致性致密化和剪枝策略。$s_d^i = \frac{1}{K}\sum_{j=1}^{K}\sum_{p\in\Omega_i}\mathbb{I}(\mathcal{M}^{j}_{\text{mask}}(p)=1)$

### 衰减减少（Falloff Reduction）

误差加权的 Beta 衰减正则化器：
$$\omega(p)=\exp(-\gamma\,\|\mathbf{C}(p)-\hat{\mathbf{C}}(p)\|_1)$$
$$\mathcal{L}_\beta = \frac{1}{|P|}\sum_{p\in P}\omega(p)\,\bar{\beta}(p)$$

仅在重建收敛后自动激活，将软高斯核拉向硬边圆盘。

## Results & Comparisons

| 方法 | Mip-NeRF 360 PSNR | 原语数 | FPS |
|-----|-------------------|--------|-----|
| 3DGS | 27.21 | 2.7M | 134 |
| 2DGS | 27.04 | 2.0M | 64 |
| NeST-Splatting | 26.68 | 1.0M | 23 |
| Hybrid Latents | 26.85 | 0.2M | 36 |
| BBSplat | 26.98 | 0.4M | 25 |
| FastGS | 27.56 | 0.40M | 942 |
| Ours (falloff) | **26.75** | **0.14M** | **664** |

Tanks & Temples 上 PSNR 24.14，FPS 1094（falloff 版本）。训练约 45 分钟。

## Related Work Analysis

与 [[NeST-Splatting]]、[[Hybrid Latents]]、[[Nexels]] 等混合表示方法的关键差异：这些方法在推理时仍需神经场查询，速度低于 3DGS；本文通过烘焙为纹理图集，推理仅依赖硬件纹理采样，达到甚至超过 3DGS 的速度。

与 [[BBSplat]] 的差异：BBSplat 使用每原语显式 RGB 纹理，内存随分辨率线性增长；本方法用全局哈希网格 + 烘焙图集，更高效。

## Ablations

- **Falloff 正则化**：λ=0.005 时原语数从 259K 降至 175K，FPS 从 317 提升至 622
- **视角相关特征**：球面 Voronoi（SV）优于 SH 和球面 Beta，PSNR 31.94 vs 30.88（SH）
- **BC7 量化**：相比 FP16 RGB，质量损失仅 ±0.01dB PSNR，内存从 3.8GB 降至 638MB

## Limitations

- 每个片段的哈希网格前向/反向在训练时仍是瓶颈
- 纹理图集内存仍然较大（~638MB），需要更高效的空间映射
- 需要进一步优化纹理坐标计算的效率

## Connections

- [[3D Gaussian Splatting (3DGS)]] — 基础光栅化框架
- [[2D Gaussian Splatting (2DGS)]] — 平面 surfel 表示
- [[NeST-Splatting]] — 混合哈希网格 + 高斯方法
- [[Hybrid Latents]] — 每原语特征 + 哈希网格
- [[FastGS]] — 多视角一致剪枝策略
- [[Beta-Splatting]] — 可变形 Beta 核

## Contradictions

- 与纯每原语颜色方法（3DGS，2DGS）对立：外观不应完全由每原语属性承载，需要全局纹理残差
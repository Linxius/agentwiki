---
title: "Sparse Voxels Rasterization: Real-time High-fidelity Radiance Field Rendering"
type: paper
tags: [Gaussian Splatting, Voxel Rasterization, Morton Order, Octree, Neural-free Rendering, Mesh Extraction]
date: 2026-08-04
source_file: raw/papers/input.md
url: https://arxiv.org/abs/2412.04459
links: []
---

## Summary

本文提出 **SVRaster**，一种不依赖神经网络或 3D 高斯的辐射场渲染方法，使用自适应稀疏体素模型。核心创新是**方向相关的 Morton 排序**实现正确深度排序，避免 3DGS 的 popping artifact。体素通过 Octree 布局自适应分配到不同细节层级，支持体积融合、体素池化和 Marching Cubes 网格提取。在 Mip-NeRF360 数据集上 LPIPS 为 0.185（优于 3DGS 的 0.216），渲染速度达 121 FPS（与 3DGS 的 131 FPS 相当），训练时间仅 15 分钟。

## 原始出处

- 原始文件: [raw/papers/input.md](../../raw/papers/input.md)
- 原文链接: [https://arxiv.org/abs/2412.04459](https://arxiv.org/abs/2412.04459)
- Brief 条目: [brief.md](#) — 2026-08-04 digest 条目 2
- 深度阅读报告: N/A

## Key Contributions

1. **神经自由体素渲染**：完全显式的体素表示，无需 MLP 或 3D 高斯，即可达到 SOTA 可比的新视角合成质量。
2. **方向相关 Morton 排序**：基于射线方向的 8 种 Morton 排列实现正确深度排序，彻底消除 popping artifact。
3. **自适应稀疏体素**：Octree 布局支持不同细节层级的自适应分配，最大分辨率 $65536^3$ 网格下仍保持高效渲染。
4. **无缝集成经典 3D 处理**：支持 Volume Fusion、Voxel Pooling 和 Marching Cubes，可直接提取高质量网格。

## Method

### 框架图

```
[SVRaster 渲染管线]

[场景表示]
  Octree 布局 → 自适应稀疏体素 {v_geo, v_sh}
    ├─ v_geo: 8 角点密度参数 → trilinear → explin → 密度场
    ├─ v_sh: 球谐系数 → 视角相关颜色
    └─ v_n: 密度场梯度 → 法线
            ↓
[体素光栅化]
  1. 投影 8 角点到图像空间 → 分配到 tile
  2. 根据射线方向符号选择 Morton 排列类型（8 种）
  3. 按 Morton 码排序 → 正确深度顺序
  4. Alpha 混合 → 像素颜色
            ↓
[后处理]
  Volume Fusion / Voxel Pooling / Marching Cubes → 网格
```

### 双重写作

**问题**：3DGS 中基于基元中心的排序不能保证正确的深度顺序，导致 popping artifact（一致几何下的突然颜色变化）。同时，多个高斯覆盖的 3D 点体密度定义不明确，使表面重建变得困难。

**解决思路**：利用体素的固有结构特性——3D 空间被划分为不相交的体素，配合方向相关的 Morton 排序可保证正确的渲染顺序。同时，显式的体密度场使表面提取变得直接。

**具体方法**：

**1. 体素场景表示**

体素通过 Octree 层级 $l \in [1, L]$（$L=16$）和网格索引 $v = \{i,j,k\} \in [0, \ldots, 2^L - 1]^3$ 定义：

$$\mathbf{v}_s = \mathbf{w}_s \cdot 2^{-l}, \quad \mathbf{v}_c = \mathbf{w}_c - 0.5 \cdot \mathbf{w}_s + \mathbf{v}_s \cdot v$$

每个体素包含：
- **几何参数**：8 个角点密度 $\mathbf{v}_{geo} \in \mathbb{R}^{2\times2\times2}$，共享相邻体素角点实现连续密度场
- **外观参数**：球谐系数 $\mathbf{v}_{sh} \in \mathbb{R}^{(N_{shd}+1)^2 \times 3}$
- **指数线性激活**：$\mathrm{explin}(x) = \begin{cases} x & x > 1.1 \\ \exp(\frac{x}{1.1}-1+\ln 1.1) & \text{otherwise} \end{cases}$，比 softplus 快 2 倍

**2. 体素 Alpha 计算**

在射线-体素交集内均匀采样 $K$ 个点，数值积分得到体密度：

$$\alpha = 1 - \exp\left(-\frac{l}{K}\sum_{k=1}^{K}\mathrm{explin}(\mathrm{interp}(\mathbf{v}_{geo}, \mathbf{q}_k))\right)$$

**3. 方向相关 Morton 排序**

关键创新：基于射线方向的正负符号选择 Morton 排列类型。3D 空间有 8 个卦限，对应 8 种 Morton 排列。对每个 tile 内所有像素共享同一射线方向符号时，只需按对应 Morton 类型排序即可。

**4. 自适应修剪与细分**

每 $h_{every}=1000$ 次迭代执行：
- **修剪**：移除最大混合权重 $T_i \alpha_i < h_{prune}$ 的体素
- **细分**：按训练损失梯度累积优先级 $\mathbf{v}_{priority} = \sum_{\mathbf{r} \in R} \|\alpha(\mathbf{r}) \cdot \partial \mathcal{L}(\mathbf{r}) / \partial \alpha(\mathbf{r})\|$，选择 top $h_{percent}=5\%$ 的体素细分

**5. 网格提取**

- **TSDF-Fusion**：计算稀疏网格点的截断符号距离值
- **Marching Cubes**：从零水平集提取表面网格

## Training

- **迭代次数**：20,000 次
- **初始 Octree 层级**：$h_{lv}=6$（$64^3$ 体素）
- **背景壳层**：$h_{out}=5$，前景体素的 2 倍
- **修剪阈值**：从 0.0001 线性缩放到 0.05
- **细分百分比**：5%
- **射线停止阈值**：$h_T = 10^{-4}$
- **超采样倍数**：$h_{ss} = 1.5$
- **每个体素采样点数**：新视角合成 K=1，网格重建 K=3
- **GPU**：RTX 3090 Ti
- **损失函数**：$\mathcal{L} = \mathcal{L}_{mse} + \lambda_{ssim}\mathcal{L}_{ssim} + \lambda_T\mathcal{L}_T + \lambda_{dist}\mathcal{L}_{dist} + \lambda_R\mathcal{L}_R + \lambda_{tv}\mathcal{L}_{tv}$

## Results & Comparisons

### Mip-NeRF360 数据集

| 方法 | FPS↑ | 训练时间↓ | LPIPS↓ | PSNR↑ | SSIM↑ |
|------|------|----------|--------|-------|-------|
| 3DGS | 131 | 24m | 0.216 | 27.45 | 0.815 |
| **Ours** | **121** | **15m** | **0.185** | **27.33** | **0.822** |
| Ours fast-rend | 258 | 9m | 0.210 | 26.87 | 0.804 |
| Ours fast-train | 131 | 4.5m | 0.199 | 27.08 | 0.816 |

### Tanks&Temples + Deep Blending

| 方法 | T&T FPS↑ | T&T LPIPS↓ | T&T PSNR↑ | DB FPS↑ | DB LPIPS↓ | DB PSNR↑ |
|------|---------|-----------|----------|--------|----------|---------|
| 3DGS | 180 | 0.176 | 23.75 | 140 | 0.244 | 29.60 |
| **Ours** | **125** | **0.144** | **23.04** | **366** | **0.228** | **29.84** |

### 内存与高分辨率 FPS

| 方法 | 峰值 GPU 显存↓ | 模型大小↓ | 1x FPS | 2x FPS | 3x FPS |
|------|--------------|----------|--------|--------|--------|
| 3DGS | 1.8 GB | 0.7 GB | 131 | 69 | 39 |
| **Ours** | **3.9 GB** | **1.8 GB** | **121** | **103** | **69** |

### 网格重建（Tanks&Temples + DTU）

| 方法 | T&T F-score↑ | DTU CD↓ | 训练时间 |
|------|-------------|---------|---------|
| 3DGS | 0.19 | 1.96 | 11m |
| 2DGS | 0.32 | 0.80 | 11m |
| **Ours** | **0.40** | **0.76** | **5m** |

### 自适应 vs 均匀体素消融

| 分辨率 | LPIPS↓ | PSNR↑ | FPS↑ |
|--------|--------|-------|------|
| 均匀 $256^3$ | 0.444 | 23.98 | 457 |
| 均匀 $512^3$ | 0.326 | 25.37 | 190 |
| **自适应** | **0.200** | **23.29** | **<10** |

自适应体素在同等 FPS 下质量显著优于均匀 $512^3$。

## Related Work Analysis

- **3DGS**：本工作的主要对比基线。3DGS 基于高斯基元的光栅化渲染速度快，但存在 popping artifact 和体密度歧义问题。
- **Plenoxels**：之前的完全显式体素网格方法，通过体射线投射采样渲染，FPS 显著低于光栅化方法。
- **NeRF / InstantNGP**：隐式神经表示方法，渲染速度远低于光栅化方法。
- **Sparse Voxel Octrees / VDB**：经典稀疏体素管理数据结构，本工作不使用传统 Octree 指针结构，仅存储叶节点体素。
- **NeuS / VolSDF**：SDF 表面重建方法，本工作的密度场可类似扩展为 SDF 建模。

## Ablations

1. **方向相关 Morton 排序**：确保不同层级体素的正确渲染顺序，消除 popping artifact。
2. **自适应体素细分**：相比均匀分辨率，在同等 FPS 下 LPIPS 显著改善（0.200 vs 0.326）。
3. **exponential-linear 激活**：比 softplus 快 2 倍（21.5M vs 11.8M ops/sec），效果等价。
4. **高分辨率扩展性**：在 3x 分辨率下 SVRaster 达 69 FPS，显著优于 3DGS 的 39 FPS。

## Limitations

1. **模型体积较大**：比 3DGS 需要更多显存（3.9 GB vs 1.8 GB）和模型大小（1.8 GB vs 0.7 GB）。
2. **曝光变化敏感**：训练视角存在严重曝光变化时，会产生明显的亮度边界和漂浮物，PSNR 和 FPS 下降。
3. **纹理细节几何凸起**：当前方法倾向于为纹理细节产生不必要的几何凸起。
4. **不依赖 SfM 先验**：不使用 COLMAP 稀疏点初始化，在部分场景下质量略低于使用 SfM 先验的方法。

## 评论与启示

1. **体素复兴**：在 3DGS 热潮下，SVRaster 证明了经典体素表示在高效光栅化和显式结构方面的不可替代价值，为神经渲染提供了正交的技术路线。
2. **Morton 排序的巧妙应用**：利用 8 种射线方向相关的 Morton 排列解决多层级体素排序问题，简洁而有效，体现了计算机科学中经典数据结构在现代渲染中的生命力。
3. **神经-free 渲染的扩展性**：由于不依赖 MLP，体素网格可直接对接经典 3D 处理管线（TSDF-Fusion、Marching Cubes、Voxel Pooling），为 3D 理解和生成提供了更直接的接口。

## Connections

- [[3DGS]] — 高斯泼溅基础方法，SVRaster 的主要对比基线
- [[Plenoxels]] — 显式体素网格的神经自由渲染先驱
- [[Sparse Voxel Octrees]] — 经典稀疏体素数据结构
- [[Morton Order / Z-order Curve]] — 空间填充曲线用于体素排序
- [[Marching Cubes]] — 等值面提取算法
- [[TSDF-Fusion]] — 截断符号距离场体素融合
- [[InstantNGP]] — 哈希网格加速 NeRF
- [[NeuS]] — SDF 表面重建方法

## Contradictions

- 在 Tanks&Temples 数据集上，SVRaster 的 PSNR（23.04）略低于 3DGS（23.75），但 LPIPS（0.144）显著优于 3DGS（0.176），且 FPS（125）接近 3DGS（180）。这说明在曝光变化大的场景中 3DGS 更稳健。
- Mip-NeRF360 上 SVRaster 的 LPIPS（0.185）优于 Zip-NeRF（0.187），但 PSNR（27.33）略低于 3DGS（27.45），体现 LPIPS 更偏好细节恢复而 PSNR 偏好平滑渲染。

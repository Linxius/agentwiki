---
title: "Ref-GS: Directional Factorization for 2D Gaussian Splatting"
type: paper
tags: [Gaussian Splatting, Deferred Rendering, Directional Encoding, Inverse Rendering, Spherical Mip-Grid, 2DGS]
date: 2026-08-04
source_file: raw/papers/arxiv-2412.00905.md
url: https://arxiv.org/abs/2412.00905
links: []
---

## Summary

本文提出 **Ref-GS**，一种基于 2D 高斯泼溅（2DGS）的延迟渲染方法，解决视角相关效果与几何重建之间的歧义问题。核心方法是将高斯属性混合后再进行方向编码（deferred shading），引入 Spherical Mip-grid（Sph-Mip）捕获表面粗糙度，并通过向量外积实现几何-光照分解。该方法在反射场景上实现了照片级真实的视角相关渲染，同时保持精确的几何重建，在 Shiny Blender 和 Shiny Real 数据集上均达到 SOTA 表现。

## 原始出处

- 原始文件: [raw/papers/arxiv-2412.00905.md](../../raw/papers/arxiv-2412.00905.md)
- 原文链接: [https://arxiv.org/abs/2412.00905](https://arxiv.org/abs/2412.00905)
- Brief 条目: [brief.md](#) — 2026-08-04 digest 条目 1
- 深度阅读报告: N/A

## Key Contributions

1. **延迟高斯着色（Deferred Gaussian Shading）**：将高斯属性混合后在图像空间进行着色，而非逐基元着色，有效减少法线-视角歧义，产生更精确的镜面反射和表面重建。
2. **方向分解（Directional Factorization）**：通过空间特征与方向特征的外积 $\mathbf{k} \otimes \mathbf{s}$ 实现几何-光照分解，降低每个高斯基元的特征通道数，减少体积渲染计算开销。
3. **Sph-Mip 编码**：基于经纬度网格的多级球面特征金字塔，通过粗糙度维度插值捕获不同尺度的表面粗糙度，实现远场光照建模。

## Method

### 框架图

```
[Ref-GS 渲染管线]

[Geometry Pass - 几何传递]
  2D 高斯基元 → 光栅化 → G-Buffer
    ├─ 漫反射颜色 I_d
    ├─ 空间特征 K (H×W×D)
    ├─ 粗糙度图 M (H×W×1)
    └─ 法线图 N (H×W×3)
            ↓
[Lighting Pass - 光照传递]
  对每个像素 (u,v):
    1. 从 N 计算反射方向 ω_r
    2. ω_r → 球坐标 (θ,φ)
    3. Sph-Mip(ω_r, ρ, M) → 方向特征 S
    4. K ⊗ S → 高维中间张量
            ↓
[Rendering Pass - 着色传递]
  I = I_d + f_Θ(S, K⊗S)
  γ-tone mapping → sRGB
```

### 双重写作

**问题**：在 3DGS 和 2DGS 中，每个基元独立查询 SH 系数得到视角相关颜色，然后进行前向累积。在反射场景中，这种方法的视角相关颜色与基元法线的耦合会产生歧义——改变 SH 系数可以等效抵消视角方向变换，导致高频率反射和法线重建不准确。

**解决思路**：借鉴计算机图形学中的延迟着色（deferred shading），先渲染几何属性到 G-buffer，再在屏幕空间进行着色。这样视角相关颜色是在混合后的表面上评估，而非单个基元上，消解了 SH 系数与基元方向的歧义。

**具体方法**：

**1. 延迟高斯着色**

将每个基元的属性（漫反射颜色 $\mathbf{c}_d$、特征 $\mathbf{f}$、粗糙度 $\rho$）沿射线进行 alpha 混合：

$$\mathbf{I} = \mathbf{I}_d + f_{\Theta}(\mathbf{S}, \mathbf{K} \otimes \mathbf{S})$$

其中 $\mathbf{K}$ 是通过基元特征 $\mathbf{f}_i$ alpha 混合得到的空间特征图，$\mathbf{S}$ 是从 Sph-Mip 查询的方向特征图，$\otimes$ 是逐像素外积。

**2. 方向分解**

受 TensoRF 启发，使用向量外积 $\mathbf{s} \circ \mathbf{k}$ 表示视角相关效应。空间特征 $\mathbf{k} \in \mathbb{R}^D$ 和方向特征 $\mathbf{s} \in \mathbb{R}^C$ 通过外积组合为块矩阵，展平后输入轻量 MLP 解码器得到最终颜色。这种分解显式地将几何（空间特征）和光照（方向特征）分离。

**3. Sph-Mip 编码**

在球面上使用经纬度网格分布特征点，展开为 2D 特征网格。反射方向 $\omega_r$ 通过球坐标 $(\theta, \phi)$ 映射到网格 XY 轴，粗糙度 $\rho$ 对应 Z 轴。通过多级 mipmap（9 级，基础分辨率 $512 \times 1024 \times 16$）和粗糙度维度的三线性插值，高效查询方向特征。

## Training

- **框架**：PyTorch + Nvdiffrast
- **GPU**：单张 Tesla V100 32GB
- **优化器**：Adam，30,000 次迭代
- **优化参数**：MLP $f_\Theta$、mipmap $\mathcal{M}$、每个 2D 高斯的位置/缩放/旋转/不透明度/漫反射颜色/粗糙度/特征
- **损失函数**：$\mathcal{L} = \mathcal{L}_{\text{rgb}} + \lambda_d \mathcal{L}_{\text{d}} + \lambda_n \mathcal{L}_{\text{n}}$，其中 $\mathcal{L}_{\text{rgb}} = (1-\lambda)\mathcal{L}_1 + \lambda\mathcal{L}_{\text{D-SSIM}}$（$\lambda=0.2$），$\lambda_d=100$，$\lambda_n=0.05$
- **MLP 架构**：1 隐藏层 256 神经元，ReLU 激活
- **Sph-Mip 分辨率**：基础级 $H_\mathcal{M}=512, W_\mathcal{M}=1024, C=16$，共 9 级

## Results & Comparisons

### 数据集

- **Shiny Blender**：合成反射物体数据集（Car, Ball, Helmet, Teapot, Toaster, Coffee）
- **Shiny Real**：真实世界反射场景（Gardenspheres, Sedan, Toycar）
- **NeRF Synthetic**：通用物体数据集
- **Glossy Synthetic**：光泽物体数据集
- **Glass & Ball**：透明折射物体数据集

### Shiny Blender + Shiny Real 对比

| 方法 | Shiny Blender Avg PSNR | Shiny Real Avg PSNR | Shiny Blender Avg SSIM | Shiny Real Avg SSIM |
|------|----------------------|-------------------|----------------------|-------------------|
| Ref-NeRF | 32.32 | 23.62 | 0.956 | 0.646 |
| 3DGS-DR | 33.94 | 23.80 | 0.971 | 0.659 |
| **Ours** | **34.80** | **24.44** | **0.973** | **0.682** |

### LPIPS 对比（越低越好）

| 方法 | Shiny Blender Avg | Shiny Real Avg |
|------|-------------------|----------------|
| 3DGS-DR | 0.059 | 0.236 |
| **Ours** | **0.056** | **0.224** |

### 法线估计精度（MAE°，越低越好）

| 方法 | Shiny Blender Avg |
|------|------------------|
| 3DGS-DR | 2.43° |
| **Ours** | **2.21°** |

### 训练与渲染速度（相对 3DGS = 1.0）

| 方法 | 渲染速度 | 训练时间 |
|------|---------|---------|
| 3DGS | 1.00× | 1.00× |
| GaussianShader | 0.17× | 11.05× |
| 3DGS-DR | 0.93× | 3.25× |
| **Ours** | **0.37×** | **2.63×** |

### 消融实验

| 变体 | PSNR | SSIM | LPIPS | MAE° |
|------|------|------|-------|------|
| w/o Sph-Mip | 29.95 | 0.943 | 0.090 | 3.61 |
| w/o mipmap | 30.12 | 0.945 | 0.091 | 5.12 |
| w/o Deferred Shading | 31.79 | 0.957 | 0.062 | 2.57 |
| w/o K⊗S | 33.37 | 0.966 | 0.051 | 2.38 |
| **Full** | **34.00** | **0.969** | **0.046** | **2.21** |

## Related Work Analysis

- **Ref-NeRF**：将 IDE（Integrated Directional Encoding）引入 NeRF，用反射方向替代视角方向查询。但依赖 MLP 表示几何，训练和渲染较慢。
- **GaussianShader**：将 3DGS 与 PBR 着色器结合，显式建模视角相关效应，但无法处理近场照明。
- **3DGS-DR**：在 3DGS 中引入延迟着色进行反射建模，但同样难以精确建模近场照明。
- **3iGS**：使用张量分解优化入射光照，但在近场照明建模上仍有局限。
- **2DGS**：Ref-GS 的基础，采用 2D 定向圆盘作为表面元，提供更精确的表面重建。

## Ablations

1. **Sph-Mip 编码**：移除后 PSNR 从 34.00 降至 29.95，LPIPS 从 0.046 升至 0.090，说明 Sph-Mip 对高频视角相关外观建模至关重要。
2. **Mipmap 多级策略**：移除 mipmap 后粗糙表面重建失败并出现伪影（PSNR 30.12 vs 34.00），因为真实场景通常不是单一材质。
3. **延迟着色**：移除后镜面反射质量下降（PSNR 31.79 vs 34.00），法线估计误差增大（2.57° vs 2.21°）。
4. **方向分解**：移除 K⊗S 后近场互反射无法重建（PSNR 33.37 vs 34.00）。

## Limitations

1. **渲染速度**：相比 2DGS 较慢（37% 基准速度），因为 MLP 解码器增加了计算开销。
2. **难以集成到标准 CG 引擎**：依赖神经解码器，需要通过 textured mesh baking 等技术转换。
3. **高维特征开销**：K⊗S 外积产生 H×W×(D×C) 维中间张量（H×W×64），需要一定显存。

## 评论与启示

1. **延迟着色在神经渲染中的有效性**：Ref-GS 证明将传统 CG 的延迟着色引入 3DGS 可以有效解决视角-法线歧义问题，这一思想可能推广到其他基于基元的表示方法。
2. **外积分解的简洁性**：用简单的向量外积代替复杂的多层交互，既实现了几何-光照分解又降低了特征通道数，体现了低秩分解在神经渲染中的普遍价值。
3. **球面 Mip 网格的创新**：将 mipmap 思想引入球面特征网格，通过粗糙度维度实现多尺度视角相关外观建模，为远场光照表示提供了新思路。

## Connections

- [[2DGS]] — 2D 高斯泼溅基础方法
- [[3DGS-DR]] — 延迟着色的 3DGS 反射建模
- [[GaussianShader]] — 3DGS 与 PBR 着色器结合
- [[Ref-NeRF]] — NeRF 中的反射建模先驱
- [[3iGS]] — 张量分解的光照优化
- [[Spherical Harmonics]] — 球谐函数在神经渲染中的应用
- [[Deferred Shading]] — 计算机图形学中的延迟着色技术
- [[TensoRF]] — 张量分解的神经表示

## Contradictions

- 无直接矛盾。Ref-GS 在 Shiny Blender 和 Shiny Real 数据集上均优于 3DGS-DR 和其他基线方法。

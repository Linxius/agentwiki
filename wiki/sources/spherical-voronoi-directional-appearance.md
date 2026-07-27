---
title: "Spherical Voronoi Directional Appearance as a Differentiable Partition of the Sphere"
type: source
tags: [paper]
date: 2026-07-28
source_file: raw/papers/arxiv-251214180-81c10972.md
url: https://arxiv.org/abs/2512.14180
venue: ""
published: 2025
links:
  - https://sphericalvoronoi.github.io
---

## Summary

本文提出**Spherical Voronoi (SV)**，一种新的显式球面函数表示方法，用于 [[3D Gaussian Splatting|3DGS]] 中的外观建模。SV 通过可微分的 soft Voronoi 划分将球面方向域分割为可学习的区域，每个区域由 site（站点）位置和对应颜色值表示，通过 softmax 加权组合输出。相比 [[Spherical Harmonics|SH]]（带限、Gibbs 伪影）、[[Spherical Gaussian|SG]] 和 [[Spherical Betas|SB]]（优化不稳定、局部极小），SV 在保持优化稳定性的同时能精确建模高频信号。对于镜面反射场景，SV 被扩展为可学习的光照探针（Voronoi Light Probes），结合延迟渲染管线，在 Ref-NeRF、GlossySynthetic 等反射基准上达到 SOTA。

## 原始出处

- 原始文件: [raw/papers/arxiv-251214180-81c10972.md](../../raw/papers/arxiv-251214180-81c10972.md)
- 原文链接: [https://arxiv.org/abs/2512.14180](https://arxiv.org/abs/2512.14180)
- 项目主页: [https://sphericalvoronoi.github.io](https://sphericalvoronoi.github.io)

## Key Contributions

1. **Spherical Voronoi 表示**：基于可微分 soft Voronoi 划分的球面函数显式表示，克服了传统球面基函数的带限和优化不稳定问题
2. **方向辐射度建模**：将 SV 应用于 3DGS 的视相关辐射建模，在 Mip-NeRF 360、NeRF-Synthetic、DeepBlending、Tanks&Temples 上一致超越 SH/SG/SB
3. **反射建模**：通过可学习的光照探针（Voronoi Light Probes）扩展 SV 到空间变化的镜面反射，实现完全显式且可微分的反射模型，在 Ref-NeRF/GlossySynthetic 上达到 SOTA

## Method

![SV 框架图](../images/spherical-voronoi-directional-appearance/fig5.png)
*图 5：Spherical Voronoi 基函数 — (左) 球面函数由一组 Voronoi sites 表示；(右) 每个 site 的支撑区域覆盖整个球面*

![延迟渲染管线](../images/spherical-voronoi-directional-appearance/fig7.png)
*图 7：延迟渲染管线 — 2DGS 场景先光栅化到 G-buffer（位置、法线、粗糙度、漫反射颜色），再通过光照 pass 结合探针光照和环境 cubemap 计算最终着色*

### 整体思路

SV 的核心思想是将球面划分为可学习的 Voronoi 区域，每个区域关联一个颜色值，查询方向时用 softmax 加权各区域值。这与 SH/SG/SB 的本质区别在于：SV 的”基函数”是数据驱动的（由 site 位置决定），而非预定义的固定基函数。

温度参数 τ 控制划分的锐利度：小 τ 产生平滑过渡（适合漫反射），大 τ 逼近硬划分（适合镜面高光），实现从平滑到锐利的连续控制。

对于反射建模，SV 被嵌入光照探针中，每个探针在 3D 空间中有一个位置和一个 SV 函数。探针之间通过逆距离加权插值，实现空间变化的反射效果。结合延迟渲染（G-buffer → 光照 pass）和环境 cubemap 远场照明，构成完整的反射建模框架。

### 各组件/步骤

**Spherical Voronoi 表示 (Sec 3.2)**

给定 K 个 site 方向 s_k 和对应颜色值 c_k，方向 ω 的函数值为：

f_SV(ω; τ, s, c) = Σ_k w_k(ω; τ_k) c_k

其中权重 w_k 通过 softmax 计算：

w_k(ω; τ) = exp(τ_k s_k · ω) / Σ_{k'} exp(τ_{k'} s_{k'} · ω)

- 每个 site 有可学习的 3D 方向 s_k 和 3D 颜色 c_k
- τ_k 控制该 site 的温度（锐利度），可从 site 向量范数隐式派生：τ_k = ‖s_k‖
- 8 个 sites 匹配 degree-3 SH 的自由度，每 Gaussian 共 48 个参数（8×6）
- softmax 确保所有 sites 梯度良好，无 SG/SB 中 kernel 重叠导致的竞争问题

**加速方案 (Sec 7)**

对大 K 场景（反射建模中数千 sites），naive 推理 O(K) 不可行。使用低分辨率 cubemap 预处理：
- 每个 cubemap texel t 预选 TopK 最近 sites S(t)
- 推理时只计算 S(t(ω_r)) 中的 sites
- 复杂度从 O(K) 降至 O(|S(t)|)
- 每 500 步重建一次 assignment

**方向辐射度建模 (Sec 3.3)**
- 直接替换 3DGS 中的 SH 表示
- 每个 Gaussian 存储 site 参数 (τ_k, s_k, c_k) 作为可学习参数
- 用 f_SV(ω) 输出视相关 RGB 颜色
- 与 3DGS-MCMC、2DGS、Beta-Splatting 兼容

**反射建模 (Sec 3.4)**
- 基于 [[2D Gaussian Splatting|2DGS]] 骨干，每个 primitive 增加粗糙度 r ∈ [0,1] 和漫反射颜色 d ∈ ℝ³
- 延迟渲染：Geometry Pass 输出位置 P、法线 N、粗糙度 R、漫反射颜色 D
- 光照 Pass 计算公式：
  - 最终颜色 C = D + C_spec
  - C_spec = α C_n + (1-α) C_f
  - C_f = cubemap(ω_r) — 远场照明（可学习环境 cubemap）
  - C_n = Σ_i w̃_i f_SV^i(ω_r) — 近场照明（SV 光照探针插值）
  - ω_r = 2(ω·N)N - ω — 反射方向

- 粗糙度映射到温度：τ = (1-R)τ_max + R τ_min，τ_min=0.2, τ_max=1500
  - 低粗糙度 → 大 τ → 锐利反射
  - 高粗糙度 → 小 τ → 模糊反射

**Voronoi 光照探针**
- 每个探针 i：位置 p_i，SV 函数 (τ_i, s_i, c_i)，混合权重 α_i
- 查询时选择 kNN 探针 N(P)，逆距离加权插值
- 权重：w̃_i = ‖P-p_i‖⁻¹ / Σ_j ‖P-p_j‖⁻¹
- 合成近场 C_n = Σ w̃_i f_SV^i(ω_r)
- 混合因子 α = Σ w̃_i α_i

## Training

- 辐射度建模：Beta-Splatting 骨干，30k 迭代，不使用测试集早停
- 反射建模：2DGS 骨干，合成场景 128 探针 × 2048 sites，真实场景 1024 探针 × 2048 sites
- Cubemap 分辨率：256×256×6×3
- SV sites 初始化为 Fibonacci 球面均匀采样
- Cubemap 加速 assignment 每 500 步重建一次
- 其余超参数（损失、scheduler 等）沿用对应骨干的默认配置

## Results & Comparisons

**辐射度建模 (Table 1)**
| 数据集 | SH | SG | SB | SV |
|--------|-----|-----|-----|-----|
| Mip-NeRF 360 | 28.09 | 28.18 | 28.12 | **28.71** |
| NeRF-Synthetic | 34.15 | 34.26 | 34.10 | **34.58** |
| DeepBlending | 29.80 | 29.67 | 29.56 | **30.63** |
| Tanks&Temples | 24.50 | 24.71 | 24.54 | **25.00** |

SV 在所有数据集上一致超越 SH/SG/SB，甚至超过 Zip-NeRF（基于 MLP 的神经辐射场），表明显式表示可以匹敌甚至超越神经表示。

**反射建模 (Table 2)**
| 数据集 | Ref-GS | GaussianShader | 3DGS-DR | Ours |
|--------|--------|----------------|---------|------|
| Ref-NeRF | 36.01 | 32.06 | 34.33 | **36.09** |
| GlossySynthetic | 30.83 | 29.93 | 27.99 | **31.30** |
| Ref-Real | **24.14** | 22.98 | 23.05 | 23.91 |

SV 在 Ref-NeRF 和 GlossySynthetic 上达到 SOTA，Ref-Real 略低于 Ref-GS（可能因 Ref-GS 使用了非标准降采样）。

**探针表示消融 (Table 3, Ref-NeRF)**
| 表示 | PSNR | SSIM | LPIPS |
|------|------|------|-------|
| SG | 34.19 | 0.967 | 0.060 |
| SB | 34.07 | 0.966 | 0.061 |
| Cubemap | 34.48 | 0.970 | 0.056 |
| SV | **36.09** | **0.976** | **0.050** |

SV 在相同参数预算下远超 SG/SB/Cubemap。

## Related Work Analysis

论文与以下几类工作相关：
1. **球面基函数**：SH（带限、Gibbs 伪影）、SG（优化不稳定、局部极小）、SB（更灵活但更难优化）— 这些是 SV 的直接对比基线
2. **NeRF 反射建模**：Ref-NeRF 首次分解辐射度+法线正则化；NeRF-Casting 通过次级光线追踪实现一致反射 — SV 在显式表示中达到类似的反射质量
3. **3DGS 反射建模**：GaussianShader（简化着色模型+MLP 残差）、3DGS-DR（延迟渲染）、Ref-GS（方向光分解+屏幕空间 mip-map）— 本文的方法完全显式，无需 MLP 解码器
4. **光照探针**：NeLF-Pro（神经光照探针）、EnvGS（环境 Gaussian）— 本文的探针使用显式 SV 函数，更加高效

## Ablations

- **SV vs SG/SB/Cubemap 探针** (Table 3)：SV 在相同参数预算下 PSNR 高出 1.6-2.0 dB
- ![消融可视化](../images/spherical-voronoi-directional-appearance/fig8.png)
  *图 8：定性消融 — 移除反射、近场探针、材质参数（粗糙度）逐步降低锐度和反射一致性*
- **Kernel 容量** (Fig 9)：|S(K)|=8, |N(K)|=8 为质量-效率平衡点
- **Sites 数量** (Table 5)：8-12 sites 性能饱和，之后边际收益递减

## Limitations

1. **Ref-Real 非 SOTA**：Ref-Real 数据集上略低于 Ref-GS，可能因 Ref-GS 使用了非标准降采样
2. **推理速度**：反射模型为 0.45× 3DGS，延迟渲染+探针查询有额外开销
3. **探针数量和位置**：合成/真实场景需要不同探针数（128 vs 1024），缺乏自适应机制
4. **完全显式的局限**：在极复杂反射场景中，神经解码器可能仍占优（如 Ref-GS 在 Ref-Real 上的表现）
5. **粗糙度-温度映射**：线性映射 τ = (1-R)τ_max + R τ_min 可能不够灵活

## Connections

- SV 与 [[3D Gaussian Splatting|3DGS]] 完全兼容，可替换 SH 表示
- 延迟渲染管线借鉴 [[3DGS-DR]] 和 [[Ref-GS]] 的设计
- 光照探针概念类似于 [[NeLF-Pro]] 的神经光照探针，但使用显式 SV 函数
- 反射方向参数化继承了 [[Ref-NeRF]] 的设计思想

## Contradictions

- 论文声称”显式表示可以匹敌神经表示”，但 Ref-Real 数据集上 Ref-GS（使用 MLP 解码器）的 PSNR 更高
- 作者批评竞争表示（SG/SB）优化不稳定，但自己的 SV 也需要精心设计温度机制和初始化策略
- 加速方案（cubemap TopK）引入了额外的超参数（cubemap 分辨率、候选数、重建频率），增加调参成本
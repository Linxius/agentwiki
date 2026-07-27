---
title: Spherical Voronoi (SV)
type: concept
tags: [representation, differentiable-rendering]
date: 2026-07-28
---

## Spherical Voronoi (SV)

Spherical Voronoi 是一种基于可微分 soft Voronoi 划分的球面函数显式表示方法，由 Francesco Di Sario 等人在 [[Spherical Voronoi Directional Appearance as a Differentiable Partition of the Sphere]] 中提出。

### 原理

给定 K 个 site 方向 s_k 和对应值 c_k，方向 ω 的输出为：

f_SV(ω; τ, s, c) = Σ_k [exp(τ_k s_k · ω) / Σ_{k'} exp(τ_{k'} s_{k'} · ω)] · c_k

- 每个 site 定义球面上的一个 Voronoi 单元
- Softmax 权重实现可微分划分
- 温度 τ 控制划分锐利度：τ→0 平滑过渡，τ→∞ 硬划分

### 与经典表示对比

| 特性 | SH | SG/SB | SV |
|------|-----|-------|-----|
| 高频信号 | ❌ 带限/Gibbs | ✓ | ✓ |
| 优化稳定性 | ✓ 正交基 | ❌ 局部极小 | ✓ softmax 全梯度 |
| 参数效率 | O(L²) | O(K) | O(K) |
| 解释性 | 低 | 中 | 高（各 site 有明确方向） |

### 应用

1. **3DGS 辐射度建模**：替换 SH 表示视相关颜色，8 sites/primitive
2. **反射建模 (Voronoi Light Probes)**：探针嵌入 SV 函数，处理空间变化镜面反射

### 关联概念

- [[Voronoi Light Probes]] — SV 在反射建模中的扩展
- [[3D Gaussian Splatting]] — SV 的主要应用场景
- [[Spherical Harmonics]] — 传统球面基函数表示
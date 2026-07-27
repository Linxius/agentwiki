---
title: Voronoi Light Probes
type: concept
tags: [representation, reflection-modeling]
date: 2026-07-28
---

## Voronoi Light Probes

Voronoi Light Probes 是 [[Spherical Voronoi|Spherical Voronoi (SV)]] 在反射建模中的扩展，由 [[Spherical Voronoi Directional Appearance as a Differentiable Partition of the Sphere]] 提出。每个探针在 3D 空间中存储一个位置和对应的 SV 函数，用于建模空间变化的镜面反射。

### 原理

- 场景中放置 N 个可学习探针，每个探针包含：
  - 3D 位置 p_i
  - SV 函数 (τ_i, s_i, c_i) — 查询反射方向 ω_r
  - 混合权重 α_i ∈ [0,1]
- 渲染时选择 k 近邻探针，逆距离加权插值

### 关键方程

- 近场照明: C_n = Σ_{i∈N(P)} w̃_i · f_SV^i(ω_r)
- 混合因子: α = Σ_{i∈N(P)} w̃_i · α_i
- 权重: w̃_i = ‖P-p_i‖⁻¹ / Σ_j ‖P-p_j‖⁻¹

### 与其他方法对比

- 相比 [[Ref-GS]]（神经解码器）：完全显式，更高效
- 相比 [[NeLF-Pro]]（神经探针）：使用显式 SV 函数，无 MLP
- 相比 3DGS-DR（仅 cubemap）：额外建模近场照明

### 关联概念

- [[Spherical Voronoi]] — 探针内部使用的球面函数表示
- [[3D Gaussian Splatting]] — 探针嵌入的渲染管线
- [[Deferred Rendering]] — 探针渲染的实现框架
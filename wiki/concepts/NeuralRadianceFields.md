---
title: "Neural Radiance Fields"
type: concept
tags: [nerf, neural-rendering, novel-view-synthesis]
date: 2026-07-28
---

# Neural Radiance Fields (NeRF)

NeRF（Neural Radiance Fields）是一种用神经网络表示3D场景的**体积神经渲染**范式，由 Mildenhall et al. (2020) 提出。

## 核心思想

- 将场景表示为连续函数：F_θ(x, d) → (c, σ)，即从3D坐标x和视角方向d映射到颜色c和体积密度σ
- 沿光线采样点，通过**体积渲染**积分合成像素颜色
- 使用位置编码（Positional Encoding）提升高频细节表示能力

## 体积渲染公式

c(r) = ∫_{τ_n}^{τ_f} T(τ) σ(r(τ)) c(r(τ), d) dτ
其中 T(τ) = exp(-∫_{τ_n}^{τ} σ(r(z)) dz) 为累积透过率

## 关键发展

| 方向 | 代表工作 | 核心改进 |
|------|----------|----------|
| 质量提升 | MipNeRF | 抗锯齿，集成位置编码 |
| 无界场景 | MipNeRF 360 | 场景收缩+提案网络 |
| 表面重建 | NeuS | SDF替代密度，Eikonal正则化 |
| 效率提升 | Instant NGP | 多分辨率哈希编码，空域跳过 |
| 实时渲染 | Adaptive Shells | 自适应窄带壳+光线追踪 |
| 显式表示 | Volumetric Surfaces | 多层网格替代体积渲染 |
| 3D高斯 | 3D Gaussian Splatting | 显式高斯原语+光栅化 |

## Connections

- [[Signed Distance Function]] — NeuS等用SDF替代密度改善几何质量
- [[Adaptive Shells]] — 混合方案：隐式场+显式壳
- [[Instant NGP]] — 哈希编码使NeRF训练从天级→秒级

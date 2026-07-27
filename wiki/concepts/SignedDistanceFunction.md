---
title: "Signed Distance Function"
type: concept
tags: [sdf, implicit-representation, geometry]
date: 2026-07-28
---

# Signed Distance Function (SDF)

SDF（Signed Distance Function）是一种**隐式几何表示**，将空间点x映射到其到最近表面的**带符号距离**：f(x) ∈ ℝ。f(x)=0表示表面位置，正/负值表示表面外部/内部。

## 在神经渲染中的应用

### NeuS (Wang et al., 2021)
将SDF与体渲染结合：用SDF f经sigmoid映射为体积密度σ：
σ = max(-dΦ_s/dτ(f) / Φ_s(f), 0), Φ_s(f) = (1+exp(-f/s))^{-1}
其中s为核大小（控制密度扩散程度），通过Eikonal正则化 ||∇f||=1 确保f为有效SDF。

### Adaptive Shells (Wang et al., 2023)
- 将NeuS的全局核s扩展为**空间变化核**s(x)
- 利用SDF水平集演化提取自适应窄带壳
- 侵蚀（向内缩）：f→SDF_-；膨胀（向外扩）：f→SDF_+

### Volumetric Surfaces (2024)
- 使用**多个SDF**表示多层网格
- 每层的SDF零水平集定义一层三角形网格
- 通过光栅化替代体积渲染

## 优缺点

| 优势 | 劣势 |
|------|------|
| 拓扑灵活（可表示任意形状） | 提取显式网格需Marching Cubes |
| 天然支持形状插值/变形 | 远距离推断不可靠 |
| Eikonal正则化提供良好先验 | 训练需仔细初始化 |
| 可微，适合基于优化的重建 | 薄结构表示困难 |

## Connections

- [[Neural Radiance Fields]] — SDF作为替代密度场的方法
- [[Adaptive Shells]] — 利用SDF水平集演化提取自适应壳
- [[Marching Cubes]] — 从SDF提取三角网格的标准算法

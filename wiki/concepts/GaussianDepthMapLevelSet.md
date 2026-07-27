---
title: "Gaussian Depth Map Level Set Sampling"
type: concept
tags: [technique, surface-reconstruction]
date: 2026-07-28
sources: ["sources/su-ga-r.md"]
---

# Gaussian Depth Map Level Set Sampling

深度图水平集采样是 [[SuGaR]] 论文提出的高效网格提取方法的核心步骤：利用高斯体深度图在场景表面上高效定位水平集点，替代 Marching Cubes 在全空间网格上的穷举搜索。

## 算法流程

1. 从训练视角渲染高斯体深度图（扩展 3DGS 光栅化器）
2. 随机采样深度图像素
3. 沿视线方向在 $[-3\\sigma, 3\\sigma]$ 范围内采样 $n$ 个点
4. 计算各点密度值 $d_i$
5. 若存在 $d_i < \\lambda < d_j$ ，通过线性插值定位精确水平集位置
6. 法线取为密度梯度方向

## 优势

- **速度快**：仅需在深度图附近搜索，避免了全空间 3D 网格的构建和遍历
- **鲁棒性好**：比 Marching Cubes 更适合稀疏密度场
- **可扩展**：通过 Poisson 重建自动生成流形网格，支持网格简化

## 相关概念

- [[SuGaR]] — 整体方法
- [[Poisson表面重建|Poisson Surface Reconstruction]] — 后处理步骤
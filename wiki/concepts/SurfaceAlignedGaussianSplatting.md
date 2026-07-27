---
title: "Surface-Aligned Gaussian Splatting"
type: concept
tags: [technique, 3DGS]
date: 2026-07-28
sources: ["sources/su-ga-r.md"]
---

# Surface-Aligned Gaussian Splatting

Surface-Aligned Gaussian Splatting 是 [[SuGaR]] 论文提出的核心概念：通过正则化项引导 [[3D Gaussian Splatting]] 中的高斯体沿场景表面排列并均匀分布，从而使得从高斯体中提取网格成为可能。

## 技术要点

- **密度场到 SDF 的转化**：将高斯体密度函数 $d(p)$ 通过 $f(p)=\\pm s_{g*}\\sqrt{-2\\log(d(p))}$ 映射为"理想"有符号距离函数
- **正则化目标**：最小化当前密度场的 SDF 与理想 SDF 的差异（Eq. 8），同时加入法线一致性约束（Eq. 10）
- **深度图辅助估计**：利用高斯体深度图高效估计 $\\hat{f}(p)$，避免全局 SDF 计算
- **效果**：使高斯体变扁平（2D 化）、沿表面对齐、不透明度二值化

## 相关概念

- [[3D Gaussian Splatting]] — 基础表示
- [[神经隐式表面|Neural SDF]] — 替代的隐式表面表示方法
- [[Poisson表面重建|Poisson Surface Reconstruction]] — 网格构建算法
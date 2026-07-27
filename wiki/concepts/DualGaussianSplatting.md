---
title: "Dual Gaussian Splatting"
type: concept
tags: [rendering, 3d-gaussians]
---

双高斯溅射是由 [[Ref-DGS]] 提出的一种场景表示方法，将场景分解为两组互补的高斯原语：

- **几何高斯 ($\mathcal{G}_{\mathrm{geo}}$)**：捕捉视角无关的场景结构和漫反射
- **局部反射高斯 ($\mathcal{G}_{\mathrm{local}}$)**：捕捉近场镜面反射交互

核心动机：镜面反射不应作为几何属性处理。将视角相关的反射效果从几何表示中解耦，避免反射引起的几何畸变（表面收缩、局部凹陷）。

与相关概念的关系：
- [[3D Gaussian Splatting (3DGS)]] — 单组高斯的基础框架
- [[2D Gaussian Splatting (2DGS)]] — 表面对齐的平面高斯
- [[Ref-GS]] — 使用环境映射+Spatial Feature 但无显式解耦
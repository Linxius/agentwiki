---
title: "Physically-Aware Specular Adaptive Mixing Shader"
type: concept
tags: [rendering, specular]
---

[[Ref-DGS]] 提出的轻量级物理感知镜面着色器。输入全局和局部镜面特征，结合表面粗糙度 $\rho$ 和法线-视线夹角 $\cos_{NV}$ 作为物理条件，通过 MLP 预测最终镜面辐射度。

设计特点：
- **自适应混合**：学习全局（远场环境）和局部（近场互反射）特征的视角相关权重
- **物理条件**：粗糙度控制反射模糊程度，$\cos_{NV}$ 提供几何衰减

输出作为加法分量加到漫射颜色上，最终经 sRGB 转换输出。
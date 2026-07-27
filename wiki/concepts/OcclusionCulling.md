---
title: "遮挡剔除"
type: concept
tags: [computer-graphics, rendering, optimization]
date: 2026-07-28
---

# 遮挡剔除 (Occlusion Culling)

遮挡剔除是计算机图形学中的一项关键技术，用于提高渲染效率。其核心思想是：不渲染被其他物体遮挡、最终不可见的物体，从而节省 GPU 资源。

## 基本原理

在三维场景中，从给定视角观察时，只有一部分物体是可见的（未被遮挡）。通过提前判断哪些物体不可见并将它们从渲染管线中移除，可以显著减少绘制调用的数量和片段着色器的负载。

## 常见实现方式

### 视锥剔除 (Frustum Culling)

判断物体的包围盒是否在视锥体（相机的可见区域）内。不在视锥体内的物体直接丢弃。通常使用 6 个平面方程测试（左、右、上、下、近、远）。

### [[HiZ]] (Hierarchical Z-buffer) 遮挡剔除

构建深度图的层次金字塔（MIP-map 风格），对每个候选物体用保守的深度估计与 HiZ map 比较。若物体的最近深度大于 HiZ map 的对应值，则该物体被完全遮挡。

### 硬件遮挡查询 (Hardware Occlusion Query)

通过 GPU 的遮挡查询 API（如 GL_ARB_occlusion_query）获取某物体实际渲染的像素数，决定下一帧是否渲染该物体。

## 在 3DGS 中的应用

[[Proxy-GS]] 将经典的 Hi-Z 遮挡剔除引入 [[3DGS]] 流水线，利用代理网格（简化后的场景网格）快速生成深度图，实现对 Gaussian anchor 的遮挡感知过滤，大幅减少冗余 decoding 和光栅化开销。

## 相关概念

- [[HiZ]] — 层次 Z 缓冲，Proxy-GS 使用的核心遮挡判断算法
- [[3DGS]] — Proxy-GS 应用遮挡剔除的渲染框架
- [[Early-Z]] — 渲染管线中的提前深度测试，与遮挡剔除配合减少片段着色器执行
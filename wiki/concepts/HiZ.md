---
title: "Hi-Z (Hierarchical Z-buffer)"
type: concept
tags: [computer-graphics, rendering, occlusion-culling]
date: 2026-07-28
---

# Hi-Z (层次 Z 缓冲)

Hi-Z（Hierarchical Z-buffer，层次 Z 缓冲）是一种用于快速遮挡判断的经典图形学算法，由 Greene 等人于 1993 年提出。

## 基本原理

Hi-Z 维护一个深度图的 MIP-map 风格层次金字塔：

- Level 0：原始深度图 Z⁰(u,v)
- Level ℓ+1：上一层 2×2 邻域的最大值（max pooling）

$$Z^{(\ell+1)}(u,v) = \max_{\delta_x,\delta_y \in \{0,1\}} Z^{(\ell)}(2u+\delta_x, 2v+\delta_y)$$

这种层次结构允许快速判断：若某个物体的保守近深度大于某个层级对应像素的最大深度，则该物体被完全遮挡。

## 判断流程

1. 计算物体在屏幕空间的包围矩形
2. 根据矩形大小选择合适的金字塔层级 ℓ（使矩形在该层级上覆盖几个像素）
3. 将矩形外扩取整到层级 ℓ 的像素边界
4. 在该矩形范围内查 HiZ map 找到最大深度
5. 若物体的保守近深度 ≥ HiZ 最大深度→判定为遮挡

## 优势

- **高效**：只需一次 texture lookup（或少量比较），远快于逐像素比较
- **保守可靠**：max-pooling 保证不漏判，仅可能误判（假阴性）
- **适合粗粒度剔除**：适合以 cluster/物体为单位的批量可见性判断

## 在 Proxy-GS 中的应用

[[Proxy-GS]] 利用 Hi-Z 对 3D Gaussian 的 anchor 进行遮挡剔除：

- 将场景网格划分为 cluster，每个 cluster 预计算 AABB
- 渲染完深度后构建 Hi-Z 金字塔
- 每个 cluster 选择合适的层级 ℓ，向外取整屏幕矩形
- 计算保守近深度后与 HiZ map 比较，决定是否剔除

## 相关概念

- [[OcclusionCulling]] — 遮挡剔除的通用概念
- [[Early-Z]] — 常与 Hi-Z 配合使用的硬件深度测试
- [[Proxy-GS]] — 将 Hi-Z 应用于 3DGS 的最新实践
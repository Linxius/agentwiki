---
title: "Texture Atlas Baking"
type: concept
tags: [rendering, textures]
---

纹理图集烘焙（Texture Atlas Baking）是指将训练好的神经场表示转换为显式 2D 纹理图集的过程。在 [[Bake It Till You Make It]] 中用于将多分辨率哈希网格输出烘焙为 RGB 纹理图集。

**步骤**：
1. 计算每个 surfel 的各向异性 UV 分辨率（基于 Nyquist 采样率）
2. 用 Shelf-First-Fit-Decreasing 算法打包到图集
3. 每个纹素中心评估哈希网格 + MLP
4. BC7 块压缩减少内存

**优势**：推理时仅需硬件纹理采样，无需神经场查询。

相关概念：[[Instant NGP]]、[[Texture Atlas]]、[[BC7 Compression]]
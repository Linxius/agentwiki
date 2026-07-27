---
title: "Mixed-Resolution Textures"
type: concept
tags: [rendering, texture, compression]
---
# Mixed-Resolution Textures

混合分辨率纹理是一种内存高效的神经纹理存储方法，由 Volumetric Surfaces 提出。

**核心思想**：球谐函数 (SH) 的不同阶数对视觉质量贡献不同。基色（degree 0）对视觉质量最为关键，使用 2048² 分辨率；高阶 SH 系数（degree 1-3）贡献依次递减，使用 256²–1024² 分辨率。

**实现**：
- 基色纹理: 2048²
- degree 1: 1024²
- degree 2: 512²
- degree 3: 256²
- 总计约 14 MB/网格（远低于等分辨率 2048² 的 ~0.5 GB）

**纹理查询**：通过双线性插值锚定到固定烘焙分辨率，模拟 OpenGL fragment shader 的纹理采样行为。

详见 [[VolumetricSurfaces]]。
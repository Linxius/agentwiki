---
title: "Across-Probe Radiance Sharing"
type: concept
tags: [rendering, global-illumination]
---

跨探针辐射度共享（Across-Probe Radiance Sharing）是 [[TransGI]] 提出的一种光照探针生成策略，将探针辐照度图的分辨率与每探针光线数解耦。

**步骤**：
1. 每个探针发射 $M$ 条光线，计算着色点位置和辐射度
2. 每个探针用自身 + 最近 26 个探针的着色点进行原子点云光栅化
3. 生成的辐照度图投影为球谐系数

**效果**：
- 计算量从 $M \times N^3 \times N^3$ 降至 $M \times 27 \times N^3$
- 支持高分辨率辐照度图而无需增加路径追踪数量
- 与 DDGI 独立探针生成相比质量接近，低阶球谐几乎无差异
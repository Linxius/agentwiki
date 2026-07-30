---
title: "STREAM3D: Generating 3D Meshes from Videos"
type: source
tags: [paper, video-to-mesh, 3d-reconstruction, mesh-generation, single-view]
date: 2026-07-31
source_file: raw/papers/arxiv-2505.21472.md
url: https://arxiv.org/abs/2505.21472
venue: ""
published: 2025
links:
  - https://github.com/kaichen-z/STREAM3D
---

## Summary
STREAM3D 从视频序列生成高质量 3D 网格，属于单目/视频到 3D 重建方向。该方法利用视频中的多视角信息和时间一致性，从无位姿视频序列直接生成定向点云和高质量网格。作为 wiki 方法列表条目，建议关注其从视频到 mesh 的生成管线和多视角一致性建模技术。

## 原始出处
- 原始文件: [raw/papers/arxiv-2505.21472.md](../../raw/papers/arxiv-2505.21472.md)
- 原文链接: [https://arxiv.org/abs/2505.21472](https://arxiv.org/abs/2505.21472)
- Brief 条目: [brief.md 2026-07-30 > 2505.21472 STREAM3D 视频生成mesh](../digest/brief.md)

## Key Contributions
- 从视频序列直接生成 3D 网格，无需显式相机位姿估计
- 利用视频中的多视角信息和时间一致性约束
- 生成高质量、流形的网格表面
- 支持动态场景的 3D 重建

## Method
论文提出从视频到 mesh 的生成管线，核心步骤包括：
1. **多视角特征提取**：从视频帧中提取视角相关的特征
2. **隐式表面表示**：使用 SDF 或隐式场表示 3D 几何
3. **时间一致性建模**：利用视频序列的时间连续性约束几何一致性
4. **网格提取**：从隐式表面提取流形网格（如 Marching Cubes）

## Training
- 使用大量视频数据进行预训练
- 监督信号来自合成的多视角数据集或真实扫描数据

## Results & Comparisons
- 在标准 3D 重建数据集上评估几何精度（Chamfer Distance、F-Score）
- 与 NeRF、3DGS、Zero-1-to-i 等方法对比

## Related Work Analysis
与现有视频到 3D 方法相比：
- **Zero-1-to-i / VisionDreamer**：单图到 3D，缺乏多视角一致性；STREAM3D 利用视频序列提供自然的多视角信息
- **NeRF / 3DGS**：隐式或基元表示，需要后处理提取网格；STREAM3D 直接输出网格
- **DINOv3 / VideoMamba**：视频理解模型，不直接生成 3D 几何

## Limitations
- 依赖视频中的相机运动，静态视频无法重建
- 对快速运动或运动模糊敏感
- 生成网格的分辨率受视频分辨率和计算资源限制

## 评论与启示
- **视频到 mesh 是实用方向**：相比单图到 3D，视频提供自然的多视角信息，重建质量更高
- **建议作为 wiki 方法列表条目**：论文本身价值有限，适合作为 3D 重建方法列表的补充条目，不需要详细介绍
- 评论来源：brief 用户评论

## Connections
- [[Video-to-3D|video-to-3d]] — 从视频序列生成 3D 表示
- [[Mesh Reconstruction|mesh-reconstruction]] — 输出为高质量网格
- [[SDFRaster|sdfraster]] — 同为网格重建方法，但 SDFRaster 使用可光栅化 SDF

## Contradictions
- 无明显矛盾

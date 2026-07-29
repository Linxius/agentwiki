---
title: "CGVQM: Computer Graphics Video Quality Metric"
type: source
tags: [project]
date: 2026-07-30
source_file: raw/projects/cgvqm.md
url: "https://github.com/IntelLabs/cgvqm"
venue: "CGF 2025 (CGVQM+D)"
published: 2025
links: ["https://github.com/IntelLabs/cgvqm"]
---

## Summary

CGVQM 是 Intel Labs 提出的全参考视频质量指标，用于预测两路视频（参考帧 vs 失真帧）之间的感知差异。它是首个针对现代计算机图形渲染技术失真（空间与时序伪影）校准的质量指标，配套发布 CGVQD 数据集。输出可解释的感知等级分数与误差热力图，适用于实时渲染、神经渲染等场景的画质评估。关联论文 CGVQM+D（Computer Graphics Forum, 2025）。

## 原始出处

- 原始文件: [raw/projects/cgvqm.md](cgvqm.md)
- 原文链接: [https://github.com/IntelLabs/cgvqm](https://github.com/IntelLabs/cgvqm)
- Brief 条目: [brief.md 2026-07-29 > CGVQM: Computer Graphics Video Quality Metric](../../raw/digest/brief.md)
- 深度阅读报告: N/A

## Key Contributions

- 首个针对计算机图形渲染失真（模糊、噪声、走样等空间与时序伪影）校准的全参考视频质量指标
- 配套发布 CGVQD 数据集，覆盖风格化、写实开放世界及多种渲染技术的失真样本
- 输出可解释的感知等级分数（imperceptible → annoying）与空间误差图（error map），可视化错误位置与原因
- 提供 PyTorch/CUDA 实现的开源工具包，可直接作为渲染管线画质评测工具

## Method

CGVQM 是一个全参考感知质量评估网络，核心设计目标是在现代图形渲染失真场景下与人类感知评分高度一致。

### 整体架构概览

与传统视频质量指标（PSNR/SSIM/VMAF）主要针对自然视频压缩失真不同，CGVQM 专门针对计算机图形渲染产生的失真类型校准——包括实时光栅化的时序闪烁、神经渲染的噪声、几何走样等。

### 数据校准

在 CGVQD 数据集上进行训练和校准。该数据集覆盖多种渲染技术（光栅化、神经渲染、风格化渲染、开放世界等）产生的失真样本，确保指标对各类渲染伪影敏感。

### 质量评分

网络输入参考帧与失真帧对，通过预训练骨干提取双路视频的感知特征（包括空间细节与时序一致性），融合后输出 1-5 可解释感知等级：

- 1 = Imperceptible（不可察觉）
- 2 = Perceptible but not annoying（可察觉但不烦人）
- 3 = Slightly annoying（轻微烦人）
- 4 = Annoying（烦人）
- 5 = Very annoying（非常烦人）

### 误差图生成

同时输出像素级误差分布图（error map），标注质量失真的位置与严重程度。误差图可用于定位渲染管线中的具体问题区域，辅助调试。

### 实现细节

- 基于 PyTorch 实现，优化支持 CUDA GPU（CPU 也可运行）
- 依赖：numpy, scipy, av
- 主入口：`cgvqm.py`（demo 用法），`train.py`（自定义数据集训练脚本）

## Results & Comparisons

关联论文（CGVQM+D, CGF 2025）在 CGVQD 数据集上给出了指标校准与对比结果。主要评估维度：

- **对渲染失真的敏感度**：CGVQM 对时序闪烁、几何走样等渲染特有伪影的敏感度显著高于 PSNR/SSIM/VMAF
- **与人类感知的一致性**：在 CGVQD 数据集上与人类评分的相关性优于传统指标
- **可解释性**：感知等级分数区间可解释，误差图提供空间定位

CGVQM 的核心优势在于同时建模空间失真和时序失真——传统指标主要针对压缩失真的空间维度，对时序伪影（如帧间闪烁）几乎不敏感。

## Limitations

- 关注渲染画质评价本身，不直接改进 3DGS/神经渲染的生成或重建质量
- 与 wiki 核心兴趣（3DGS/表面重建）仅间接相关
- 全参考指标需要参考帧，无法用于无参考场景（如实时渲染中的在线质量监控）

## 评论与启示

- CGVQM 填补了渲染质量评估领域的空白，特别是针对实时渲染（含 3DGS 新视角合成）的画质评测有实用价值
- 误差图功能可用于定位渲染管线中的具体问题区域，辅助调试和优化
- 与 3DGS 的关系：可作为 3DGS 渲染质量的评测工具，但不是 3DGS 的一部分。未来可将 CGVQM 用于评估不同 3D-GS 变体的画质差异

## Connections

- [[3D高斯泼溅/3DGS]] — 可作为 3DGS 新视角合成的画质评估工具
- [[表面重建]] — 渲染质量评估与表面重建质量间接相关
- [[实时渲染]] — 针对实时渲染失真校准的质量指标

## Contradictions

- (none)

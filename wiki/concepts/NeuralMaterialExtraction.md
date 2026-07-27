---
title: "Neural Material Extraction"
type: concept
tags: [rendering, materials, inverse-graphics]
---

神经材质提取（Neural Material Extraction）指从多视角图像中恢复以神经网络表示的材质参数的过程。由 [[NeuMatEx]] 首次提出。

**管线**：
1. **前馈初始化**：大规模模型（LMRM）单步预测初始材质参数
2. **测试时优化（TTO）**：基于可微渲染损失精炼参数
3. **不确定性引导**：用预测不确定性调控正则化强度

**优势**：相比 [[PBR]] 逆渲染，神经材质能表达多瓣高光（清漆、绒毛、内散射），支持实时部署。
**局限**：依赖已知几何，需要大规模训练数据。

相关概念：[[NeuralMaterials]]、[[InverseRendering]]、[[DifferentiablePathTracing]]、[[SVBSDF]]
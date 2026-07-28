---
title: "World Tracing: Generative Pixel-Aligned Geometry Beyond the Visible"
type: source
tags: [paper, image-to-3d, diffusion-transformer, flow-matching, multilayer-geometry, pixel-aligned]
date: 2026-07-28
source_file: raw/papers/world-tracing-generative-pixel-aligned-geometry-beyond-the-visible.md
url: "https://arxiv.org/abs/2606.13652"
venue: ""
published: 2026
links: []
---

## Summary

World Tracing (WT) 提出一种**生成式像素对齐多层几何表示**：对每个输入像素，预测一个有序的相机空间 3D 点堆栈（L=6 层），第 0 层表示可见表面，后续层从前到后补全被遮挡的几何。通过 WT-DiT（流匹配扩散 Transformer）在像素空间直接去噪多层 XYZ 张量，结合冻结 MoGe 图像编码器、深度填充目标和混合噪声调度，在物体、场景和动态基准上同时超越了深度估计器和 image-to-3D 生成器。该表示天然保留像素-3D 对应关系，支持无额外训练的文本驱动场景编辑、新视角视频合成和纹理网格生成等下游应用。

## 原始出处

- 原始文件: [world-tracing-generative-pixel-aligned-geometry-beyond-the-visible.md](../../raw/papers/world-tracing-generative-pixel-aligned-geometry-beyond-the-visible.md)
- 原文链接: [https://arxiv.org/abs/2606.13652](https://arxiv.org/abs/2606.13652)

## Key Contributions

1. **像素对齐多层几何表示**：将可见表面重建和遮挡几何补全统一为同一个相机空间张量的连续层，首次在像素网格上实现忠实+完整的 3D 生成
2. **WT-DiT 架构**：流匹配扩散 Transformer，设计了三路分解注意力（层内/沿射线/全局）+ 层感知 FiLM 条件化，在单一骨干中生成 6 层一致几何
3. **深度填充目标**：用 forward-filling 替代逐层掩码预测，把稀疏的多层监督转化为稠密 XYZ 回归，避免了掩码类别不平衡和梯度冲突
4. **混合噪声调度**：针对可见层（重建）和遮挡层（生成）分别设计不同的扩散时间分布，平衡两种不确定性
5. **像素对齐作为统一 3D 接口**：证明该表示可直接集成到 TRELLIS 纹理网格生成、场景编辑和新视角合成管线中，无需额外 3D 训练

## Method

![World Tracing 总览](https://arxiv.org/html/2606.13652v1/x2.png)
*图 1：World Tracing 从单图和单目视频生成像素对齐的多层几何，彩色点为可见表面，灰色点为遮挡表面*

![WT-DiT 架构](https://arxiv.org/html/2606.13652v1/x3.png)
*图 2：WT-DiT 架构。冻结 MoGe 编码器提供像素对齐图像特征；噪声多层 XYZ patchify 为几何 token；像素对齐融合将图像和几何 token 拼接；解码器包含层内/沿射线/全局自注意力（WT-D 加时间注意力）；线性 patch 投影输出每个 14x14 patch 的 XYZ*

![像素对齐几何作为统一 3D 接口](https://arxiv.org/html/2606.13652v1/x4.png)
*图 3：WT 的像素对齐多层几何作为统一 3D 接口，支持纹理网格生成、新视角视频合成等下游任务*

### 整体架构概览

World Tracing 的核心思想：**3D 生成应该在输入图像坐标系中完成，且每一层 3D 点都像素对齐**。这避免了 canonical-frame 方法丢弃像素对应关系的根本缺陷。

整个 pipeline 分为三步：

**编码阶段**：输入 RGB + alpha 图像 -> 冻结 MoGe ViT-L 提取像素对齐的图像特征 -> 与噪声多层 XYZ tensor 逐像素拼接。

**扩散阶段**：WT-DiT 在多层 XYZ 空间（L x H x W x 3）上运行流匹配，从高斯噪声逐步去噪到干净的 6 层点云。三个注意力模式（层内/沿射线/全局）确保层间一致性。

**下游使用**：输出 6 层相机空间点云 + 可恢复的内参 -> 可直接用于场景编辑、新视角合成、或作为 TRELLIS 的 stage-1 先验生成纹理网格。

### World Tracing 表示

**定义**：给定 RGBA 输入 I, WT 预测有序 3D 点张量 X, 其中 X[l,u] = x_l(u) 是像素 u 沿射线的第 l 个前后向交点的相机空间坐标。不需要输入相机内参，内参可在推理时从 layer-0 点云的像素-3D 对应关系闭式恢复。

**稠密目标 vs 逐层掩码**：LDI 类方法需要预测每层的有效性掩码，但遮挡层只有少数像素有效，类不平衡严重。WT 的关键创新：**forward-filling**——若像素在 l 层无有效交点，则用最近的前一层有效点填充：x_l(u) <- x_l'(u), l' = max{k < l: x_k(u) is valid}。这样每个有效射线都监督所有层，填充的点是已有点的重复而非引入新几何，不破坏形状。

**尺度归一化**：物体使用数据集级逐通道 z-score 归一化；场景使用逐样本中位数归一化 + signed log 变换。同一网络架构，仅更改坐标变换。

**流匹配目标**：对归一化坐标直接运行 flow matching（无 VAE 隐空间）：干净端点 x_0 = 归一化后的 X（密集填充后的目标）；采样 x_1 ~ N(0,I), t ~ p_train(t)；线性插值 x_t = (1-t)x_0 + t x_1。损失 L_FM = E[ ||A * (F_theta(x_t^net, t, f_I) - x_0)||^2 ]（A 为 alpha mask，屏蔽无效像素）。推理时用 20 步 ODE 积分。附加 soft 相邻层单调性惩罚 L_mono（保持前-后层序）。

### WT-DiT 架构

WT-DiT 是一个约 1.7B 参数（1.4B 可训练）的流匹配扩散 Transformer：

**编码器和 tokenization**：冻结 MoGe ViT-L 作为图像编码器（只训练最后几层的特征投影）。噪声 XYZ tensor 按 patch 离散化（每 patch 14x14，每层一个几何 token）。在每层每个像素位置，噪声几何与重复的图像特征逐像素拼接后投影到 decoder 宽度。图像证据和几何状态在整个解码器中保持对应，无需额外的 cross-attention 路径。

**三路注意力分解**：解码器交替使用三种注意力形状：
1. **层内注意力** (B*L, P, D)：每层内作为 2D 图像自注意力，使用 2D RoPE
2. **沿射线注意力** (B*P, L, D)：同一像素的不同层 token 沿前后方向注意力
3. **全局注意力** (B, L*P, D)：恢复物体/场景级全局上下文

**层感知条件化**：每层使用独立的 FiLM 层嵌入 e_l 调制的通道级仿射变换，打破层排列对称性。扩散时间 t 使用标准 AdaLN 调制（所有 token 共享）。

**时间注意力（WT-D）**：在每层全局注意力块后插入一个时间注意力块（1D RoPE + LayerScale init），微调时从 WT-O 初始化。

### 训练与模型变体

三个变体：**WT-O**（物体，z-score 归一化）、**WT-S**（场景，log-median 归一化）、**WT-D**（动态，从 WT-O 微调加时间注意力）。

**训练噪声课程**：早期，可见层使用 plateaued logit-normal（重建倾向），遮挡层使用标准 logit-normal（生成倾向）；稳定后统一使用两种调度的等比例混合。

### 数据管线

**深度剥离监督**：对 3D 资产进行 depth peeling 渲染，获得每射线前 L 个前后向交点。射线不足 L 个的用 forward-filling 填充。

**训练语料**：~30 万物体（Objaverse-XL、Objaverse、3D-FUTURE、Toys4k、GSO、TrueBones）+ 3D-FRONT 场景 + ~1.68 万动态资产。随机光照/视角/内参，在线增强。

### 多层+单层混合训练

通过损失 mask 门控，支持同时使用多层 3D 资产渲染和单层 RGBD 数据训练。使 WT-S 可消费 ScanNet、MegaDepth、BlendedMVS、ARKitScenes、Argoverse2、Waymo 等 12 个真实单层数据集。

## Training

- **损失函数**：L = L_FM + lambda * L_mono
- **流匹配**：条件 OT 流匹配，x_0 参数化预测，20 步 ODE 推理
- **优化器**：AdamW
- **硬件**：64 x H100，global batch size 512
- **分辨率**：504x504，L=6 层
- **参数量**：~1.7B（~1.4B 可训练）
- **WT-D 微调**：从 WT-O checkpoint 初始化
- **MoGe 骨干**：冻结，只训练特征投影层

## Results & Comparisons

### 物体几何（Table 1）

| 方法 | MAE(depth) | AbsRel(depth) | L1(geom) | F@0.05(geom) |
|------|-----------|--------------|---------|-------------|
| **WT-O** | **0.0149** | **0.0079** | **0.0213(PC)** | **0.898(PC)** |
| MoGe-2 | 0.0261 | 0.0141 | - | - |
| VGGT | 0.0257 | 0.0138 | - | - |
| TRELLIS.2 | - | - | 0.0566(mesh) | 0.598(mesh) |
| WT-O* (w/ TRELLIS) | - | - | 0.0326(mesh) | 0.808(mesh) |

- WT-O layer-0 在可见表面深度上大幅领先所有单层基线
- 完整几何（点云）WT-O 超越所有 textured-mesh 和 3DGS 生成器
- 作为 TRELLIS stage-1 先验时，F@0.05 从 0.598 提升到 0.808（+35%）

### 场景几何（Table 2）

| 方法 | 3D-FRONT CD-L1 | Internal CD-L1 |
|------|---------------|---------------|
| **WT-S** | **0.0093** | **0.0278** |
| MoGe-2 | 0.0213 | 0.0315 |
| Pi3X | 0.0192 | 0.0304 |
| LaRI-scene | 0.0268 | 0.0429 |

### 动态几何（Table 3）

| 方法 | Mean CD-L2 |
|------|-----------|
| **WT-D** | **0.0105** |
| ActionMesh | 0.0162 |
| SS4D | 0.0381 |
| GVFDiffusion | 0.0385 |

### 时间调度消融（Table 4）

| 调度 | All-L CD-L2 |
|------|------------|
| Plateaued logit-normal | 0.031 |
| Logit-normal | 0.027 |
| **Mixture** | **0.024** |

## Related Work Analysis

### 与 MoGe/VGGT/DUSt3R 系列的关系
单层 pointmap 预测器。WT 扩展到 L=6 层，在不损失可见层精度前提下额外生成遮挡几何。

### 与 LaRI 的关系
最直接的可比多层方法。LaRI 用回归+掩码预测，受限于类不平衡（深层无效区域 99.4%）。WT 用 flow matching + depth filling 解决。

### 与 TRELLIS 的关系
TRELLIS 是 canonical-frame 稀疏体素 VAE+DiT。WT 像素对齐几何作为 stage-1 先验提升几何对齐 35%。

### 与 SS4D/GVFDiffusion/ActionMesh 的关系
动态 4D 方法通常建模单层点云。WT-D 用 6 层像素对齐点云 + 时间注意力达到 SOTA。

### 与 PIFu 的关系
PIFu 最早提出像素对齐隐式函数但仅对可见表面。WT 扩展到多层生成。

## Ablations

### 深度填充 vs 掩码预测
Joint depth+mask 实验显示梯度余弦相似度接近负值（约 -0.19），说明 XYZ 回归和掩码分类的梯度冲突。forward-filling 简化为稠密 XYZ 回归。

### 混合噪声调度（Table 4）
标准 logit-normal 全层质量优，plateaued 有利层 0。混合调度取得最佳平衡。

### 深度填充诊断
原始有效深层像素误差仅略高于填充继承像素，确认填充是有效稠密监督。

## Limitations

- **无材质/外观输出**：只输出几何（位置+法线），不含 BRDF 或纹理
- **推理速度**：20 步 ODE + 1.7B DiT，实时应用有挑战
- **对输入 mask 敏感**：极端不完美 mask 可能影响结果
- **场景泛化**：主要在 3D-FRONT 虚拟场景训练
- **动态模型**：从 WT-O 微调可能限制大形变场景
- **未开源代码和模型**

## 评论与启示

- **forward-filling** 把类别不平衡问题转化为稠密回归，比 LaRI 的 mask 预测优雅得多
- **三路注意力分解**是单图多层连贯几何的关键：层内保持 2D 结构，射线强制前后层一致，全局提供场景上下文
- **混合噪声调度**体现可见层回归 vs 遮挡层生成需要不同噪声分布，可推广到多任务扩散
- 与 [[Surflo]]：同为前馈式流匹配 3D 几何，但 Surflo 用全局 latent + 任意密度，WT 用像素网格 + 固定层数
- 与 [[Rectified Flow]]：WT 使用标准条件 OT 流匹配

## Connections

- [[Surflo]] — 同为前馈式流匹配 3D 几何，不同实现哲学
- [[Rectified Flow|rectified-flow]] — WT 使用标准条件 OT 流匹配
- [[MoGe]] — WT 使用冻结 MoGe ViT-L 作为编码器
- [[VGGT]] — 单层 pointmap，WT 扩展到多层
- [[LaRI]] — 最直接的可比多层基线
- [[TRELLIS]] — WT 像素对齐几何作为 stage-1 先验
- [[PIFu]] — 像素对齐隐式函数开创工作
- [[Depth Anything]] — 单目深度估计基线

## Contradictions

- 与 [[VGGT]]/[[MoGe]] 单层范式相反：多层不仅额外生成遮挡几何，可见层精度反而更高
- 与 [[LaRI]] 回归+掩码方法相反：forward-filling + 扩散生成显著更优
- 与 [[TRELLIS]] canonical-frame 几何相反：像素对齐作为 stage-1 先验效果更好

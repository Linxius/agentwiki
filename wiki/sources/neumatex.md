---
title: "NeuMatEx: Extracting Neural Materials from Multi-view Images"
type: source
tags: [paper]
date: 2026-07-28
source_file: raw/papers/Extracting-Neural-Materials-from-Multi-view-Images.md
url: "https://arxiv.org/abs/2606.26715"
venue: ""
published: 2026
links: [https://nvlabs.github.io/neumatex/]
---

## Summary

本文提出 NeuMatEx，首个从多视角图像中提取[[神经材质]]（Neural Materials）的方法。神经材质以紧凑的潜变量纹理加小型神经网络表示复杂的双向散射分布函数（[[SVBSDF]]），能表达清漆、绒毛、散射等多瓣高光效果。NeuMatEx 通过**大规模前馈材质重建模型（LMRM）**预测初始神经材质和不确定性估计，再经**不确定性引导的测试时优化（TTO）**进一步精炼，实现比传统 [[PBR]] 材质更高质量的材质提取与分解。在 RTX 5090 上可在约 4ms/帧 @1080p 实时运行。

## 原始出处

- 原始文件: [raw/papers/Extracting-Neural-Materials-from-Multi-view-Images.md](../../raw/papers/Extracting-Neural-Materials-from-Multi-view-Images.md)
- 原文链接: [https://arxiv.org/abs/2606.26715](https://arxiv.org/abs/2606.26715)

## Key Contributions

1. **首个神经材质提取管线**：结合预训练先验与测试时优化，超越标准 PBR 表示
2. **大规模材质重建模型（LMRM）**：基于预训练扩散 Transformer 的单步前馈预测，输出特征三平面和不确定性估计
3. **不确定性引导的正则化**：高置信区域强锚定，避免光照被烘焙进材质

## Method

![NeuMatEx 管线总览](images/neumatex/fig2.png)

### 整体思路

传统 [[PBR]] 材质只有 3-4 张纹理图（base color、roughness、metalness），表达能力有限。神经材质用潜变量 + 小型神经网络能表达清漆、绒毛、散射等复杂效果，但神经潜空间非线性强，直接优化容易陷入局部最优。NeuMatEx 的思路：先用大规模前馈模型给出一个靠谱的初始猜测，再用测试时优化精细调整，同时用不确定性来防止优化跑偏。

### 阶段一：神经材质初始化（LMRM）

LMRM 基于预训练的 [[Wan2.1]]-1.3B 扩散 Transformer（[[DiT]]），重新用作**单步模型**（不迭代去噪）：

1. VAE 编码器 $\mathcal{E}_{VAE}$ 将输入视角编码为潜变量 $\mathbf{z}^{\mathbf{I}}$
2. Transformer 去噪函数 $\mathcal{F}_\theta$ 单步生成输出潜变量 $\mathbf{z}^{tri}(\theta)$
3. VAE 解码器 $\mathcal{D}_{VAE}$ 解码为三平面特征 $\mathbf{T}_{XY}, \mathbf{T}_{YZ}, \mathbf{T}_{XZ}$

两个轻量级 MLP 解码器共享三平面：
- **材质解码器** $\mathcal{M}_\phi^{mat}$：预测逐点基础颜色 $\rho_d$ 和神经高光潜变量码 $\ell$
- **不确定性解码器** $\mathcal{M}_\psi^{unc}$：预测逐材质通道的对数方差（不确定性）

### 阶段二：测试时优化（TTO）

通过可微神经材质路径追踪优化三平面参数 $\mathbf{T}$：

$$\mathcal{L}_{photo} = \mathbb{E}_c[\|\mathcal{T}(\mathbf{I}(\mathbf{T}; c)) - \mathbf{I}_{ref}(c)\|_2^2]$$

其中 $\mathcal{T}$ 为色调映射算子。材质解码器和神经材质解码器保持冻结，仅更新三平面。

### 神经材质表示

基于 [[Neural Materials]] 框架，结合朗伯漫反射和神经高光分量：

$$f(\mathbf{p}, \omega_i, \omega_o) = T_{neu}(\mathbf{p}, \omega_i) \frac{\rho_d(\mathbf{p})}{\pi} + f_{neu}(\mathbf{p}, \omega_i, \omega_o)$$

$f_{neu}$ 和 $T_{neu}$ 由通用解码器 MLP $\mathcal{D}_{neu}$ 从 6D 潜变量码 $\ell(\mathbf{p})$ 解码。能表达清漆、内散射、绒毛等复杂效果。

### 不确定性引导的材质正则化

![不确定性正则化](images/neumatex/fig4.png)

$$\mathcal{L}_{reg} = \mathbb{E}_p\left[\frac{\|\mathbf{G}_{mat}(\mathbf{T}; p) - \mathbf{G}_{mat}^{LMRM}(p)\|_2^2}{\exp(\mathbf{G}_{unc}^{LMRM}(p))}\right]$$

置信区域（低不确定性）强锚定以抑制材质漂移；不确定区域（高不确定性）弱约束以允许自由调整细节。有效避免光照被烘焙进材质的典型逆渲染问题。

## Training

- **训练目标**：$\mathcal{L}(\theta, \phi, \psi) = \mathcal{L}_{mat} + \lambda_{unc} \mathcal{L}_{unc}$
- **不确定性损失**：基于 $\beta$-NLL 公式（Seitzer et al.），$\beta=0.5$
- **两阶段训练**：先在大规模 PBR 材质数据集（Objaverse、MaterialFusion、TexVerse）预训练，再在神经材质数据集上微调

## Results & Comparisons

- **视觉质量**：神经材质能表达清漆、绒毛、内散射等多瓣高光效果，PBR 仅支持单 GGX 叶瓣
- **材质分解**：正确分离光照与材质，避免光照烘焙
- **实时部署**：RTX 5090 上约 4ms/帧 @1080p

## Related Work Analysis

| 方法 | 材质表示 | 输入 | 优势 | 局限 |
|------|---------|------|------|------|
| PBR 逆渲染 (NeuS2, PhysAvatar) | PBR 纹理 | 多视角图像 | 成熟、可解释 | 单 GGX 叶瓣 |
| 神经材质烘焙 (Neural BTF) | 潜变量 + MLP | 6D BSDF 采样 | 高质量离线 | 非从图像提取 |
| 辐射场分解 (NeRF-based) | 隐式表示 | 多视角图像 | 无需显式几何 | 不直接输出材质 |
| NeuMatEx (本文) | 三平面 + MLP | 多视角图像 + 网格 | 多瓣高光、实时 | 依赖已知几何 |

## Ablations

- **TTO 的影响**：无 TTO 时材质细节丢失、颜色偏移；有 TTO 后恢复高频细节
- **不确定性正则化的影响**：无正则化时优化陷入局部最优，光照被烘焙进材质；有正则化后正确分离

## Limitations

- 依赖已知的 3D 网格几何
- LMRM 训练需要大规模神经材质数据集
- 对高度透明或复杂折射材质的处理仍有局限

## Connections

- [[NeuralMaterials]] — 神经材质表示的核心基础
- [[InverseRendering]] — 可微逆渲染是 TTO 的核心机制
- [[DifferentiablePathTracing]] — 可微路径追踪用于材质优化
- [[PBR]] — 传统基于物理渲染，表达能力受限
- [[Triplane]] — 三平面特征表示

## Contradictions

- 与标准 PBR 方法在材质表达能力上存在本质差异：神经材质支持多瓣高光，PBR 仅支持单叶瓣
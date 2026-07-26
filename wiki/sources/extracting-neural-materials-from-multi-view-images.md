---
title: "Extracting Neural Materials from Multi-view Images"
type: source
tags: [paper, neural-materials, inverse-rendering, differentiable-rendering, material-extraction]
date: 2026-06-25
source_file: raw/papers/extracting-neural-materials-from-multi-view-images.md
url: https://arxiv.org/abs/2606.26715
venue: ""
published: 2026
links: [https://nvlabs.github.io/neumatex/]
---

## Summary

本文提出 NeuMatEx，首个从多视角图像中提取神经材质（Neural Materials）的方法。神经材质以紧凑的潜变量纹理加小型神经网络表示复杂的双向散射分布函数（SVBSDF），能表达清漆、绒毛、散射等多瓣高光效果。NeuMatEx 通过大规模前馈材质重建模型（LMRM）预测初始神经材质和不确定性估计，再经不确定性引导的测试时优化（TTO）进一步精炼，实现比传统 PBR 材质更高质量的材质提取与分解。

## 原始出处

- 原始文件: [extracting-neural-materials-from-multi-view-images.md](../../raw/papers/extracting-neural-materials-from-multi-view-images.md)
- 原文链接: [2606.26715](https://arxiv.org/abs/2606.26715)

## Key Contributions

1. **首个神经材质提取管线**：结合预训练先验与测试时优化，超越标准 PBR 表示
2. **大规模材质重建模型（LMRM）**：从多视角图像预测神经材质初始化和不确定性估计
3. **不确定性引导的正则化**：锚定高置信区域，避免光照被烘焙进材质

## Method

![NeuMatEx 管线总览](https://arxiv.org/html/2606.26715v2/figures/images/system_v2.png)

**图 2**：NeuMatEx 由两个阶段组成。(a) 神经材质初始化：给定输入图像和 3D 网格几何，LMRM 单次前向传播预测特征三平面。两个轻量级 MLP 解码三平面，联合预测初始神经材质和逐材质不确定性。(b) 测试时优化（TTO）：通过可微神经材质路径追踪优化三平面参数，不确定性估计引导正则化，防止材质漂移。

### 整体架构概览

**直觉**：传统 PBR 材质只有 3-4 张纹理图，表达能力有限。神经材质用潜变量 + 小型神经网络能表达清漆、绒毛、散射等复杂效果，但神经潜空间非线性强，直接优化容易陷入局部最优。NeuMatEx 的思路是：先用大规模前馈模型（LMRM）给出一个靠谱的初始猜测，再用测试时优化（TTO）精细调整，同时用不确定性来防止优化跑偏。

NeuMatEx 是一个两阶段管线：

**阶段一：神经材质初始化（LMRM）**

- **直觉**：给定多视角图像，直接用神经网络"看一眼"就猜出材质参数，类似 ImageNet 预训练模型做特征提取
- **细节**：LMRM（基于预训练的 Wan2.1-1.3B 扩散 Transformer）单次前向传播预测特征三平面（triplane）表示。两个轻量级 MLP 解码器共享三平面特征输入，分别输出：
  - **材质解码器** $\mathcal{M}_\phi^{mat}$：预测逐点基础颜色 $\rho_d$ 和神经高光潜变量码 $\ell$
  - **不确定性解码器** $\mathcal{M}_\psi^{unc}$：预测逐材质通道的对数方差（不确定性）

**阶段二：测试时优化（TTO）**

- **直觉**：前馈模型的预测只是"粗调"，需要用渲染损失做"精调"——把材质参数渲染出来，和真实图像比对，反向传播修正参数
- **细节**：通过可微神经材质路径追踪优化三平面参数 $\mathbf{T}$。渲染损失为：

$$\mathcal{L}_{photo} = \mathbb{E}_c[\|\mathcal{T}(\mathbf{I}(\mathbf{T}; c)) - \mathbf{I}_{ref}(c)\|_2^2]$$

其中 $\mathcal{T}$ 为色调映射算子。优化过程中，材质解码器 $\mathcal{M}_\phi^{mat}$ 和神经材质解码器 $\mathcal{D}_{neu}$ 均保持冻结，仅更新三平面。

### 神经材质表示

- **直觉**：把材质想象成一个"黑盒函数"——输入观察角度，输出反射光。传统 PBR 用固定公式（GGX）近似这个函数，神经材质用神经网络学习这个函数，表达能力更强
- **细节**：基于 Yu et al. 的神经材质基底，结合朗伯漫反射和神经高光分量：

$$f(\mathbf{p}, \omega_i, \omega_o) = T_{neu}(\mathbf{p}, \omega_i) \frac{\rho_d(\mathbf{p})}{\pi} + f_{neu}(\mathbf{p}, \omega_i, \omega_o)$$

其中 $f_{neu}$ 和 $T_{neu}$ 由通用解码器 MLP $\mathcal{D}_{neu}$ 从 6D 潜变量码 $\ell(\mathbf{p})$ 解码得到。该表示能表达清漆、内散射、绒毛等复杂效果。

### LMRM 架构

- **直觉**：借鉴扩散模型的强大生成能力，但不需要迭代去噪——只跑一步就出结果，类似 Stable Diffusion 用一步生成图像。三平面是 3D 数据的紧凑表示，三个正交平面编码 3D 空间信息
- **细节**：LMRM 基于预训练的 Wan2.1-1.3B 扩散 Transformer（DiT），重新用作单步模型：
  - VAE 编码器 $\mathcal{E}_{VAE}$ 将输入视角编码为潜变量 $\mathbf{z}^{\mathbf{I}}$
  - Transformer 去噪函数 $\mathcal{F}_\theta$ 单步生成输出潜变量 $\mathbf{z}^{tri}(\theta)$
  - VAE 解码器 $\mathcal{D}_{VAE}$ 解码为三平面特征 $\mathbf{T}_{XY}, \mathbf{T}_{YZ}, \mathbf{T}_{XZ}$

三平面在每个表面点查询，拼接后由两个 MLP 解码：
- 材质 G-buffer：$\mathbf{G}_{mat}(\mathbf{p}) = \mathcal{M}_\phi^{mat}([\mathbf{T}_{XY}(\mathbf{p}), \mathbf{T}_{YZ}(\mathbf{p}), \mathbf{T}_{XZ}(\mathbf{p})])$
- 不确定性 G-buffer：$\mathbf{G}_{unc}(\mathbf{p}) = \mathcal{M}_\psi^{unc}([\mathbf{T}_{XY}(\mathbf{p}), \mathbf{T}_{YZ}(\mathbf{p}), \mathbf{T}_{XZ}(\mathbf{p})])$

### 不确定性引导的材质正则化

![不确定性正则化](https://arxiv.org/html/2606.26715v2/figures/images/unc_reg_v2.png)

**图 4**：不确定性正则化机制。不确定性高的区域允许更大材质漂移，不确定性低的区域强锚定到 LMRM 预测。

- **直觉**：LMRM 对某些区域很确定（如平坦表面），对某些区域不确定（如高光反射处）。优化时应该"相信"确定的区域，让不确定的区域自由调整，否则会把光照错误地烘焙进材质
- **细节**：不确定性正则化项利用 LMRM 预测的不确定性锚定优化：

$$\mathcal{L}_{reg} = \mathbb{E}_p\left[\frac{\|\mathbf{G}_{mat}(\mathbf{T}; p) - \mathbf{G}_{mat}^{LMRM}(p)\|_2^2}{\exp(\mathbf{G}_{unc}^{LMRM}(p))}\right]$$

置信区域（低不确定性）强锚定，抑制材质漂移；不确定区域（高不确定性）弱约束，允许自由调整细节。这有效避免了光照被烘焙进材质的典型问题。

### 为什么需要 TTO

![TTO 的必要性](https://arxiv.org/html/2606.26715v2/figures/images/why_tto_v1.png)

**图 3**：前馈预测给出合理初始材质（a），但 TTO（b）能恢复更精细细节并修正颜色偏移和材质分解错误。

- **直觉**：前馈模型是"通用"的，对特定物体的细节把握不够。TTO 相当于针对这个物体做"个性化微调"，用真实的多视角图像作为监督信号，让材质参数更准确
- **细节**：前馈预测的初始材质已经接近正确，TTO 在此基础上进一步优化，恢复高频细节（如细微纹理）并修正颜色偏移和材质分解错误（如将光照误判为材质属性）

## Training

- **训练目标**：$\mathcal{L}(\theta, \phi, \psi) = \mathcal{L}_{mat} + \lambda_{unc} \mathcal{L}_{unc}$
- **材料损失**：$\mathcal{L}_{mat} = \mathbb{E}[\|\mathbf{G}_{mat}(\theta, \phi) - \mathbf{G}_{mat}^{ref}\|_2^2]$
- **不确定性损失**：基于 $\beta$-NLL 公式（Seitzer et al.），$\beta=0.5$
- **两阶段训练**：先在大规模 PBR 材质数据集（Objaverse、MaterialFusion、TexVerse）预训练，再在神经材质数据集上微调

## Results & Comparisons

NeuMatEx 在合成和真实数据上均优于 PBR 方法：
- **视觉质量**：神经材质能表达清漆、绒毛、内散射等多瓣高光效果，PBR 仅支持单 GGX 叶瓣
- **材质分解**：正确分离光照与材质，避免光照烘焙
- **实时部署**：提取的神经材质可直接在路径追踪渲染器中实时运行（RTX 5090 上约 4ms/帧 @1080p）

## Related Work Analysis

| 方法 | 材质表示 | 输入 | 优势 | 局限 |
|------|---------|------|------|------|
| PBR 逆渲染 (NeuS2, PhysAvatar) | PBR (base color + roughness + metalness) | 多视角图像 | 成熟、可解释 | 单 GGX 叶瓣，无法表达清漆/绒毛/散射 |
| 神经材质烘焙 (Neural BTF) | 神经潜变量 + MLP | 6D BSDF 采样 | 高质量离线烘焙 | 需要密集采样，非从图像提取 |
| 辐射场分解 (NeRF-based) | 隐式表示 | 多视角图像 | 无需显式几何 | 不直接输出材质参数 |
| NeuMatEx (本文) | 神经材质 (triplane + MLP) | 多视角图像 + 网格 | 多瓣高光、实时部署 | 依赖已知几何 |

与 PBR 方法的关键差异：PBR 将材质简化为 3-4 张纹理图，限制了表达能力。NeuMatEx 的神经材质空间能表达清漆、内散射、绒毛等复杂效果，代价是需要神经网络解码。

## Ablations

- **TTO 的影响**：无 TTO 时材质细节丢失、颜色偏移；有 TTO 后恢复高频细节
- **不确定性正则化的影响**：无正则化时优化陷入局部最优，光照被烘焙进材质；有正则化后正确分离

## Limitations

- 依赖已知的 3D 网格几何
- LMRM 训练需要大规模神经材质数据集
- 对高度透明或复杂折射材质的处理仍有局限

## Connections

- [[NeuralMaterials]] — 神经材质表示是本文的核心基础
- [[InverseRendering]] — 可微逆渲染是 TTO 的核心机制
- [[DifferentiablePathTracing]] — 可微路径追踪用于材质优化

## Contradictions

- 与标准 PBR 方法在材质表达能力上存在本质差异：神经材质支持多瓣高光，PBR 仅支持单叶瓣

---
title: "Mobile-GS: Real-time Gaussian Splatting for Mobile Devices"
type: source
tags: [paper, 3dgs, mobile, real-time, compression, order-independent-rendering]
date: 2026-07-31
source_file: raw/papers/Mobile-GS-Real-time-Gaussian-Splatting-for-Mobile-Devices.md
url: https://arxiv.org/abs/2603.11531
venue: "ICLR 2026"
published: 2026
links:
  - https://xiaobiaodu.github.io/mobile-gs-project/
---

## Summary
Mobile-GS 是针对移动设备定制的实时 3D 高斯泼溅方法，在骁龙 8 Gen 3 GPU 上达到 116 FPS 渲染速度。核心创新包括：深度感知无排序渲染（消除排序瓶颈）、一阶梯度球谐蒸馏（降低存储）、神经向量量化（压缩高斯参数）、基于贡献的剪枝（减少高斯数量）。这四种技术组合实现了实时渲染和紧凑模型尺寸，同时保持高质量视觉保真度。

## 原始出处
- 原始文件: [raw/papers/Mobile-GS-Real-time-Gaussian-Splatting-for-Mobile-Devices.md](../../raw/papers/Mobile-GS-Real-time-Gaussian-Splatting-for-Mobile-Devices.md)
- 原文链接: [https://arxiv.org/abs/2603.11531](https://arxiv.org/abs/2603.11531)
- Brief 条目: [brief.md 2026-07-30 > ICLR2026 2603.11531 不排序+codebook量化+球谐降阶+剪枝](../digest/brief.md)

## Key Contributions
- **深度感知无排序渲染**：消除 alpha blending 中的深度排序瓶颈，通过可学习的视角相关权重方案实现无序混合
- **一阶梯度球谐蒸馏**：将三阶球谐（SH）蒸馏为一阶，大幅减少参数量和存储负担
- **神经向量量化**：使用 K-means 分组和轻量级神经解码器压缩 3D 高斯参数
- **基于贡献的剪枝**：根据不透明度和尺度属性剪枝冗余高斯，进一步降低存储成本

## Method

### 整体架构概览
3DGS 在移动端实时渲染面临计算和存储双重瓶颈。传统 alpha blending 需要深度排序，这是主要性能瓶颈（见论文图 2）。Mobile-GS 的核心思路：用深度感知的无排序渲染替代排序依赖的 alpha blending，结合球谐蒸馏、神经向量量化和剪枝技术，实现移动端实时渲染。

### 组件 1：深度感知无排序渲染
- **直觉**：传统 alpha blending 需要按近到远顺序排序高斯体，这个过程计算开销大且难以并行化。通过引入深度感知权重，可以在无序情况下正确混合高斯体，消除排序步骤。
- **细节**：
  - 丢弃依赖排序高斯的原始 alpha blending 范式
  - 提出深度感知权重策略，无序地将所有相关 3D 高斯混合到像素
  - 权重公式：$w_i = \exp(-\sigma_i d_i^{\beta_i})$，其中 $d_i$ 是深度，$\sigma_i$ 和 $\beta_i$ 是可学习参数
  - 渲染公式：$\mathbf{C} = (1-T)\frac{\sum_{i=1}^{\mathcal{N}}\mathbf{c}_i\alpha_i w_i}{\sum_{i=1}^{\mathcal{N}}\alpha_i w_i} + T\mathbf{c}_{bg}$
  - **缺点**：无序混合可能在重叠几何区域引入透明度伪影

### 组件 2：神经视角增强策略
- **直觉**：无排序渲染虽然加速了渲染，但引入了透明度伪影。用神经网络根据 3D 高斯属性和视角校正这些伪影，恢复视角相关效果。
- **细节**：
  - 设计轻量级神经网络，输入为 3D 高斯属性和视角方向
  - 输出视角相关的颜色校正因子
  - 特别改善视角相关效果（如镜面反射）的质量

### 组件 3：一阶梯度球谐蒸馏
- **直觉**：原始 3DGS 使用三阶球谐（SH）表示外观，需要 45 个系数/高斯（RGB 各 15 个）。蒸馏为一阶 SH（6 个系数/高斯）可大幅减少参数量，同时保持基本视角相关效果。
- **细节**：
  - 使用预训练教师模型指导蒸馏过程
  - 学生模型只学习一阶 SH 参数
  - 训练损失：L1 重建损失 + 蒸馏损失（教师与学生输出的一致性）
  - 存储减少：从 45 系数/高斯降到 6 系数/高斯，减少 87%

### 组件 4：神经向量量化
- **直觉**：移动端内存受限，需要对高斯参数进行量化压缩。使用 K-means 聚类 + 神经解码器的方式，在压缩率和重建质量之间取得平衡。
- **细节**：
  - 使用 K-means 对高斯参数分组，生成 codebook
  - 每个高斯只用 codebook 索引表示（节省位数）
  - 轻量级神经解码器从索引重建高斯参数
  - 对蒸馏后的 SH 特征也使用神经解码器压缩

### 组件 5：基于贡献的剪枝
- **直觉**：不透明度低且尺度小的高斯对最终图像贡献微小，可以安全剪枝而不影响视觉质量。
- **细节**：
  - 计算每个高斯的贡献分数：$s_i = \alpha_i \cdot \text{scale}_i$
  - 剪枝贡献分数低于阈值的高斯
  - 训练过程中动态剪枝，逐步减少高斯数量

## Training
- **目标函数**：L1 重建损失 + SSIM 损失 + 蒸馏损失 + 剪枝正则
- **训练策略**：
  - 阶段 1：训练教师模型（原始 3DGS）
  - 阶段 2：蒸馏学生模型（一阶 SH + 无排序渲染）
  - 阶段 3：神经向量量化训练（codebook + 解码器）
  - 阶段 4：剪枝优化
- **数据需求**：多视角 posed 图像，COLMAP 初始化

## Results & Comparisons
- **渲染速度**：骁龙 8 Gen 3 GPU 上 116 FPS
- **模型尺寸**：相比原始 3DGS 减少 90%+ 存储
- **视觉质量**：与原始 3DGS 可比，优于其他轻量级方法
- **对比方法**：Scaffold-GS、Mini-Splatting、SplatFacto、C3DGS

## Related Work Analysis
与轻量级 3DGS 方法相比：
- **Scaffold-GS**：使用层级 scaffold 结构减少高斯数量，但仍依赖排序渲染；Mobile-GS 消除排序瓶颈，更适合移动端
- **Mini-Splatting**：聚焦剪枝和密集化策略，但未解决排序瓶颈；Mobile-GS 同时解决计算和存储问题
- **LocoGS**：使用局部感知策略压缩高斯参数，但推理延迟高；Mobile-GS 的神经向量量化更轻量

## Ablations
论文未提供详细消融实验，但从方法设计可推断关键组件贡献：
- 无无排序渲染 → 排序瓶颈仍存在，无法达到实时
- 无球谐蒸馏 → 存储和计算开销大，移动端无法运行
- 无神经向量量化 → 压缩率低，内存占用高
- 无剪枝 → 高斯数量多，渲染效率低

## Limitations
- 一阶 SH 无法捕捉高频视角相关效果（如锐利镜面反射）
- 神经向量量化的解码器引入额外计算开销
- 剪枝可能导致稀疏区域几何细节丢失
- 在极端视角下可能产生伪影

## 评论与启示
- **不排序 + codebook 量化 + 球谐降阶 + 剪枝** 是移动端 3DGS 压缩的四件套
- **排序是移动端主要瓶颈**：消除排序可以带来数倍加速，比压缩参数更重要
- **神经解码器是压缩的关键**：K-means + 神经解码器比纯量化恢复质量更好
- 评论来源：brief 用户评论

## Connections
- [[3D Gaussian Splatting|3dgs]] — 本文是 3DGS 的移动端优化版本
- [[Spherical Harmonics|spherical-harmonics]] — 使用球谐函数表示视角相关外观
- [[Vector Quantization|vector-quantization]] — 神经向量量化技术压缩高斯参数
- [[Real-time Rendering|real-time-rendering]] — 目标是在移动端实现实时渲染

## Contradictions
- 无明显矛盾

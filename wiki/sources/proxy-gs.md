---
title: "Proxy-GS: Unified Occlusion Priors for Training and Inference in Structured 3D Gaussian Splatting"
type: source
tags: [paper]
date: 2026-07-28
source_file: raw/papers/arxiv-250924421-bd77fe07.md
url: "https://arxiv.org/abs/2509.24421"
venue: ""
published: 2025
links: []
---

## Summary

本文提出 Proxy-GS，一种利用轻量代理网格（proxy mesh）为结构化 [[3DGS]] 引入遮挡感知的统一框架。核心是一个快速代理渲染系统，能在 1ms 内生成 1000×1000 分辨率的精确遮挡深度图。该代理在推理阶段指导 anchor 和 Gaussian 的遮挡剔除，在训练阶段引导 anchor 向表面稠密化，避免遮挡区域产生不一致的 anchor。在 MatrixCity Streets 等高遮挡场景中，Proxy-GS 相比 [[Octree-GS]] 实现超过 2.5 倍加速，同时提升渲染质量。

## 原始出处

- 原始文件: [raw/papers/arxiv-250924421-bd77fe07.md](../../raw/papers/arxiv-250924421-bd77fe07.md)
- 原文链接: [https://arxiv.org/abs/2509.24421](https://arxiv.org/abs/2509.24421)

## Key Contributions

- **代理引导的遮挡过滤（Proxy Guided Filter）**：利用轻量代理网格进行硬件光栅化，结合 [[HiZ]] 层次遮挡剔除和 Early-Z 深度测试，在 ∼1ms 内生成精确深度图。通过 Vulkan-CUDA 零拷贝互操作将深度图直接暴露为 PyTorch tensor，避免 GPU-CPU 往返开销
- **代理引导的稠密化（Proxy-Guided Densification）**：在训练阶段利用代理深度图识别高误差区域，将新 anchor 投影到代理网格表面，避免在遮挡区域产生冗余 anchor
- **与消费级 GPU 硬件光栅化无缝集成**：通过 Vulkan API 利用 GPU 固定功能单元进行深度生成，适配 RTX 4090 等消费级显卡
- **在 MatrixCity 等高度遮挡场景中实现 >2.5× 加速**，同时保持或提升 PSNR/SSIM/LPIPS 指标
- **anchor 数量大幅减少**：在 MatrixCity 上从 800-1040k（Octree-GS）降至 80-190k（Proxy-GS），降低约 80-90% 的 decoding 负担

## Method

### 整体思路

Proxy-GS 的核心观察是：在 3DGS 的 MLP 变体中，大量 anchor 分布在被遮挡区域，这些 anchor 解码出的 Gaussian 永远不会被实际看到，却仍消耗 decoding 和光栅化资源。传统 LOD 技术仅按距离粗略减少细节，无法感知遮挡关系。

本文的解决方案是：从场景重建的粗略网格出发，构建一个轻量代理网格，通过 [[HiZ]]（层次 Z 缓冲）快速计算每帧每个 cluster 的可见性。在推理时剔除被遮挡的 anchor；在训练时将被遮挡区域的 anchor 生长引导到代理表面，使 anchor 分布更符合真实几何结构。

![Proxy-GS 管线概览](images/proxy-gs/fig2.png)

**图 2**：Proxy-GS 整体流程：原始场景→重建网格→QEM 简化→cluster 划分→Vulkan 深度渲染→遮挡剔除→anchor 过滤/稠密化→最终渲染

### 代理引导的遮挡过滤（Proxy Guided Filter）

#### 代理网格构建

对于室外大规模场景，使用 COLMAP 生成的密集点云重建网格；对于室内无纹理区域，使用 [[MapAnything]] 等大重建模型生成密集点云后转换为网格。无论哪种来源，都经过进一步简化。

#### QEM 边缘折叠简化

对每个顶点 v，以其入射面的平面方程累积二次型 Qv：

$$Q_v = \sum_{f \in N(v)} \mathbf{p}_f \mathbf{p}_f^{\top}$$

折叠边 (i,j) 时合并二次型 Q' = Qi + Qj，最小化误差 E(x̅) = x̅^T Q' x̅ 得到最优收缩位置。维护一个按代价排序的优先级队列，迭代折叠最低代价边。禁止破坏流形或翻转三角形朝向的折叠。

#### 边界/特征保持

对边界或尖锐折痕边，通过添加两个约束平面增强顶点二次型：法向约束平面和切向约束平面，以权重 λb 增强，防止边界在简化过程中塌陷。

#### Cluster 构建

将简化网格划分为三角形集合 {Lk}，每个 cluster 预计算：(a) 对象空间 AABB（轴对齐包围盒）; (b) 保守屏幕空间包围矩形 Rk⁽⁰⁾（level-0），通过投影 AABB 的 8 个角点并取外向包围盒得到。

#### 帧级可见性：Frustum 和 Hi-Z 遮挡剔除

每个帧对每个 cluster 执行两级可见性检查：
1. **视锥剔除（Frustum culling）**：用 6 个视锥平面（法向向内）检查 AABB，完全在任一平面外的 cluster 直接丢弃
2. **[[HiZ]] 遮挡剔除**：构建层次 Z 金字塔，对每个 cluster 选择合适层级 ℓ，向外取整屏幕矩形后查 HiZ map 做深度比较。若 cluster 的保守近深度 ≥ HiZ 中的最大深度，则该 cluster 被判定为遮挡

#### 深度专用 Pass 与 Early-Z

可见的 cluster 通过一个纯深度管线（禁用颜色写入、启用深度写入）渲染，使用最小 fragment shader 以利用 Early-Z 硬件加速。

#### Vulkan-CUDA 零拷贝互操作

深度图像的内存通过 Vulkan 导出为外部文件描述符（FD），CUDA 端导入该 FD 为外部内存并映射到设备指针，最后包装为 PyTorch CUDA tensor，完全避免 GPU-CPU 数据往返。

#### Anchor 级别的遮挡过滤

将代理深度图与 frustum 剔除融合到一个 CUDA kernel 中：
- 将 anchor 的 3D 坐标投影到 NDC
- 映射到像素坐标 (u,v)
- 检查 anchor 深度 vs 代理深度图：若 anchor 深度 > 代理深度 + γ（安全裕度），则视为被遮挡
- 安全裕度 γ=0.3 在质量/速度间取得最佳平衡

### 代理引导的稠密化（Proxy-Guided Densification）

原始 anchor 生长策略仅根据梯度大小决定是否在 Gaussian 周围生成新 anchor，忽略了遮挡关系：被遮挡的 Gaussian 即使梯度大，其新 anchor 也永远不会被解码看到。

Proxy-GS 的改进：
1. 利用预计算的代理深度图，计算每个 patch 的 L1 损失
2. 识别异常高损失的 patch（loss > 3 × 平均损失）
3. 将这些 patch 中的新 anchor 投影到代理网格表面，确保 anchor 在可见几何附近生长
4. 避免了在不可见区域浪费 anchor，同时改善了可见区域的几何覆盖

## Training

基于 [[Octree-GS]] 的默认初始化和 LOD 策略构建。

**训练过程消融（Table 3, Block 5）：**

| ID | 遮挡训练 | 代理稠密化 | 代理推理 | PSNR↑ | FPS↑ | 平均 anchor |
|---|---|---|---|---|---|---|
| 1 | ✗ | ✗ | ✗ | 21.41 | 48 | 719k |
| 2 | ✗ | ✗ | ✓ | 19.06 | 165 | 82k |
| 3 | ✓ | ✗ | ✓ | 21.50 | 147 | 93k |
| 4 | ✓ | ✓ | ✓ | 21.68 | 143 | 106k |

ID 1 为 Octree-GS 基线。仅推理时使用代理遮挡（ID 2）带来 3× FPS 提升但质量下降。加入训练时遮挡（ID 3）恢复并超过基线质量。再加入代理稠密化（ID 4）取得最佳平衡。

所有实验在 NVIDIA A100-40GB 上训练 40k 迭代，在 RTX 4090 上测试推理速度。

## Results & Comparisons

### MatrixCity 数据集（Table 1）

| 方法 | Block 1&2 PSNR↑ | Block 1&2 FPS↑ | Block 5 PSNR↑ | Block 5 FPS↑ |
|---|---|---|---|---|
| [[3DGS]] | 21.55 | 115 | 20.70 | 121 |
| [[Scaffold-GS]] | 21.44 | 81 | 20.56 | 71 |
| [[Octree-GS]] | 21.94 | 32 | 21.41 | 48 |
| **Proxy-GS** | **22.11** | **126** | **21.68** | **151** |

Proxy-GS 在所有 Block 上取得最佳 PSNR（22.11 / 21.06 / 21.68）和最高 FPS（126 / 134 / 151），相比 Octree-GS 实现 2-3× 速度提升。

### 真实场景（Table 2）

| 方法 | Small City PSNR↑ | Small City FPS↑ | Berlin PSNR↑ | Berlin FPS↑ | CUHK-LOWER PSNR↑ | CUHK-LOWER FPS↑ |
|---|---|---|---|---|---|---|
| [[Octree-GS]] | 23.03 | 51 | 27.83 | 263 | 26.42 | 212 |
| **Proxy-GS** | **23.09** | **139** | **27.85** | **275** | **26.44** | **239** |

在 Small City 等高遮挡街景中，Proxy-GS 实现 2.73× FPS 提升。在 Berlin 和 CUHK-LOWER 等低遮挡场景中也有稳定改进。

![定性对比](images/proxy-gs/fig4.png)

**图 4**：不同数据集上的定性对比，红色框标记差异显著区域。Proxy-GS 更好地保留了建筑物窗户、人行横道等细节。

### 与不同渲染加速方法的集成（Table 4）

| 方法 | PSNR↑ | FPS↑ |
|---|---|---|
| Proxy-GS + 原始渲染器 | 23.27 | 112 |
| + FlashGS | 23.27 | 115 |
| + Hardware 3DGS | 23.20 | 155 |

Proxy-GS 可与 [[FlashGS]]、[[Hardware 3DGS]] 等现有加速技术无缝组合，在略微牺牲质量的情况下获得更高帧率。

## Related Work Analysis

### 与 [[NeRF]] 系列的关系

NeRF 系列（Mip-NeRF、NeRF++、Mip-NeRF 360）实现了高质量的新视角合成，但密集射线采样的计算开销使其难以实时运行。[[3DGS]] 以显式 Gaussian 基元替代隐式场，实现了实时性能，但 MLP 变体引入的新 decoding 开销在大规模场景中成为新瓶颈。

### 与 pruning/LOD 策略的关系

现有方法（[[Scaffold-GS]]、[[Octree-GS]]）通过结构化 anchor 和 LOD 来减少 Gaussian 数量，但它们仅基于相机距离选择 LOD 层级，不考虑遮挡关系。Proxy-GS 首次将遮挡感知引入 anchor 选择过程，可叠加于上述方法之上。

### 与传统图形学遮挡剔除的关系

[[HiZ]]（层次 Z 缓冲）是 1990 年代提出的经典遮挡剔除算法，在传统游戏引擎中广泛应用。Proxy-GS 将其引入 3DGS pipeline，并通过 Vulkan-CUDA 零拷贝互操作实现无缝集成。与 nvdiffrast、预训练 3DGS 深度等替代方案相比，代理深度渲染速度更快（151 FPS vs 32/54 FPS）。

## Ablations

### 代理精度依赖性（Fig. 6）

Proxy-GS 对代理网格分辨率不敏感——从精细（108MB）到粗略（824KB）的网格，渲染质量几乎不变。这是因为城市建筑场景以近平面表面为主，粗略网格仍能保持正确的遮挡结构。

对顶点噪声更敏感：噪声 > 5% 会破坏遮挡边界的全局几何结构，导致清晰度下降。但 < 5% 的小噪声影响有限，因为 anchor 与解码 Gaussian 之间存在固有偏移。

![网格分辨率与顶点噪声消融](images/proxy-gs/fig5.png)

**图 5**：代理网格分辨率可视化。从精细到粗略的简化过程中，遮挡结构保持完整。

### 安全裕度 γ（Table 10, Fig. 7）

| γ | PSNR↑ | FPS↑ |
|---|---|---|
| 0.1 | 22.94 | 142 |
| **0.3** | **23.09** | **139** |
| 0.6 | 23.02 | 135 |
| 1.0 | 23.05 | 128 |

γ=0.3 在渲染质量和速度间取得最佳平衡。γ 过小导致近距离区域伪影，γ 过大引入过多 anchor 降低 FPS。

![安全裕度可视化](images/proxy-gs/fig7.png)

**图 7**：不同安全裕度的可视化对比。

### 平均 anchor 数（Table 9）

| 数据集 | Proxy-GS | Octree-GS | 减少比例 |
|---|---|---|---|
| MatrixCity Block 1&2 | 190k | 800k | 76% |
| MatrixCity Block 3&4 | 190k | 1040k | 82% |
| MatrixCity Block 5 | 80k | 720k | 89% |
| Small City | 350k | 840k | 58% |

Proxy-GS 在所有数据集中一致减少 decoding anchor 数量，高遮挡场景效果更显著。

![顶点噪声可视化](images/proxy-gs/fig8.png)

**图 8**：不同级别顶点噪声对渲染质量的影响。

## Limitations

- **依赖网格重建质量**：代理网格的构建依赖于 COLMAP 或大重建模型（如 MapAnything）的输出，在极端无纹理或运动模糊场景中网格可能不完整
- **低遮挡场景收益有限**：在 aerial 视图等几乎无遮挡的场景中，Proxy-GS 的加速和提质效果较弱
- **额外预处理步骤**：需要网格重建→QEM 简化→cluster 划分的预处理流水线，增加部署复杂度
- **安全裕度需要调参**：γ 值的选取在不同场景间有轻微变化，虽然 γ=0.3 在多数场景表现良好但不是通用最优解
- **无法处理动态遮挡**：代理网格为静态场景构建，无法处理运动物体的动态遮挡关系

## Connections

- [[3DGS]] — Proxy-GS 构建于 MLP 变体 3DGS 之上，通过遮挡感知进一步减少冗余 anchor
- [[Octree-GS]] — 本文的基线方法，Proxy-GS 在其 LOD 结构之上叠加遮挡剔除
- [[Scaffold-GS]] — 结构化 anchor 方法的代表，Proxy-GS 的遮挡过滤可直接集成
- [[HiZ]] — 层次 Z 缓冲，Proxy-GS 的核心可见性判断算法
- [[NeRF]] — 神经辐射场家族，Proxy-GS 代理深度获取的对比基线之一
- [[FlashGS]] / [[Hardware 3DGS]] — 3DGS 渲染加速方法，Proxy-GS 可与之组合使用
- [[MapAnything]] — 用于室内场景密集点云生成的大重建模型

## Contradictions

- 与 [[Octree-GS]] 在渲染质量上的对比：Octree-GS 在低遮挡场景（Berlin）中 PSNR 非常接近（27.83 vs 27.85），但在高遮挡场景中 Proxy-GS 显著领先（FPS 32→126），体现了遮挡感知策略对遮挡密集型场景的重要性
- 与 pruning 策略的关系：pruning 方法在减少 Gaussian 数量时必然导致质量下降，而 Proxy-GS 的遮挡剔除在减少 80-90% anchor 的同时还能提升质量，说明遮挡引起的不是简单的参数冗余而是结构性问题
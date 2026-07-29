---
title: "A LoD of Gaussians: Unified Training and Rendering for Ultra-Large Scale Reconstruction with External Memory"
type: source
tags: [paper, gaussian-splatting, level-of-detail, large-scale-reconstruction, external-memory, hierarchical-spt, out-of-core-training]
date: 2026-07-29
source_file: raw/digest/sources/2026-07-29/arxiv-250701110-d74ea026.md
url: "https://arxiv.org/abs/2507.01110"
venue: "SIGGRAPH 2026"
published: 2026
links: []
---

## Summary

A LoD of Gaussians 提出了一种**无需分块**的超大尺度 3D Gaussian Splatting 训练与渲染框架：将所有高斯体存储在 CPU 内存（外部存储）中，通过动态按需流式传输减少显存压力，并在消费级 GPU（<=24 GB VRAM）上实现 6000 万+ 高斯体的实时渲染与训练。核心创新包括：(1) 结合高斯层级树与 Sequential Point Tree 的 **Hierarchical SPT (HSPT)** 数据结构，实现高效、并行化的 LoD 切割；(2) 基于 MCMC 风格的新增策略的**层级稠密化**方法，支持训练期间层级结构动态扩展；(3) GPU 缓存与视图调度系统，利用时序一致性最小化 CPU-GPU 数据传输开销。该方法在 MatrixCity-Scale 数据集上以 4000 万高斯体达到 PSNR 21.73，渲染仅需 8 GB 显存，训练时间仅 15 小时（对比 Hierarchical 3DGS 的 4.23 百万步和近 4 天）。

## 原始出处

- 原始文件: [arxiv-250701110-d74ea026.md](../../raw/digest/sources/2026-07-29/arxiv-250701110-d74ea026.md)
- 原文链接: [https://arxiv.org/abs/2507.01110](https://arxiv.org/abs/2507.01110)
- Brief 条目: [brief.md 2026-07-29 > A LoD of Gaussians: Out-of-Core Training and Rendering for Seamless Ultra-Large Scene Reconstruction](../../raw/digest/brief.md)

## Key Contributions

- **无需分块的超大尺度训练与渲染**：首次实现单张消费级 GPU（<=24 GB VRAM）上对城市级高斯场景（6000 万+高斯体）的端到端训练与交互式渲染，无需场景分块
- **层级 SPT (HSPT) 数据结构**：结合高斯层级树的 BFS 视锥剔除能力和 SPT 的并行二分查找，两步切割实现高效 LoD 选择
- **层级稠密化策略**：借鉴 3DGS-MCMC 的 spawn 机制，在训练期间稳定扩展和重平衡高斯层级树，避免破坏性重置
- **GPU 缓存与视图调度系统**：以 SPT 为单位缓存切割结果，结合 KNN 近邻视图选择，最大化高斯体复用率

## Method

![A LoD of Gaussians 总览](https://arxiv.org/html/2507.01110v4/extracted/6587698/imgs/Teaser.png)
*图 1：无需分块的完整层级 3D 高斯表示，支持从航拍到街景的多尺度无缝重建。混合 LoD 系统实现动态、视图相关的高斯流式传输*

![方法总览：训练迭代与稠密化步骤](https://arxiv.org/html/2507.01110v4/extracted/6587698/imgs/VisualAbstract.png)
*图 7：单次训练迭代（步骤 1-8）和稠密化步骤（A-D）的方法总览*

![SPT 与高斯层级对比](https://arxiv.org/html/2507.01110v4/extracted/6587698/imgs/Hierarchy_SPT.png)
*图 2：Sequential Point Tree 和高斯层级树在 9 个高斯体上的 LoD 切割对比*

![层级 SPT 转换](https://arxiv.org/html/2507.01110v4/extracted/6587698/imgs/Hierarchical_SPT.png)
*图 4：高斯层级树通过按体积切割并转换子树为 SPT 形成 HSPT*

![缓存策略](https://arxiv.org/html/2507.01110v4/extracted/6587698/imgs/Caching.png)
*图 5：缓存策略总览。高斯体从上层树、新加载的 SPT 切割和缓存命中三个来源组装*

![内存布局](https://arxiv.org/html/2507.01110v4/extracted/6587698/imgs/MemLayout.png)
*图 6：BigCity-Scale 6000 万高斯体单次训练迭代的 CPU/GPU 峰值内存消耗*

### 整体架构概览

现有方法对大场景的解决方案是**分块训练**——将场景切分成小块，各自独立训练后再合并。这种方法有三个根本缺陷：(1) **相机-分块不对齐**：相机视角常跨越多个分块，边界任意难定义；(2) **冗余重叠**：避免边界伪影需要大量重叠区域，增加内存和训练时间；(3) **非对称硬件需求**：渲染时可能需要同时加载所有可见分块，超出训练硬件能力。

A LoD of Gaussians 的核心思路：**完全避免分块**。将全部高斯体存储在 CPU RAM（外部存储）中，每次训练只按需加载当前视角可见的高斯体到 GPU。通过 LoD 层级确保远处视角只加载粗糙表示，近处才加载精细细节，从而将显存占用控制在消费级 GPU 范围内。

整个流程分三步：
1. **初始化**：从稀疏点云初始化少量高斯体，在 GPU 上训练 10 万步建立全局结构
2. **构建层级**：将训练好的高斯体构建为二进制层级树，进入外部存储训练循环
3. **训练循环**：按需从 CPU RAM 加载 SPT 切割 -> GPU 训练 -> CPU 稠密化 -> 重建 HSPT -> 重复

### 外部存储训练

标准 3DGS 将全部高斯体属性、训练图像和优化器状态存储在 GPU VRAM 中。每个高斯体约需 ~800 字节，限制了约 50 万高斯体/GB 显存。A LoD of Gaussians 将所有高斯体数据存储在 CPU RAM 中，每次训练迭代按需流式传输到 GPU。

**内存占用**：每个高斯体约 1 GB RAM / 百万高斯体。层级结构本身仅占总 RAM 的不到 10%，大部分 RAM 消耗在每高斯属性及其对应的 Adam 优化器状态。

### 4.1 初始化

遵循 Hierarchical 3DGS 的做法，从稀疏点云初始化高斯模型（含天球点）。初始表示足够小，可完全驻留 GPU 内存，在禁用稠密化的情况下训练 100,000 步。此阶段的目标是建立稳定的全局场景结构，为层级构建做准备。之后构建二进制高斯层级树，以训练好的高斯体为叶子节点，父节点为其子节点的合并近似。

### 4.2 梯度传播

遵循标准 3DGS 误差传播方式更新高斯体属性（基础色、SH 系数、位置、协方差）。但只在当前训练视角选择的切割集合上操作，因此梯度可能传播到层级中间的高斯体。

### 4.3 层级稠密化

稠密化 LoD 表示的核心挑战：层级结构必须在训练期间持续演化。prior 方法通过仅在分块训练和稠密化完成后构建 LoD 层级来规避此问题。

借鉴 3DGS-MCMC 的 MCMC 风格 spawn 机制：按不透明度概率选择高斯体"分裂"，替换为两个新高斯体。作者将此方法适配为层级结构——对叶子节点**spawn**两个新子节点，而非分裂单个高斯体，以最小化伪影增加层级大小。

对于死亡叶子节点（不透明度低于阈值），其父节点被兄弟节点替代；死亡叶子节点和父节点被 respawn 到另一个被选为稠密化的节点的子节点。两种操作确保层级可以在训练中稳定扩展和按需重平衡。避免破坏性重置在外部存储设置中尤为重要，因为许多高斯体在恢复不透明度后将不再符合层级结构。

![层级稠密化示例](https://arxiv.org/html/2507.01110v4/extracted/6587698/imgs/Densification.png)
*图 3：叶子节点稠密化和 respawn 的示例*

### 4.4 层级 SPT 数据结构 (HSPT)

#### 背景：高斯层级与 SPT

**高斯层级树**（Hierarchical 3DGS 使用）：通过 BFS 评估切割条件 ||mu_i - p_cam||_2 >= m_d(i)，保证 proper cut，但 GPU 并行效率极差。

**Sequential Point Tree (SPT)**：切割条件 m_d(parent(i)) > ||mu_root - p_cam||_2 >= m_d(i)，所有高斯体可并行评估，只需存储排序的 (m_d(i), m_d(parent(i))) 对。通过二分查找确定 cutoff 索引。缺陷：同一 SPT 内所有高斯体共享相同 LoD，由相机到根节点的距离决定。对于城市级分布散乱的高斯体，离根远的区域实际离相机可能很近，却被迫用太粗糙的细节。

**保守最小距离**：为弥补 SPT 的缺陷，定义 M_d(i) = m_d(i) + ||mu_i - p_cam||_2，利用三角不等式保证正确切割。

#### HSPT：两步切割

HSPT 的核心思想：**BFS 负责视锥剔除，SPT 负责 LoD 选择，各管各的**。

构造方式：通过 BFS 按节点体积切割层级树，s_i^1 * s_i^2 * s_i^3 < size。切割集合将层级分为两部分：
- **上层**：体积大于 size 的高斯体（少量节点，约几百个），用 BFS 遍历做视锥剔除
- **下层**：以切割节点为根的紧密子树，每个子树体积上限约束，保证 SPT 假设成立，转换为 SPT

切割过程两步走：
1. 对上层 BFS 遍历，选择需要的节点和 SPT 子树（同时做视锥剔除）
2. 对每个选中的 SPT 按相机到其根的距离做二分查找，确定该 SPT 内的 LoD

上层 BFS 保证 proper cut 和早期剔除（视锥外子树直接不加载），下层 SPT 提供高效的并行 LoD 选择。

**最小距离度量改进**：由于 HSPT 不需每步重建，可使用更精确但更昂贵的最小距离度量：
m_d'(i) = T / sqrt(s_i^1 * s_i^2 + s_i^1 * s_i^3 + s_i^2 * s_i^3)
即高斯椭球表面积的倒数平方根，更好地捕获各向异性高斯的感知大小。

**重建频率**：实践中只在每次稠密化后重建 HSPT，利用 m_d 在优化中缓慢演化的事实。

#### 视锥剔除

对 BFS 中考虑的每个节点做视锥剔除：检查以高斯体为中心、半径为 (3 * max_j s_i^j) * sqrt(3) 的球是否与视锥相交。使用高斯尺度作为整棵子树范围的代理，实践中与完整边界球层级对比无显著差异。早期剔除显著减少需要从 RAM 加载的高斯体数量。

### 4.5 GPU 缓存

以 SPT 为单位缓存切割结果，而非缓存单个高斯体。每条缓存条目存储：某个 SPT 在特定相机距离下的切割结果，以及缓存的距离 d_bar_j。

缓存命中检查使用距离比例容差：D_min <= d_j / d_bar_j <= D_max。如果满足条件，直接复用缓存的 SPT 切割，避免昂贵的 RAM 到 GPU 传输。

**LRU 写回策略**：当显存超过阈值时，条目写回 RAM。每 1000 步清空整个缓存以防过拟合。

**视图选择**：预计算所有训练视图位置的 k-NN 图，选择地理上接近的后续训练视图以提高缓存命中率。按分布 P(j|i) proportional 1/(w_ij + W) 采样，每 12 次迭代注入随机视图以保留泛化能力。

![连续 LoD 过渡](https://arxiv.org/html/2507.01110v4/extracted/6587698/imgs/continuous_LOD.jpg)
*图 10：层级 SPT 实现精细（左）和粗糙（右）表示之间的平滑过渡*

![视锥剔除效果](https://arxiv.org/html/2507.01110v4/extracted/6587698/imgs/Frustum4.png)
*图 9：视锥剔除和 LoD 选择大幅减少渲染所需的高斯体数量*

### 4.6 内存布局

MatrixCity-Scale 6000 万高斯体单次训练迭代的内存消耗：
- **CPU RAM**：每高斯体约 1 GB/百万，层级结构不到 10%
- **GPU VRAM**：所有 SPT 元数据仅 680 MB，上层层级仅 24 MB
- 宽角度航拍视图中仅加载场景子集：220 万高斯体直接渲染，240 万保留在缓存中

## Training

- **优化器**：Adam
- **训练流程**：
  1. 初始化阶段：100,000 步，无稠密化，在 GPU 上建立全局结构
  2. 层级构建后：外部存储训练循环
  3. HSPT 重建：每次稠密化后重建
- **稠密化**：MCMC 风格 spawn（叶子节点 spawn 两个子节点）+ 死亡 respawn 策略
- **视图调度**：KNN 近邻视图选择 + 每 12 步注入随机视图
- **缓存刷新**：每 1000 步清空 GPU 缓存
- **训练时间**：MC-Scale 250,000 步，约 15 小时（对比 Hierarchical 3DGS 的 4.23 百万步、近 4 天）
- **硬件**：RTX 3090（消费级 GPU）
- **SH 度**：1（大场景下减少显存）

## Results & Comparisons

### MatrixCity-Scale（1.5 万张图像）

| 方法 | PSNR↑ | SSIM↑ | LPIPS↓ | 高斯体数 |
|------|-------|-------|--------|---------|
| **Ours (60M)** | **21.73** | **0.712** | **0.213** | 60M |
| Ours* (40M) | 20.63 | 0.668 | 0.282 | 40M |
| Hierarchical*,‡ | 13.77 | 0.519 | 0.559 | 82M |
| 3DGS-MCMC | 13.16 | 0.448 | 0.586 | 6M |

### Campus 数据集（2.2 万张图像）

| 方法 | PSNR↑ | SSIM↑ | LPIPS↓ | 高斯体数 |
|------|-------|-------|--------|---------|
| **Ours (80M)** | **22.86** | **0.725** | **0.237** | 80M |
| Ours (38M) | 22.83 | 0.713 | 0.248 | 38M |
| Hierarchical*,‡ | 17.76 | 0.601 | 0.424 | 80M |
| Hierarchical single† | 24.61 | 0.807 | 0.331 | - |
| 3DGS-MCMC | 15.11 | 0.600 | 0.580 | 6M |

### 性能对比

| 场景 | 渲染全帧 | 无缓存渲染 | 训练全帧 | HSPT 切割 | BFS 切割 |
|------|---------|-----------|---------|----------|---------|
| MC-Scale (38M) | 48.1 ms | 119.4 ms | 156 ms | 31.9 ms | 47.8 ms |
| MC-Scale (80M) | 47.1 ms | 92.6 ms | 205 ms | 31.3 ms | 40.0 ms |
| Campus (80M) | 83.2 ms | 222.3 ms | - | 36.5 ms | 53.7 ms |

### 关键发现

- **质量**：Ours 在两个数据集上均显著优于 Hierarchical 3DGS（MC-Scale PSNR 高 8 分，Campus 高 5 分）
- **显存**：仅需 8 GB VRAM（MC-Scale）和 16 GB（Campus 80M），可在消费级 GPU 上交互式 flythrough
- **训练效率**：250,000 步 / 15 小时 vs Hierarchical 3DGS 的 4.23 百万步 / 近 4 天
- **分块伪影**：Hierarchical 3DGS 的分块合并引入"floaters"（孤立高斯体），严重遮挡测试视角

### 消融实验

| 配置 | MC-Scale 渲染帧时 | Campus 训练迭代时 |
|------|------------------|------------------|
| 完整管线 | 48.1 ms / 156 ms | 47.1 ms / 205 ms |
| 无缓存 | 119.4 ms / 471 ms | 92.6 ms / 244 ms |
| 无视锥剔除 | 52.3 ms / 685 ms | 38.3 ms / 312 ms |
| 无视图选择 | 355K RAM加载/frame | 219K RAM/frame（-35%） |

- **缓存**：显著提升性能，渲染帧率翻倍，训练迭代时间减少约 3 倍
- **视锥剔除**：对大场景模型特别有益，大幅减少每视图加载和处理的 RAM 高斯体数量
- **视图选择**：减少 35% 的 RAM 加载量，重建质量不受影响（PSNR 和 SSIM 略有提升）

## Related Work Analysis

### 与 Hierarchical 3DGS 的关系
Hierarchical 3DGS 通过分块训练+合并构建全局 LoD 层级，是本文最直接的对比方法。两者都使用高斯层级和 LoD 机制，但关键差异：(1) Hierarchical 3DGS 分块训练后构建层级，本文在训练期间动态维护层级；(2) Hierarchical 3DGS 假设 80 GB GPU，本文仅需 24 GB；(3) Hierarchical 3DGS 的分块合并引入 floaters 伪影，本文无此问题。

### 与 CityGaussian / VastGaussian / Horizon-GS 的关系
这些方法均采用分块策略处理大场景。CityGaussian 结合分块训练与每块 LoD 选择（使用 LightGaussian）；VastGaussian 引入解耦外观建模和渐进式分块；Horizon-GS 针对混合航拍/街景数据集。本文的无分块方法从根本上避免了分块边界伪影和视图-分块不对齐问题。

### 与 3DGS-MCMC 的关系
3DGS-MCMC 提出 MCMC 风格的稠密化（分裂和 despawn），本文借鉴其 spawn 机制并适配为层级稠密化。3DGS-MCMC 在大规模场景下受限于聚合性不透明度和尺度基剪枝，大量高斯体完全消失。

### 与 Scaffold-GS / Octree-GS 的关系
Scaffold-GS 引入锚定参考高斯点的学习特征向量，由 MLP 在渲染时生成关联高斯体；Octree-GS 通过空间细分实现层级 LoD 渲染。两者均为渲染时 LoD 控制设计，而本文的 LoD 是在训练期间直接构建和维护的。

### 与 LightGaussian / CompgS 等压缩方法的关系
压缩技术主要减少高斯体数量或每原语存储量，大多后处理应用或修改稠密化策略。本文方法与压缩技术正交，可结合使用以进一步降低内存和性能开销。

## Ablations

### 缓存消融
移除缓存后，渲染帧时从 48.1 ms 增至 119.4 ms（MC-Scale），训练迭代从 156 ms 增至 471 ms。缓存将性能提升约 2-3 倍。

### 视锥剔除消融
移除视锥剔除后，训练迭代时间从 156 ms 暴增至 685 ms（MC-Scale），因大量不必要的高斯体从 RAM 加载。MC-Scale 渲染帧时略有增加（48.1 → 52.3 ms）。

### HSPT 切割 vs BFS 切割
HSPT 切割始终快于传统 BFS 切割：MC-Scale 31.9 ms vs 47.8 ms，Campus 36.5 ms vs 53.7 ms。

### 视图选择消融
启用视图选择后，MC-Scale 每帧从 RAM 加载的高斯体从 355K 降至 219K（-35%），PSNR 和 SSIM 分别提升 0.04 和 0.05。

### 模型规模
MC-Scale 上 40M 高斯体 PSNR 20.63，60M 提升到 21.73。150M 高斯体训练成功但质量提升微弱，作者认为需要更多训练视图才能充分利用。

## Limitations

- **初始化挑战**：大规模场景下准确的相机位姿估计和稀疏点云重建仍然困难，尤其是对覆盖稀疏或不一致的真实世界数据集
- **RAM 占用**：约 1 GB RAM / 百万高斯体，虽然比 prior 方法更高效，但仍限制可扩展性。从磁盘加载可行，但会导致 10 倍减速
- **大规模高斯体收益递减**：150M 高斯体训练成功但质量提升微弱，可能需要更多训练视图
- **视锥剔除的局限**：当整个场景都在视锥内时无效，遮挡剔除可跳过整个 SPT 进一步提升
- **缓存引起的 LoD 随机性**：缓存命中导致 LoD 可能依赖缓存状态而非严格最优，虽略微影响渲染质量但反而提升训练鲁棒性
- **未开源代码和模型**

## 评论与启示

- **外部存储 + LoD = 消费级 GPU 城市级重建**：将全部高斯体放在 CPU RAM 中按需流式传输，是 3DGS 从场景级扩展到城市级的根本性范式转变。不再需要分块及其所有伪影
- **HSPT 是 BFS + SPT 的巧妙组合**：BFS 负责粗粒度的视锥剔除和 proper cut 保证，SPT 负责细粒度的并行 LoD 选择。两者各取所长、互补短板，是工程中非常优雅的分工设计
- **MCMC spawn 适配层级稠密化**：借鉴 3DGS-MCMC 的 spawn 机制解决层级训练期间结构演化问题，避免了破坏性重置，是训练期间维护层级结构的关键洞察
- **缓存引起的 LoD 随机性意外有益**：虽然缓存命中导致 LoD 可能不是严格最优，但这种随机性反而防止过拟合到固定相机距离，促进了跨尺度的更好泛化
- 与 [[3DGS]]：本文建立在标准 3DGS 基础上，解决其显存限制
- 与 [[Hierarchical 3DGS]]：同为层级 LoD，但无分块、更低显存、更高训练效率
- 与 [[3DGS-MCMC]]：借鉴其 spawn 机制，适配为层级稠密化
- 与 [[CityGaussian]]：同为城市级重建，但 CityGaussian 分块训练，本文端到端无分块

## Connections

- [[3DGS]] — 基础方法，本文扩展其到城市级尺度
- [[Hierarchical 3DGS]] — 最直接的对比方法，同为层级 LoD 但分块训练
- [[3DGS-MCMC]] — 借鉴 spawn 机制用于层级稠密化
- [[CityGaussian]] — 同为城市级 3DGS，分块训练 + 每块 LoD
- [[VastGaussian]] — 分块训练 + 解耦外观建模
- [[Horizon-GS]] — 混合航拍/街景数据集的 divide-and-conquer 方法
- [[Scaffold-GS]] — 锚定参考高斯的 LoD 渲染
- [[Octree-GS]] — 空间细分的层级 LoD 渲染
- [[LightGaussian]] — 3DGS 压缩方法，与本文正交

## Contradictions

- 与 [[Hierarchical 3DGS]] 的分块哲学相反：本文证明端到端无分块训练不仅可行，且质量更高、显存更低、训练更快
- 与 3DGS-MCMC 的 despawn 策略相反：本文避免 despawn（破坏性重置），采用 respawn 到不同节点的策略保持层级结构稳定性
- 与标准 SPT 的单一 LoD 假设相反：HSPT 通过上下层分离，使 SPT 仅在体积受限的紧密子树内使用，保证了 SPT 假设成立

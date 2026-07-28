---
title: "TopoMesh: High-Fidelity Mesh Autoencoding via Topological Unification"
type: source
tags: [paper]
date: 2026-07-28
source_file: raw/papers/TopoMesh-High-Fidelity-Mesh-Autoencoding-via-Topological-Unification.md
url: "https://arxiv.org/abs/2603.24278"
venue: "CVPR 2026"
published: 2026
links: ["https://logan0601.github.io/projects/topomesh/index.html"]
---

## Summary

TopoMesh 提出**拓扑统一**（Topological Unification）范式，通过 [[Dual Marching Cubes]]（DMC）框架让 GT 网格和 VAE 预测网格共享相同拓扑结构，首次实现顶点/面层级的显式对应和直接监督。核心包含 Topo-Remesh 重网格化算法（L∞ 距离度量，1024³ 分辨率约 15 秒）和 Topo-VAE 稀疏体素 VAE（稀疏体素-点交叉注意力编码器 + 拓扑/几何解耦解码器）。在锐边 F1 上提升超 8%，Chamfer Distance 降低超 30%，为 [[3DGS]] 和原生 3D 扩散模型的 VAE-Diffusion 管线奠定了更强的重建基础。

## 原始出处

- 原始文件: [raw/papers/TopoMesh-High-Fidelity-Mesh-Autoencoding-via-Topological-Unification.md](../../raw/papers/TopoMesh-High-Fidelity-Mesh-Autoencoding-via-Topological-Unification.md)
- 原文链接: [https://arxiv.org/abs/2603.24278](https://arxiv.org/abs/2603.24278)
- Brief 条目: [brief.md 2026-07-28 > TopoMesh](../../raw/digest/brief.md)
- 深度阅读报告: [deepdive/2026-07-28/topomesh](../../raw/digest/deepdive/2026-07-28/topomesh-high-fidelity-mesh-autoencoding-via-topological-unification.md)

## Key Contributions

1. **拓扑统一范式**：首次在 VAE 中让 GT 和预测网格共享 DMC 拓扑结构，实现顶点/面层级的显式对应，启用直接的拓扑/顶点/法线监督
2. **Topo-Remesh**：全 GPU 加速 + L∞ 度量重网格化，15 秒完成 1024³ 分辨率转换，二面角分布与 GT 几乎一致
3. **解耦 VAE 架构**：稀疏体素-点交叉注意力编码器（单查询向量，74GB→3.8MB 注意力图压缩）+ 拓扑/几何解耦解码器
4. **稳定训练策略**：Teacher Forcing + GT 引导剪枝 + 渐进分辨率训练（32³ → 64³ → 128³）
5. **SOTA 效果**：锐边 F1 提升超 8%，CD 降低超 30%

## Method

![TopoMesh 框架概览](https://arxiv.org/html/2603.24278v2/x1.png)
*TopoMesh 两大模块：Topo-Remesh 将任意网格转为 DMC 兼容格式，Topo-VAE 在统一拓扑下进行编码/解码和显式监督*

### 整体思路

3D 原生扩散模型的 VAE-Diffusion 管线中，VAE 的重建质量决定了生成质量上限。现有 VAE 面临根本矛盾：**GT 网格具有任意、可变的拓扑结构**（顶点数、连接方式都不固定），而 **VAE 网络只能预测固定结构的隐式场**（如规则网格上的 SDF）。

TopoMesh 的核心洞察：**让 GT 网格和网络预测网格共享同一个 DMC 拓扑框架**。这样顶点和面就一一对应了，可以直接计算 L1 顶点损失和法线损失，而非依赖 SDF 或渲染等间接监督。

### Topo-VAE 架构

#### 稀疏体素-点编码器

输入网格顶点集 $V_i$（点云，可达 200 万点）和法线 $N_i$，输出稀疏体素特征 $z$。

**关键挑战**：全局注意力不可行（20k 体素 × 2M 点 = 74GB 注意力图）。
**解决**：每个点只属于唯一一个体素，替换为局部注意力——每个点只与自己所在的体素交互。

$$ O_i = \sum_{j=1}^{n_i} \text{Softmax}_i(\frac{Q \cdot K_j^T}{\sqrt{d}}) \cdot V_j $$

- $Q$: 共享可学习查询向量（所有体素共用——归一化到局部坐标后所有体素内部的几何类似）
- $K_j, V_j$: 体素内第 $j$ 个点特征的线性投影
- 注意力图从 $O(N \times P)$ 压缩到 $O(P)$（74GB → 3.8MB）

![注意力图压缩](https://arxiv.org/html/2603.24278v2/x2.png)
*左：注意力图压缩（每点只关注一个体素 → O(P)）；右：单查询向量聚合体素内所有点*

#### 解耦拓扑/几何解码器

标准 [[FlexiCubes]] 使用 SDF 值 s 同时决定拓扑（符号）和几何（幅值），导致两个损失互相竞争。TopoMesh 将 SDF 解耦：

$$ \text{Topo} = \{o, \gamma\}, \quad \text{Geom} = \{u, \alpha, \beta, \delta\} $$

网格生成分两步：
$$ F_o = \text{DMC}(o) $$
$$ V_o = \text{FlexiCubes}(o \times u, \alpha, \beta, \delta, \gamma) $$

- 拓扑参数 $\{o, \gamma\}$ 决定面的存在和三角剖分
- 几何参数 $\{u, \alpha, \beta, \delta\}$ 决定顶点位置
- 拓扑和几何独立学习，避免"拉锯战"

### 显式网格级损失

![显式网格级损失](https://arxiv.org/html/2603.24278v2/x3.png)

因为拓扑统一，可以直接在网格属性上施加监督：

1. **拓扑损失** $L_{topo} = \text{BCE}(o, o_{gt})$ — 网格角点占用率二值交叉熵
2. **顶点损失** $L_{vert} = \text{L1}(v, v_{gt})$ — 顶点位置 L1 距离
3. **法线损失** $L_{normal} = \text{L1}(n, n_{gt})$ — 面朝向监督（DMC 输出四边形需处理 triangulation 不一致）

总损失：
$$ L = \lambda_{topo} L_{topo} + \lambda_{vert} L_{vert} + \lambda_{normal} L_{normal} + \text{正则项} $$

### Teacher Forcing 训练策略

**问题**："拓扑-几何拉锯战"——拓扑正确时拓扑损失消失但几何损失突然变大，梯度使拓扑翻转回错误状态。

**解决**：训练时用 GT 拓扑 $o_{gt}$ 代替预测 $o$ 传入几何解码器：
$$ \text{训练时: } V_o = \text{FlexiCubes}(o_{gt} \times u, \alpha, \beta, \delta, \gamma) $$
$$ \text{推理时: } V_o = \text{FlexiCubes}(o \times u, \alpha, \beta, \delta, \gamma) $$

**配合策略**：
- GT 引导体素剪枝：保留 GT 表面窄带内体素
- 渐进分辨率训练：32³(160k) → 64³(160k) → 128³(380k)，共 700k 步

### Topo-Remesh — 全 GPU 加速重网格化

#### L∞ 距离度量（核心创新）

传统 L2 距离只测点到最近点的欧氏距离，会磨圆锐角。L∞ 距离引入局部表面结构：

$$ D_\infty(P, Q) = \max_{T_i \in T(Q)} d(P, \Pi_i) $$

- $Q$: $P$ 在网格上的最近点
- $\Pi_i$: 包含 $Q$ 的第 $i$ 个邻接面平面
- 直觉：将局部表面沿每个邻接面法向膨胀 ε，形成多面体包络

![L2 vs L∞](https://arxiv.org/html/2603.24278v2/x4.png)
*L2 平滑角点 / L∞ 保留角度*

#### 流水线（5 阶段，全 GPU，~15 秒）

| 阶段 | 耗时 | 说明 |
|------|------|------|
| Voxelization | 0.15s | 输入网格 → 1024³ 体素 |
| FloodFill | 4.54s | 定位表面窄带内体素 |
| SDF Calculation（L∞） | 1.06s | 网格角点计算 L∞ 距离 |
| Isosurface Extraction（ODC） | 8.81s | 提取保留锐边的流形网格 |
| Compression（DMC） | 0.05s | 编码为紧凑二进制（压缩比 76%） |

![Remesh 流水线](https://arxiv.org/html/2603.24278v2/x5.png)
![Remesh 对比](https://arxiv.org/html/2603.24278v2/x6.png)
*Topo-Remesh 产生干净、保留锐边的结果*

## Training

- 优化器: AdamW，恒定学习率 0.0001
- VAE 训练 700k 步: 32³(160k) → 64³(160k) → 128³(380k)，batch size 64
- DiT 训练 800k 步: 32³(200k) → 64³(300k) → 128³(300k)，batch size 512
- 数据: 320k 高质量网格（Sketchfab）
- 评估基准: Dora-Bench（1.4k 物体）+ Topo-Bench（1k 锐边物体）

## Results & Comparisons

### Remesh 质量

| 方法 | Objaverse CD↓ | Objaverse F1↑ | 时间↓ |
|------|-------------|-------------|------|
| Dora | 1.057 | 0.987 | 116.3s |
| Sparc3D | 2.864 | 0.970 | 175.9s |
| **Topo-Remesh** | **0.964** | **0.988** | **18.5s** |

L∞ 度量在 Objaverse 和 Thingi10K 上全面超越 L2 基线，二面角分布与 GT 几乎一致。

### VAE 重建

![VAE 重建对比](https://arxiv.org/html/2603.24278v2/x7.png)
*TopoMesh 更好地保留了锐边和精细几何细节*

| 方法 | #Latent | Topo-Bench F1-S↑ | Dora-Bench CD↓ | Dora-Bench F1-S↑ |
|------|---------|-----------------|---------------|-----------------|
| SparseFlex | 244691 | 0.873 | 1.625 | 0.844 |
| **TopoMesh** | **56006** | **0.932** | **1.126** | **0.915** |

仅用 SparseFlex 四分之一的 token，锐边 F1 提升 5.9%-7.1%。

### Image-to-3D 生成（Toys4K）

| 方法 | FID↓ | KID(×10³)↓ |
|------|------|------------|
| Hunyuan3D-2.1 | 59.43 | 5.97 |
| Trellis | 59.61 | 6.03 |
| Direct3D-S2 | 45.33 | 5.47 |
| **TopoMesh** | **42.48** | **4.63** |

![Image-to-3D 生成](https://arxiv.org/html/2603.24278v2/x10.png)
*TopoMesh 生成的几何更锐利、与输入图更对齐*

### 核心消融

| 配置 | CD↓ | F1↑ | F1-S↑ |
|------|-----|-----|-------|
| 渲染监督（单形状过拟合） | 1.731 | 0.776 | 0.711 |
| 显式网格监督 | **0.150** | **0.975** | **0.991** |
| 32³ 分辨率 | 1.812 | 0.933 | 0.790 |
| 64³ 分辨率 | 1.693 | 0.940 | 0.869 |
| 128³ 分辨率 | 1.126 | 0.973 | 0.915 |

![显式 vs 渲染监督](https://arxiv.org/html/2603.24278v2/x9.png)
*显式网格监督可近乎无损重建锐边，渲染监督做不到*

## Related Work Analysis

### 与 [[SparseFlex]]、[[Trellis]] 的关系

三者都是稀疏体素 VAE。Trellis 和 SparseFlex 使用 FlexiCubes + 渲染监督，TopoMesh 通过拓扑统一实现显式网格监督。结果：TopoMesh 的锐边 F1 显著领先（0.932 vs 0.873），且 token 数仅为 SparseFlex 的 1/4。

### 与 [[Dora]]、[[TripoSG]] 的关系

VecSet-based VAE（Dora、TripoSG）用全局潜向量集表示形状，擅长整体形状但限制细粒度细节。TopoMesh 的稀疏体素局部表示在精细几何上更优。

### 与 [[FlexiCubes]] 的关系

TopoMesh 的编码器和训练策略（Teacher Forcing + 拓扑/几何解耦）本质上是围绕 FlexiCubes 的改进，解决了其 SDF 耦合导致的训练不稳定问题。

## Ablations

### L∞ vs L2 重网格（Fig. 9）

二面角分布直方图显示 L∞ 完整保留锐角分布，L2 将锐角塌缩为近平面。这是 Topo-Remesh 保留锐边的根本原因。

![L∞ 消融](https://arxiv.org/html/2603.24278v2/x8.png)
*L∞ 保留锐利二面角分布，L2 将其塌缩*

### 显式监督 vs 渲染监督（Fig. 10 + Table 3）

单形状过拟合实验中，渲染监督 CD 1.731 而显式监督仅 0.150，差距超过 10 倍。说明渲染监督的模糊梯度是限制现有 VAE 的根本原因。

### 多分辨率推理（Table 3）

32³→128³ 时 CD 从 1.812 降至 1.126，F1-S 从 0.790 提升至 0.915。高分辨率对锐边保留至关重要。

## Limitations

- 稀疏体素到高分辨率时产生数百万体素，计算资源需求大
- Remesh 受限于基分辨率，无法捕获小于体素尺寸的极细细节
- DMC 输出四边形标准网格，复杂拓扑表达能力受限于体素网格

## 评论与启示

- 来自深度阅读报告：核心思路是**换了个表达方式来进行学习**（Dual Marching Cubes 统一拓扑），使原来无法直接比较的"苹果和橘子"变成了"苹果和苹果"
- 拓扑统一的思路具有通用性：任何涉及"GT 任意拓扑 vs 预测固定结构"的任务都可借鉴，如点云补全、场景图生成
- 与 [[GS-2M]] 的对比：GS-2M 解决"反射表面"这个数据域的问题（通过增加材质参数），TopoMesh 解决"拓扑不匹配"这个表示域的问题（通过统一拓扑框架），两种不同维度的"瓶颈突破"
- [[Dual Marching Cubes]] 和 [[FlexiCubes]] 值得做独立概念页

## Connections

- [[Dual Marching Cubes]] — TopoMesh 统一拓扑的核心框架
- [[FlexiCubes]] — 解码器基础，TopoMesh 做了解耦改进
- [[SparseFlex]] / [[Trellis]] — 同期稀疏体素 VAE，使用渲染监督
- [[Dora]] / [[TripoSG]] — VecSet-based VAE，全局表示
- [[3DGS]] — VAE-Diffusion 管线的下游生成任务相关
- [[GS-2M]] — 同期 wiki 页面，同为网格重建任务的不同维度突破

## Contradictions

- 与 [[SparseFlex]] 在 token 效率上的对比：TopoMesh 以 1/4 token 达到更高锐边 F1，说明拓扑统一带来的显式监督比大量 token + 间接监督更高效
- 与 [[Trellis]] 在分辨率上的对比：Trellis 用 256³ 而 TopoMesh 用 128³ latent + 1024³ remesh，两种不同的精度策略

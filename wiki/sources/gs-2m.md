---
title: "GS-2M: Material-aware Gaussian Splatting for High-fidelity Mesh Reconstruction"
type: source
tags: [paper]
date: 2026-07-28
source_file: raw/papers/GS-2M-Material-aware-Gaussian-Splatting-for-High-fidelity-Mesh-Reconstruction.md
url: "https://arxiv.org/abs/2509.22276"
venue: ""
published: 2025
links: ["https://ndming.github.io/publications/gs2m/"]
---

## Summary

GS-2M 提出一种材料感知的联合优化框架，在 [[3DGS]] 显式重建中统一了高保真网格重建和材质分解两个任务。核心创新是多视角粗糙度监督策略：通过 NCC（归一化互相关）衡量不同视角间的光度变化来指导粗糙度学习，完全消除对神经组件的依赖。结合无偏深度渲染、遮挡感知滤波和多视角法线一致性约束，GS-2M 在 DTU 上达到 SOTA（CD 0.53），并在 Shiny Blender 等高反光场景上显著优于现有显式方法。

## 原始出处

- 原始文件: [raw/papers/GS-2M-Material-aware-Gaussian-Splatting-for-High-fidelity-Mesh-Reconstruction.md](../../raw/papers/GS-2M-Material-aware-Gaussian-Splatting-for-High-fidelity-Mesh-Reconstruction.md)
- 原文链接: [https://arxiv.org/abs/2509.22276](https://arxiv.org/abs/2509.22276)
- Brief 条目: [brief.md 2026-07-28 > GS-2M](../../raw/digest/brief.md)
- 深度阅读报告: [deepdive/2026-07-28/gs-2m](../../raw/digest/deepdive/2026-07-28/gs-2m-material-aware-gaussian-splatting-for-high-fidelity-mesh-reconstruction.md)

## Key Contributions

- **材料-网格联合优化框架**：为每个 3D 高斯体增加 albedo 和 roughness 两个可学习参数，通过 Cook-Torrance 微表面 PBR 渲染管线统一优化，同时输出高保真网格和材质分解
- **多视角粗糙度监督（L_ro）**：利用 NCC 损失量化不同视角间光度变化，高变化（反光区域）鼓励低粗糙度，低变化（漫反射区域）鼓励高粗糙度，完全无需神经编码器或预训练先验
- **遮挡感知滤波 + 多视角法线一致性**：在 PGSR 的多视角约束基础上增加显式深度一致性检测和法线一致性损失，提升高频区域的几何鲁棒性

## Method

![GS-2M cover](https://arxiv.org/html/2509.22276v2/figures/cover-updated.jpg)
*GS-2M 联合优化框架：将材质分解整合到网格重建管线中，对反射表面也能生成水密三角网格*

### 整体思路

GS-2M 基于 [[PGSR]] 构建，继承其无偏深度渲染和多视角一致性约束以保持 SOTA 重建质量。在此基础上增加两层结构：(1) 为每个高斯体引入材质参数 (albedo + roughness)，通过延迟 PBR 渲染生成合成图，用真实图监督；(2) 提出多视角粗糙度监督，利用不同视角间光度变化来区分反光和漫反射区域，指导 roughness 学习。

### 无偏深度渲染

传统 3DGS 用相机空间 z-blending 做深度，邻近像素因共享相近 z 值产生有偏深度。GS-2M 采用**平面深度**（plane depth）：将每个高斯体视为微小平面，法线取缩放最小轴对应方向，距离值用平面距离代替 z 值。

深度图公式：
$$ \mathcal{D}(\mathbf{p}) = \frac{\bar{\mathcal{D}}(\mathbf{p})}{\mathcal{N}(\mathbf{p}) \cdot (K^{-1}\tilde{\mathbf{p}})} $$

- $\bar{\mathcal{D}}$: α-blending 融合的距离图，$\mathcal{N}$: 法线图，$K$: 相机内参，$\tilde{\mathbf{p}}$: 像素齐次坐标

### 多视角一致性与遮挡滤波

在 PGSR 的多视角几何/光度损失基础上做两项改进：

1. **多视角法线一致性**：在参考视图和邻居视图世界空间采样点的法线方向差异作为额外损失
2. **遮挡感知滤波**：将参考视图像素反投到邻居视图相机空间，比较 z 坐标与深度图值，不一致的像素排除在损失计算之外

![多视角一致性与遮挡滤波](https://arxiv.org/html/2509.22276v2/figures/multi-view-pgsr.jpg)
*上：无效对应滤波——p₂ 因深度不一致被排除；下：多视角法线一致性约束*

### PBR 渲染与材质建模

每个高斯体增加两个可学习参数：反照率 $a_i \in \mathbb{R}^3$ 和粗糙度 $\rho_i \in [0,1]$。采用 Cook-Torrance 微表面 BRDF 模型，通过延迟渲染合成 PBR 图像。

BRDF 公式：
$$ f_r(\omega_i, \omega_o) = \frac{(1-m)a}{\pi} + \frac{D \cdot F \cdot G}{4(n\cdot\omega_o)(n\cdot\omega_i)} $$

- $m = 1-\rho$: 金属度近似
- $D(\rho, \theta_h)$: GGX 法线分布函数，$\rho$ 越小高光越锐利
- $F$: Schlick 近似 Fresnel 项，$G$: 几何项
- 光照用可微分环境 cubemap 建模，预滤波到不同 mip 级别

通过 α-blending 渲染 albedo 图 $\mathcal{A}$ 和 roughness 图 $\mathcal{R}$，合成 PBR 图像 $\bar{\mathcal{I}}$ 后与真实图 $\mathcal{I}$ 计算 L_pbr 损失。

### 多视角粗糙度监督（核心创新）

关键观察：**高反光区域在不同视角下外观变化剧烈（NCC 低），漫反射区域光度稳定（NCC 高）**。

流程：
1. 对参考视图每个像素 p，在邻居视图找到对应 patch
2. 计算 warp 后 patch 的 NCC 损失 L_NCC
3. L_NCC > λ_ref（反光区域）→ 惩罚高粗糙度，鼓励低粗糙度
4. L_NCC < λ_ref（漫反射区域）→ 惩罚低粗糙度，鼓励高粗糙度

$$ \mathcal{L}_{ro} = \frac{1}{|\mathcal{R}|} \sum_{\mathbf{p}} \tanh(k_{ro}(L_{NCC}(\mathbf{p}) - \lambda_{ref})) \mathcal{R}(\mathbf{p}) $$

- $k_{ro}=8.0$，$\lambda_{ref} \approx 0.9$（默认）
- 纹理缺失区域用梯度版 NCC 替换防止 L_NCC 爆炸

![粗糙度监督](https://arxiv.org/html/2509.22276v2/figures/mv-rough.jpg)
*通过 NCC 量化光度变化，用阈值 λ_ref 判断反光/漫反射区域，奖惩对应粗糙度*

![粗糙度消融](https://arxiv.org/html/2509.22276v2/figures/mv-ro-ablation.jpg)
*上：无 L_ro — 光照噪声大、反照率被高光污染；下：有 L_ro — 分解清晰*

## Training

**两阶段训练**：

1. **引导阶段**（前 5,000 次迭代）：仅优化几何参数，损失为 L_rgb + L_plane + L_alpha（若有 mask）
2. **联合优化阶段**（最多 30,000 次迭代）：全部损失激活，L_rgb 替换为 L_pbr

**总损失**：
$$ \mathcal{L} = \mathcal{L}_{plane} + \mathcal{L}_{alpha} + \mathcal{L}_{dn} + \mathcal{L}_{mv} + \mathcal{L}_{tv} + \mathcal{L}_{sm} + \mathcal{L}_{ro} + \mathcal{L}_{pbr} $$

- L_plane: 惩罚非平面高斯体
- L_dn: 深度-法线一致性（图像梯度加权）
- L_mv: 多视角几何+光度一致性（含法线一致性 + 遮挡滤波）
- L_tv: 以粗糙度为权重的法线平滑
- L_sm: BRDF 参数平滑
- L_ro: 粗糙度监督（核心）
- L_pbr: PBR 渲染 L1 + SSIM 损失

**网格提取**：训练完成后从所有视角渲染 RGB-D，TSDF 融合 + marching cubes 提取三角网格。

## Results & Comparisons

### DTU 数据集（15 场景 Chamfer Distance ↓）

| 方法 | 类型 | CD ↓ | 时间 |
|------|------|------|------|
| Neuralangelo | 隐式 | 0.61 | ~16h |
| PGSR | 显式 | 0.52 | 30m |
| GausSurf | 显式 | 0.52 | 7.2m |
| **GS-2M w/o BRDF** | 显式 | **0.51** | **22.4m** |
| **GS-2M** | 显式 | 0.53 | 51.0m |

DTU 上 GS-2M 与 SOTA 显式方法持平（CD 0.51-0.53），完整版因 PBR 开销训练时间加倍但保持了竞争力的重建质量。

### Shiny Blender 反射场景

![Shiny Blender 对比](https://arxiv.org/html/2509.22276v2/figures/shiny-meshes-horizontal.jpg)
*GS-2M 在反射物体上产生均匀水密网格，2DGS/GOF/PGSR 出现变形或空洞*

### Novel View Synthesis（DTU PSNR ↑）

| 方法 | PSNR ↑ |
|------|--------|
| Neuralangelo | 33.84 |
| PGSR | 33.33 |
| **GS-2M w/o BRDF** | **34.22** |
| GS-2M | 33.86 |

增强的多视角约束（法线一致性 + 遮挡滤波）使 NVS 质量超越所有 SOTA 重建方法。

### TnT 数据集（F1-score ↑）

| 场景 | PGSR | GS-2M w/o BRDF |
|------|------|----------------|
| Barn | 0.66 | 0.57 |
| Truck | 0.66 | **0.67** |

### 核心消融

| 配置 | DTU CD ↓ | DTU PSNR ↑ |
|------|----------|------------|
| 无法线一致性 | 0.58 | 26.73 |
| 无遮挡滤波 | 0.53 | 33.76 |
| 完整版 | **0.53** | **33.86** |

法线一致性是重建质量最大提升来源，遮挡滤波主要提升 NVS。

## Related Work Analysis

### 与 [[PGSR]] 的关系

GS-2M 构建于 PGSR 之上，继承其无偏深度渲染和多视角约束。核心区别：PGSR 缺乏外观建模，在反射表面产生畸变；GS-2M 通过 PBR 材质参数 + 粗糙度监督解决了这个问题。

### 与 [[Ref-DGS]]、[[GS-ROR²]] 的关系

三者都试图在 3DGS 中统一网格重建和材质分解。区别在于：GS-ROR² 依赖 SDF 主干网络 + 编码器-解码器，Ref-GS 依赖张量分解。GS-2M 的独特优势是用极简的可学习参数（albedo + roughness）+ 自监督 NCC 策略替代了所有神经组件，保持了 22-51 分钟的快速训练。

### 与 [[NeuS]]、[[Neuralangelo]] 的关系

隐式方法（Neuralangelo）重建质量高但训练需 16h，GS-2M 在 51min 达到可比的质量（CD 0.53 vs 0.61），速度优势显著。但在 TnT 无界场景上隐式方法仍更鲁棒。

## Ablations

### 粗糙度监督 L_ro（Table 2 + Fig. 7）

移除 L_ro 后 albedo 被高光污染、环境光噪声大，说明 PBR 损失 L_pbr 单独极度欠约束。L_ro 在无任何神经先验的条件下有效约束了材质分解。

### 增强多视角约束（消融表格）

法线一致性是最大贡献源（CD 0.58 → 0.53），遮挡滤波主要影响 NVS 质量（PSNR 33.76 → 34.22）。

### BRDF 版 vs 无 BRDF 版

无 BRDF 版在纯几何指标（CD 0.51 vs 0.53）上反而略优，说明材质参数的额外自由度在某些场景轻微干扰了几何收敛，但联合版本获得了材质分解能力。

## Limitations

- **反照率和光照欠约束**：联合优化中反照率和环境光的分解仍不充分，存在噪声伪影
- **无法处理自反射**：Cook-Torrance 模型无法建模间接光照/相互反射（如 Toaster 场景）
- **Metallic 近似不精确**：$m = 1 - \rho$ 是硬编码近似，对某些场景（如汽车白色条纹）不成立
- **无界场景 OOM**：自适应密度控制在背景细节丰富场景生成过多高斯体导致显存溢出
- **仅适用于物体中心场景**：PBR 管线依赖受控光照条件

## 评论与启示

- 来自深度阅读报告：GS-2M 的核心思路是利用多视角之间的一致性来判断反光区域，以此调节粗糙度的惩罚——这是一种优雅的自监督物理先验，无需任何标注数据
- 对比 [[Ref-DGS]] 和 [[GS-ROR²]]，GS-2M 在"简单性"上做到了极致：仅用两个可学习标量 + NCC 损失就达到了可比甚至更好的反射表面重建效果
- 与 [[SuGaR]] 的对比思路值得注意：SuGaR 是"正则化高斯体使其适应表面"，GS-2M 是"为高斯体增加材质属性使其适应反射"，两种不同的"修复"范式

## Connections

- [[3DGS]] — GS-2M 以 3DGS 为基座，增加材质参数和 PBR 渲染
- [[PGSR]] — 直接基线和构建基础，贡献了无偏深度渲染和多视角约束
- [[Ref-DGS]] — 同期工作，用双高斯解耦处理反射，GS-2M 用 PBR 参数化
- [[SuGaR]] — 早期 3DGS 网格提取方法，GS-2M 属于同一任务线
- [[NeuS]] / [[Neuralangelo]] — 隐式重建 SOTA，GS-2M 在速度上显著超越

## Contradictions

- 与 [[PGSR]] 在反射表面重建上的比较：PGSR 缺乏外观建模导致反射场景畸变，GS-2M 的 PBR 框架解决了此问题，但代价是训练时间翻倍

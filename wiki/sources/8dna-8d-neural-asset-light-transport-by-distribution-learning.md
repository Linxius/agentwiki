---
title: "8DNA: 8D Neural Asset Light Transport by Distribution Learning"
type: source
tags: [Neural Rendering, Light Transport, Normalizing Flow, Distribution Learning, Pre-baking, 8D Transport]
date: 2026-08-04
source_file: ""
url: https://arxiv.org/abs/2604.25129
links: []
---

## Summary

本文提出 **8DNA（8D Neural Asset）**，一种将复杂 3D 资产内部的 8D 全局光传输预烘焙到神经表示中的方法。与假设远距离照明的 6D 方法（如 RNA）不同，8DNA 学习完整的 8D 光传输 $F(x_o, \omega_o, x_i, \omega_i)$，支持近距离照明（near-field illumination）下的精确渲染。核心创新是**分布学习框架**：使用归一化流（normalizing flow）从正向路径追踪样本中学习散射分布，而非传统回归损失。在 Candle、Milk、Cat 等 10 个资产上的实验表明，8DNA 在精度上接近路径追踪参考，渲染方差降低 2-20×，推理速度提升 2-20×，训练时间比远场基线快 3×（体积资产）。

## 原始出处

- 原文链接: [arXiv:2604.25129](https://arxiv.org/abs/2604.25129)

## Key Contributions

1. **8D 神经资产表示**：首次学习完整的 8D 光传输 $F(x_o, \omega_o, x_i, \omega_i)$，不再假设远距离照明，可精确重现近距离光照下的遮挡、互反射等效应。
2. **分布学习训练框架**：使用归一化流从正向路径追踪样本中直接采样光传输分布，无需计算 8D 回归损失的蒙特卡洛估计，训练数据生成只需 1 spp（远场方法需 4096-8192 spp）。
3. **跨渲染器可移植**：烘焙后的神经资产可导入任意渲染器进行 PBR，无需在部署渲染器中重新实现原始散射模型。

## Method

### 框架图

```
[训练阶段]
  正向路径追踪 (1 spp) → 采样 (x_o, ω_o, u_i, ω_i, β_i)
                              ↓
           归一化流 p_θ(u_i, ω_i | x_o, ω_o)  +  存活概率 α_θ(x_o, ω_o)
              (Scattering Distribution)           (Albedo Term)
                              ↓
               联合损失: -β·log p_θ + (α_θ - β)²
                              ↓
              烘焙好的 8DNA 神经资产 (可跨渲染器部署)

[推理阶段]
  8DNA 资产 + 任意照明 L_i → 快速采样/评估 → 输出 L_o
  (无需追踪长散射路径)
```

### 双重写作

**问题**：8D 光传输 $F(x_o, \omega_o, x_i, \omega_i)$ 直接回归训练面临高方差问题。因为需要 doubly delta 照明 $\delta(x-x_i)\delta(\omega-\omega_i)$ 作为监督信号，在高维空间中采样极其困难，且强峰值照明使蒙特卡洛估计方差巨大。

**解决思路**：不直接回归 $F$ 的 PDF 值，而是将 $F$ 分解为**散射分布** + **存活概率（albedo）**，使训练退化为简单的正向路径追踪采样——这正是渲染中最成熟、方差最低的操作。

**具体方法**：

**1. 光传输分解**

将 8D 光传输分解为：

$$F(u_i, \omega_i | x_o, \omega_o) = p(u_i, \omega_i | x_o, \omega_o) \cdot \beta(x_o, \omega_o)$$

其中 $p$ 是归一化的散射分布（决定光线散射到哪个方向/位置），$\beta$ 是存活概率（决定光线不被吸收的概率）。

**2. 归一化流建模散射分布**

用 16 节点 rqs（rational quadratic spline）归一化流 + 两个 MLP（各 64 hidden units, 2 layers）建模条件分布 $p_\theta(u_i, \omega_i | x_o, \omega_o)$。归一化流的性质是：
- **可精确采样**：采样分布天然与 $F$ 成正比，无需 next-event estimation
- **可精确求 PDF**：支持训练时的重要性采样

**3. 直接散射分离**

将第一次弹射的 direct scattering 与 indirect scattering 分离，避免归一化流难以建模高频细节（如 specular interreflections、caustics）的问题。

**4. 训练数据生成（仅 1 spp）**

从随机 $(x_o, \omega_o)$ 出发，进行标准正向路径追踪（无 next-event estimation）：
- 在表面/体积中采样散射事件
- 记录完整路径的 throughput $\beta_i$
- 将入射位置 $x_i$ 投影到包围盒几何参数化为 $u_i$
- 直接得到训练样本 $(x_o, \omega_o, u_i, \omega_i, \beta_i)$

**5. 训练损失**

$$\mathcal{L} = \mathbb{E}[-\beta_i \log p_\theta(u_i, \omega_i | x_o, \omega_o)] + \mathbb{E}[(\alpha_\theta(x_o, \omega_o) - \beta_i)^2]$$

第一项是散射分布的负对数似然，第二项是存活概率的回归损失。

**6. 推理（部署）**

烘焙好的 8DNA 资产可被任意渲染器查询：给定 $(x_o, \omega_o)$ 和照明 $L_i$，从 $p_\theta$ 采样 $(u_i, \omega_i)$ 并乘以 $\alpha_\theta$ 得到 $L_o$。无需在渲染器中实现原始散射模型。

## Training

- **数据生成**：正向路径追踪，仅 1 spp，无 next-event estimation，在线生成
- **网络架构**：归一化流（16 节点 rqs）+ 2 个 MLP（64 hidden units, 2 layers），加上 albedo MLP
- **输入编码**：标准频域编码（frequency encoding）
- **优化器**：Adam
- **数据重采样**：30×（每个样本被采样 30 次用于训练）
- **GPU 内存**：体积资产 ~6.8 GB，Teaset ~5.3 GB，纤维资产（CurlHair, Hair, Fabric）7.2-11.4 GB

## Results & Comparisons

### 数据集

10 个资产：Candle（ homog. SSS）、Milk（heterog. volume）、Cat（heterog. volume with colored slabs）、Seal（high-albedo）、Dragon（heterog. volume）、Bunny、CurlHair（hair BSDF）、Hair（hair BSDF）、Fabric（hair BSDF）、Teaset（conductor BSDF）

### 精度（MSE）

| 方法 | Candle | Milk | Cat | Seal | Dragon | Bunny | CurlHair | Hair | Fabric | Teaset |
|------|--------|------|-----|------|--------|-------|----------|------|--------|--------|
| Far-field | 5.760 | 0.430 | 0.162 | 0.065 | 0.505 | 0.103 | 0.228 | 1.381 | 3.379 | 0.707 |
| **Ours** | **2.855** | **0.156** | **0.009** | **0.057** | **0.182** | **0.057** | **0.126** | **0.950** | **2.541** | **0.075** |

8DNA 在所有资产上显著优于远场基线，尤其在 Milk（0.009 vs 0.162）、Teaset（0.075 vs 0.707）上差距最大。远场方法在 Cat 的 mirror 互反射（猫内部白红蓝 volumetric slabs 在前视角呈紫色）和 Teaset 的 conductor interreflections 上完全失败。

### 方差与速度（128 spp）

| 方法 | Candle 方差 | Milk 方差 | Seal 速度(min) | Milk 速度(min) |
|------|-----------|----------|---------------|---------------|
| PT | 54.34 | 33.41 | 2.04 | 15.6 |
| Far-field | 12.20 | 0.445 | 0.30 | 0.39 |
| **Ours** | **27.44** | **2.491** | **0.55** | **0.69** |

- 8DNA 在体积资产（Milk, Seal）上比 PT 快 **2-20×**
- 在纤维/表面散射（CurlHair, Hair, Fabric）上比 PT 快 **1.4-4×**
- Far-field 方差最低、速度最快，但光传输有偏（biased）

### 环境光精度

| 方法 | Milk | Cat | Teaset |
|------|------|-----|--------|
| Far-field | 0.598 | 1.657 | 0.724 |
| **Ours** | **0.079** | **0.153** | **0.092** |

远场方法在 Milk、Cat、Teaset 上因回归损失高方差未能收敛。

### 单一区域光精度

| 方法 | Milk | Cat | Teaset |
|------|------|-----|--------|
| Far-field | 1.178 | 1.013 | 14.240 |
| **Ours** | **0.152** | **0.551** | **2.389** |

近距离照明下远场方法误差急剧放大（Teaset: 14.240 vs 2.389）。

### 训练时间

| 资产类型 | 方法 | 数据生成 | 优化 | 总计 |
|---------|------|---------|------|------|
| 体积 | Far-field | 5.91h | 0.84h | 6.75h |
| 体积 | **Ours** | **0.55h** | 1.68h | **2.23h** |
| 表面 | Far-field | 1.26h | 0.72h | 1.98h |
| 表面 | **Ours** | **0.33h** | 1.45h | **1.78h** |

8DNA 体积资产训练快 **3×**，表面资产基本持平。

## Related Work Analysis

- **RNA (Mullia et al. 2024)**：可重新光照神经资产，但假设远场照明（6D 光传输），无法精确处理近距离照明。
- **Tg et al. 2024a**：对半透明物体的全球面入射方向建模，但仍假设内部散射各向同性，且推理需每出射光线追踪多条入射光线。
- **Kuznetsov et al. 2021, 2022**：平面和曲面材料的神经 BRDF 学习，仅处理表面散射。
- **Neural Importance Sampling (Müller et al. 2019)**：用归一化流做 BSDF 采样，与本工作使用归一化流的思想相似，但目标不同。
- **Li et al. 2025 (Pure-Sample)**：也使用采样而非回归学习神经材质，但针对微几何（microgeometry），未处理 3D 资产的全局光传输。

## Limitations

1. **凸包内无附加几何**：模型假设资产凸包内无额外几何遮挡。当外部物体遮挡预烘焙光路时会产生错误（图 14：Dragon 资产中扩散 slab 遮挡面积光源，导致模型遗漏遮挡效应）。
2. **归一化流表达能力有限**：难以精确建模子流形上的高频细节（如 specular interreflections、caustics、glints）。在 Teaset 上出现 oversmooth 高频细节的问题。
3. **近场 vs 远场权衡**：相比 6D 远场模型，8DNA 推理方差更高、速度更慢（Far-field 比 8DNA 快约 2×），因为需要评估 $x_i$ 依赖的网络。
4. **纯表面资产优势有限**：在简单资产（如 Teaset）上，MIS 已能有效降低 PT 方差，8DNA 的方差减少不明显。
5. **GPU 内存**：纤维资产训练需 7.2-11.4 GB，网络优化需 ~4.5 GB。

## 评论与启示

1. **分布学习 vs 回归学习**：本文证明了在光传输预烘焙中，分布学习（normalizing flow sampling）比回归（L2 loss + 蒙特卡洛估计）更稳定、更高效。这一思想可推广到其他高维渲染量（如 BSDF、BTF）的神经表示。

2. **1 spp 的数据生成**：训练数据生成仅需 1 spp 的正向路径追踪，大幅降低了数据成本。这使 8DNA 可以大规模重采样（30×）而远场方法需要数天。

3. **8D 参数的可压缩性**：归一化流能够有效参数化 8D 函数，说明光传输虽在高维空间，但存在低维流形结构可被有效压缩。

## Connections

- [[RNA: Relightable Neural Assets]] — 远场 6D 光传输预烘焙的代表方法
- [[Neural Importance Sampling (Müller et al. 2019)]] — 归一化流用于 BSDF 采样的先驱工作
- [[Normalizing Flows]] — 归一化流理论与 rational quadratic spline 实现
- [[Subsurface Scattering]] — 次表面散射的物理模型与渲染方法
- [[BSSRDF]] — Bidirectional Subsurface Scattering Reflectance Distribution Function
- [[Path Tracing]] — 正向路径追踪算法与 next-event estimation
- [[Mitsuba 3]] — 实验使用的渲染器

## Contradictions

- 无直接矛盾。8DNA 的 8D 表示是对 6D 远场方法的扩展，而非替代——远场方法在远场近似有效的场景下仍然更快、方差更低。两者适用场景不同。

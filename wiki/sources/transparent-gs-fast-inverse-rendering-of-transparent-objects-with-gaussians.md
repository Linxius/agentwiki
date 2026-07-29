---
title: "TransparentGS: Fast Inverse Rendering of Transparent Objects with Gaussians"
type: source
tags: [paper, 3d-gaussian-splatting, inverse-rendering, transparent-objects, deferred-rendering, gaussian-probe]
date: 2026-07-29
source_file: ../../raw/digest/sources/2026-07-29/arxiv-250418768-d85018a2.md
url: "https://arxiv.org/abs/2504.18768"
doi: "10.1145/3730892"
venue: "ACM TOG (SIGGRAPH 2025)"
published: 2025
authors:
  - Letian Huang
  - Dongwei Ye
  - Jialin Dan
  - Chengzhi Tao
  - Huiwen Liu
  - Kun Zhou
  - Bo Ren
  - Yuanqi Li
  - Yanwen Guo
  - Jie Guo
institutions:
  - "南京大学 软件新技术国家重点实验室"
  - "南开大学 计算机科学与技术学院"
  - "浙江大学 CAD&CG 国家重点实验室"
links:
  - "https://letianhuang.github.io/transparentgs/"
  - "https://github.com/LetianHuang/transparentgs"
---

## Summary

TransparentGS 提出一种基于 3D-GS 的快速逆向渲染管线，专门用于在复杂光照和视角条件下重建透明物体。核心创新包括：**透明高斯基元**（Transparent Gaussian Primitives）——在 3D 高斯上显式编码法线、粗糙度、金属度、透明度和折射率等物理材质属性，并通过**延迟折射**策略实现高光折射渲染；**高斯光场探针**（GaussProbe）——将环境光和邻近物体间接光统一编码为环绕透明物体的 360 度全景探针；**基于深度的迭代探针查询算法**（IterQuery）——通过深度引导的迭代收敛消除多探针视差误差。该方法在 1 小时内完成重建（比 NeRF 类方法快 20 倍以上），支持实时新视角合成，并在折射细节、反射-折射解耦、有色透明物体等方面全面领先基线方法。

## 原始出处

- 原始文件: [arxiv-250418768-d85018a2.md](../../raw/digest/sources/2026-07-29/arxiv-250418768-d85018a2.md)
- 原文链接: [https://arxiv.org/abs/2504.18768](https://arxiv.org/abs/2504.18768)
- Brief 条目: [brief.md 2026-07-29 > TransparentGS](../../raw/digest/brief.md)

## Key Contributions

1. **透明高斯基元**：在 3D-GS 原语上扩展 BSDF 参数化（法线、粗糙度、金属度、透明度 t、折射率 eta），使球谐无法处理的高频镜面反射和折射能够通过物理渲染方程精确计算
2. **延迟折射策略**：先对多个高斯基元的材质属性做 alpha 加权混合得到统一 G-Buffer（法线图、击中点图），再用斯涅尔定律计算单一折射方向查询环境光，避免前向折射的多方向模糊问题
3. **高斯光场探针**（GaussProbe）：用原始 3D-GS 重建背景后，在透明物体周围放置虚拟相机烘焙 360 度全景彩色图和深度图，统一编码环境光与邻近物体间接光
4. **IterQuery 迭代查询算法**：通过深度引导的迭代收敛（3-5 次迭代）解决多探针视差问题，显著提升折射/反射高频细节
5. **网格-高斯统一**：用透明高斯基元引导 SDF 重建提取显式网格，以网格代理快速追踪二次光线，弥补 3D-GS 光栅化无法处理二次光线的缺陷

## Method

![TransparentGS 管线总览](https://arxiv.org/html/2504.18768v1/x1.png)
*图 1：TransparentGS 整体框架。输入多视角照片 -> SAM2 + GroundingDINO 分割透明物体 -> 透明高斯基元 + 延迟折射 + GaussProbe + IterQuery*

![Transparent Gaussian Primitives 架构](https://arxiv.org/html/2504.18768v1/x2.png)
*图 2：透明高斯基元的参数化。每个高斯存储位置、协方差、不透明度、法线 n、粗糙度 rho、金属度 m、透明度 t、折射率 eta*

![延迟折射 vs 前向折射](https://arxiv.org/html/2504.18768v1/x3.png)
*图 3：延迟折射先 alpha 加权混合所有高斯的法线属性得到单一法线 N，再计算单一折射方向 omega_t 查询探针；前向折射对每个高斯分别计算折射后混合，产生模糊效果*

### 整体架构概览

TransparentGS 的管线分为四个阶段：

1. **场景分割**：SAM2 + GroundingDINO 从多视角 RGB 图像中分割出透明物体和背景
2. **背景重建与探针烘焙**：用原始 3D-GS 重建背景场景，在透明物体包围盒周围的体素中放置虚拟相机，烘焙 360 度全景彩色图和深度图
3. **透明高斯重建**：用透明高斯基元在物理渲染管线中优化透明物体的几何和材质
4. **网格-高斯统一**：每若干步用高斯击中点引导 SDF 重建提取网格，以网格代理追踪二次光线

### 透明高斯基元

**参数化**：在标准 3D-GS 原语（位置 mu、协方差 Sigma、不透明度 o、球谐系数 SH）基础上，显式编码：法线 n、粗糙度 rho、金属度 m、透明度 t、折射率 eta。其中 t 用于在透明和不透明材质间插值。

**渲染方程**：BSDF 分解为反射（BRDF）和透射（BTDF）两部分：

$$f = (1-t)f_r + t f_t$$

其中 $f_r$ 遵循 Cook-Torrance 模型（Schlick 近似 Fresnel 项），$f_t$ 为纯镜面折射（斯涅尔定律）。

**延迟折射（核心创新）**：

前向折射对每个高斯分别计算折射方向后混合，导致多条方向不一致的折射光混成模糊一片。延迟折射的做法是：

1. 对沿视线方向的所有高斯做 alpha 加权混合，得到**混合法线** $N = sum T_i alpha_i n_i$
2. 计算**alpha 加权击中点** $X$，通过解析求解高斯函数沿射线的最大值位置
3. 用混合法线和击中点，通过斯涅尔定律得到**单一折射方向** $omega_t$
4. 用 $omega_t$ 查询 GaussProbe 得到入射辐射度

$$L_t = (1-F)L_{in}(x, omega_t)$$

**有色透明物体**：扩展吸收模型 $L_t = (1-F)L_{in}(x, omega_t)e^{-sigma(lambda)d}$，用可优化的基底颜色 $b_i$ 近似透射率，解耦折射项与物体固有颜色。

### 高斯光场探针（GaussProbe）

**烘焙流程**：

1. 用原始 3D-GS 重建透明物体移除后的背景场景
2. 场景体素化，在透明物体包围盒周围体素中放置探针
3. 对每个探针，用最优投影函数将 3D 高斯投影到单位球切平面，渲染 360 度全景彩色图 $Phi$ 和深度图 $Theta$

**IterQuery 迭代查询**：

直接对 K 个探针沿同一方向查询并平均会导致视差模糊。IterQuery 的迭代过程：

1. 初始化各探针查询方向 $d_i = d$（查询射线方向）
2. 查询深度 $t_i = Theta(p_i, d_i)$，得到探针 i 与场景的交点
3. 三线性插值得到射线上的估计交点距离 $hat{t} = sum w_i((p_i + t_i d_i - o) cdot d)$
4. 更新方向 $d_i := frac{o + hat{t}d - p_i}{||o + hat{t}d - p_i||}$
5. 重复直到 $hat{t}$ 收敛（通常 3-5 次迭代）

### 网格-高斯统一

3D-GS 的光栅化无法处理透明物体内部的二次光线反弹。TransparentGS 的做法：

1. **GS -> Mesh**：用透明高斯基元渲染的击中点图 $X$ 引导 SDF 主射线采样，法线图 $N$ 正则化梯度，提取显式网格
2. **Mesh -> GS**：用提取的网格作为代理进行快速二次光线追踪，查询 GaussProbe 获得内部反弹光

### 优化与损失函数

$$L = (1-lda_1)L_1 + lda_1 L_{D-SSIM} + lda_2 L_{normal} + lda_3 L_{mask}$$

其中 $L_{normal} = 1 - N cdot widehat{N}_{D}$，$lda_1=0.2, lda_2=0.2, lda_3=1$。

## Training

- **优化器**：Adam，基于 3D-GS 实现
- **训练时长**：<1 小时（相比 NeRF 类方法 >7-10 小时，快 20 倍以上）
- **损失权重**：$lda_1=0.2$（L1+D-SSIM），$lda_2=0.2$（法线正则），$lda_3=1$（mask）
- **IterQuery 迭代次数**：5（默认）
- **探针数量**：8 或 64（经验设置）
- **场景分割**：预训练 SAM2 + GroundingDINO（文本提示 + RGB 图像 -> 边界框 -> 分割掩码）
- **多阶段策略**：先烘焙 GaussProbe，再用透明高斯优化几何和材质，定期提取网格追踪二次光线

## Results & Comparisons

### 透明物体重建能力对比（Table 1）

| 方法 | 训练时间 | 渲染 | 环境光 | 邻近物体 | 高频折射 | 反射-折射解耦 | 有色折射 | 重渲染 |
|------|---------|------|--------|---------|---------|-------------|---------|--------|
| Eikonal | >10h | offline | true | true | false | false | false | false |
| NEMTO | >10h | offline | true | false | true | true | false | true |
| NU-NeRF | >7h | offline | true | true | false | true | false | true |
| **TransparentGS** | **<1h** | **real-time** | **true** | **true** | **true** | **true** | **true** | **true** |

TransparentGS 是唯一同时支持全部八项能力的方法。

### 无色透明物体新视角合成（Table 3）

| 场景 | 方法 | PSNR↑ | SSIM↑ | LPIPS↓ |
|------|------|-------|-------|--------|
| Glass | Ours | **27.12** | **0.952** | **0.044** |
| | NU-NeRF | 26.78 | 0.942 | 0.071 |
| | GShader | 26.52 | 0.951 | 0.052 |
| HalfBall | Ours | **28.07** | **0.954** | **0.084** |
| | NU-NeRF | 27.48 | 0.946 | 0.149 |
| Apple | Ours | **23.05** | **0.965** | **0.047** |
| | NU-NeRF | 22.25 | 0.963 | 0.057 |

### 有色透明物体新视角合成（Table 4）

| 场景 | 方法 | PSNR↑ | SSIM↑ | LPIPS↓ |
|------|------|-------|-------|--------|
| Penguin | Ours | **22.09** | 0.832 | **0.255** |
| | NU-NeRF | 22.29 | 0.821 | 0.318 |
| Dolphin | Ours | **22.66** | 0.832 | **0.142** |
| | NU-NeRF | 22.70 | 0.833 | 0.306 |
| Mouse | Ours | **20.37** | 0.695 | **0.154** |
| | NU-NeRF | 19.86 | 0.673 | 0.300 |
| Bird | Ours | 21.09 | **0.830** | **0.136** |
| | NU-NeRF | 21.00 | 0.820 | 0.306 |
| **Average** | **Ours** | **21.55** | **0.797** | **0.172** |
| | NU-NeRF | 21.46 | 0.787 | 0.308 |

### 合成数据集对比（Table 5）

| 方法 | NVP PSNR↑ | NVP SSIM↑ | NLPIPS↓ | 法线 MAE↓ | 反射 PSNR↑ | 折射 PSNR↑ | 基底颜色 PSNR↑ |
|------|----------|----------|---------|----------|-----------|-----------|--------------|
| Ours | **25.66** | **0.935** | **0.064** | **5.53°** | **17.60** | **22.87** | **21.51** |
| GShader | 24.05 | 0.922 | 0.069 | 26.51° | N/A | 13.19 | — |
| NU-NeRF | 22.52 | 0.759 | 0.266 | 16.02° | 13.65 | 19.90 | 17.08 |

### 性能

- 训练时间：<1 小时（vs. NeRF 方法 >7-10 小时）
- 渲染帧率：实时（31-51 FPS，具体取决于场景复杂度）
- 与 GShader、NU-NeRF 等相比，在 PSNR、SSIM、LPIPS 上全面领先

## Related Work Analysis

### 与 NeRF 类透明重建方法的关系

NU-NeRF（Sun et al., 2024）和 Eikonal（Bemana et al., 2022）使用隐式神经场处理折射，但训练缓慢（>7-10 小时），且不支持实时渲染。NU-NeRF 用 MLP 预测折射方向，导致结果过度模糊。TransparentGS 用显式 3D-GS 原语替代 MLP，将训练时间缩短至 1 小时内。

### 与 GShader 的关系

GShader（Jiang et al., 2024）是最早尝试 3D-GS 逆向渲染的工作，但仅支持反射场景，无法处理折射。TransparentGS 通过透明高斯基元和 GaussProbe 扩展了 3D-GS 对折射和间接光的支持。

### 与 NEMTO 的关系

NEMTO（Wang et al., 2023）用 MLP 预测折射方向并假设纯环境光（无邻近物体间接光）。TransparentGS 通过 GaussProbe 统一编码环境光+间接光，通过 IterQuery 解决视差问题。

### 与 TensoIR/NeILF++ 的关系

TensoIR 通过张量分解显式计算射线积分，时间开销大。NeILF++ 用物理渲染处理镜面和反射，但结果过度平滑且训练时间长。TransparentGS 用 GaussProbe 高效编码入射光场。

## Ablations

### 延迟折射 vs 前向折射

前向折射对每个高斯分别计算折射方向后做 alpha 混合，产生多方向模糊效果。延迟折射先混合法线得到单一方向，在高频折射细节上显著更优。

### IterQuery 迭代次数

1 次迭代（等价于直接平均 K 探针）会产生明显视差模糊。2-3 次迭代即可大幅改善，5 次迭代达到稳定。迭代次数与探针数量 K 和深度图分辨率相关。

### 探针数量

8 个探针在大多数场景下足够，64 个探针在复杂间接光场景中有更好效果但增加烘焙时间。

### 网格-高斯统一

仅用 GaussProbe 查询时，透明物体内部二次光线（如空心玻璃杯内壁反射）无法正确模拟。加入网格代理后，可以追踪内部反弹光线到探针，显著提升空心物体效果。

## Limitations

- **复杂多 bounce 光路**：空心透明物体的多次内部反射仍存在歧义
- **依赖分割精度**：SAM2 + GroundingDINO 的分割结果直接影响重建质量，错误分割会导致背景/透明物体混淆
- **环境不可见**：若透明物体后方环境在训练视角中完全不可见，探针无法编码该区域
- **焦散渲染**：方法未专门建模焦散（caustics）效果
- **高斯光线追踪**：未探索高斯体积内的光线追踪，仅依赖网格代理

## 评论与启示

- **延迟折射**是关键设计——3D-GS 的光栅化天然适合"先混合几何属性、后计算着色"的延迟管线，而非传统 3D-GS 的 alpha 混合球谐颜色
- **GaussProbe 的探针烘焙**巧妙地将 3D-GS 的显式表示复用为背景光场编码，避免额外训练 MLP
- **IterQuery 的迭代收敛**在 3-5 步内解决多探针视差，相比 TensoIR 的全局射线积分高效得多
- **网格-高斯统一**是对 SuGaR 思想的逆向应用——SuGaR 用网格监督高斯，TransparentGS 用高斯引导网格
- 与 [[3DGS]]：TransparentGS 在 3D-GS 基础上扩展 BSDF 参数化和延迟折射管线
- 与 [[Ref-DGS]]：同为 3D-GS 逆向渲染扩展，但 Ref-DGS 针对镜面反射，TransparentGS 针对折射+反射+间接光

## Connections

- [[3DGS]] — TransparentGS 的基础表示
- [[Ref-DGS]] — 同为 3D-GS 逆向渲染，但面向镜面反射
- [[NU-NeRF]] — NeRF 类透明物体重建 SOTA，但训练慢且不支持高频折射
- [[GShader]] — 首个 3D-GS 逆向渲染，但不支持折射
- [[SuGaR]] — 网格-高斯统一的先行工作（方向相反）
- [[SAM2]] — 场景分割工具
- [[GroundingDINO]] — 文本引导目标检测

## Contradictions

- 与 NeRF 类方法（NU-NeRF、Eikonal）的训练速度相反：3D-GS 显式表示 + 物理渲染管线在 1 小时内完成，而隐式场方法需要 >7 小时
- 与 GShader 的能力相反：GShader 仅支持反射，TransparentGS 扩展了折射、有色折射和间接光支持
- 与 TensoIR 的效率相反：TensoIR 通过全局射线积分保证可见性但速度慢，GaussProbe + IterQuery 用探针查询近似但速度快 20 倍以上

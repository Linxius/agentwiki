---
title: "Neural Harmonic Textures for High-Quality Primitive Based Neural Reconstruction"
type: source
tags: [paper]
date: 2026-07-29
source_file: raw/digest/sources/2026-07-29/arxiv-260401204-6a516cc9.md
url: "https://arxiv.org/abs/2604.01204"
venue: ""
published: 2026
links: ["https://arxiv.org/html/2604.01204v3"]
---

## Summary

针对 3D 高斯泼溅（[[3D Gaussian Splatting|3DGS]]）等基元式（primitive-based）方法单个基元表达力不足、需用大量基元刻画高频细节的问题，本文提出 **Neural Harmonic Textures（NHT）**：在每个基元外围的虚拟支架上锚定可学习特征，在光线与基元交点处插值并经正弦/余弦周期激活，将 alpha 混合转化为谐波分量的加权和，最后用一个小 MLP 在延迟着色（deferred shading）阶段单次解码出像素颜色。该表示与基元类型无关，可无缝接入 3DGUT、Triangle Splatting、2DGS 等现有管线，在实时与离线新视角合成基准上均取得 SOTA，并扩展到语义重建与 2D 图像拟合。

## 原始出处

- 原始文件: [arxiv-260401204-6a516cc9.md](../../raw/digest/sources/2026-07-29/arxiv-260401204-6a516cc9.md)
- 原文链接: [https://arxiv.org/abs/2604.01204](https://arxiv.org/abs/2604.01204)
- Brief 条目: [2026-07-29 > Neural Harmonic Textures](../../raw/digest/brief.md)
- 深度阅读报告: 无

## Key Contributions

- **基元绑定特征嵌入（Primitive-bound feature embedding）**：把可学习特征向量锚定在每个基元（高斯/三角形）外包的虚拟四面体支架顶点上，沿射线在最大响应点处做重心插值，使特征随基元运动/形变/编辑自然移动。
- **谐波纹理（Harmonic Texturing）**：对插值后的特征施加 sin/cos 周期激活，受傅里叶分析启发将 alpha 混合改写为谐波分量的加权和；基元的不透明度充当谐波振幅，使单基元内部也能表达空间变化的高频外观。
- **神经延迟着色（Neural Deferred Shading）**：将累积谐波与射线方向（二阶球谐）拼接，用一个轻量 MLP 在图像空间单次解码像素颜色，避免逐基元多次神经网络求值。
- **与基元类型无关**：三角形、2D/3D 高斯、四面体等可互换，即插即用到 3DGUT、Triangle Splatting、2DGS 等现有 3DGS 管线。
- **在 MipNeRF360 / Tanks & Temples / Deep Blending 上取得 SOTA**，尤其在镜面高光、反射等高分辨率和大视差场景下；并以更低基元数达到此前方法的质量（低基元数区间优势明显）。
- **扩展到更高维信号**：统一局部表示同时建模颜色与语义特征，支持 2D 图像拟合与语义重建。

## Method

![Neural Harmonic Textures 方法概览](https://arxiv.org/html/2604.01204v3/x2.png)

**图 2**：方法总览——在基元外包虚拟支架锚定顶点特征，于光线交点插值并经周期激活后沿射线谐波合成，最后由轻量 MLP 延迟解码。

### 整体架构概览

3DGS 等 Lagrangian 基元式方法渲染快、易编辑、可扩展到大场景，但单个基元的表达力有限：几何与外观被紧耦合在每个基元内，高频空间细节与视相关效果（镜面高光等）只能靠堆砌基元来刻画，直接推高显存与渲染开销。神经辐射场（[[Neural Radiance Field|NeRF]]）类方法凭借位置编码/哈希网格 + MLP 拥有高局部表达力，但牺牲了显式性、运动/编辑友好性与可扩展性。

NHT 的核心思路是**把基元同时当作几何载体与局部位置编码**：在每个基元周围挂一组可学习特征，并用周期函数激活，使"纹理"在基元内部高频变化而不增加基元数量。整体分三步。

### 组件 A：基元绑定特征嵌入

- **直觉**：全局规则网格（triplane、哈希网格）把特征锚定在空间固定位置，难以随场景运动/形变，且大场景扩展性差。基元本身是显式、随物体移动的，因此把特征"绑"在基元上更自然。
- **细节**：对每个各向异性 3D 高斯基元，取其各向同性球在规范空间内的包围四面体，在四个顶点各挂一个特征向量 $\mathbf{f}^{j}\in\mathbb{R}^{N_f}$（$j\in\{0..3\}$）。对射线相交的基元，取沿射线高斯响应最大的点 $\mathbf{p}^{*}$（3DGUT 定义），用重心插值得到该处特征 $\mathbf{f}$：$\mathbf{f}=\text{interpolate}([\mathbf{f}^{0},\mathbf{f}^{1},\mathbf{f}^{2},\mathbf{f}^{3}],\mathbf{p}^{*})$。该特征随基元移动，天然支持运动、形变、删除等编辑。

### 组件 B：谐波纹理（Harmonic Texturing）

![Harmonic Textures](https://arxiv.org/html/2604.01204v3/x5.png)

**图 4**：谐波纹理示意——插值特征经 sin/cos 调制后沿射线混合，单基元内部即可呈现空间变化的高频纹理。

- **直觉**：此前方法在体积渲染"之前"用轻量 MLP 解码每个基元外观，每条射线需数十次 MLP 求值；3DGS 为降开销只在每个基元近似一次视相关颜色，但假设基元内部信号不随空间变化，无法表达高频外观。NHT 借鉴延迟着色，把特征沿射线混合后在图像空间解码。
- **细节**：受傅里叶变换启发（信号 = 不同振幅的周期函数之和），在沿射线混合前对插值特征施加周期函数（正弦/余弦）。激活后的特征等价于频率分量，基元不透明度 $\alpha_i$ 调制其振幅。插值函数在此等价于**频率调制器**：同一基元内顶点特征差异越大，纹理振荡越快、空间变化越剧烈。

### 组件 C：神经延迟着色（Neural Deferred Shading）

- **直觉**：谐波纹理产出的高维信号足够丰富，无需逐基元解码，可在图像空间用一次 MLP 求值完成最终着色，类似图形学中的延迟着色。
- **细节**：将累积谐波与射线方向 $\mathbf{d}$（二阶球谐 $\mathrm{SH}_2(\mathbf{d})\in\mathbb{R}^9$，同 hashgrid 方案）拼接，用小 MLP 解码像素颜色 $\mathbf{c}$，无需额外位置编码。渲染方程：

$$\mathbf{c}=\mathrm{MLP}_{\theta}\left(\sum_{i\in\mathcal{G}}\alpha_{i}\,T_{i}\begin{bmatrix}\sin(\mathbf{f}_{i})\\ \cos(\mathbf{f}_{i})\end{bmatrix},\;k\cdot\mathrm{SH}_{2}(\mathbf{d})\right)$$

其中 $\mathcal{G}$ 为射线相交的基元集合，$\alpha_i$、$T_i$ 为基元不透明度与累积透射率，$\mathbf{f}_i$ 为最大响应点处的插值特征。

## Training

- **损失与正则**：直接沿用 3DGS-MCMC 的稠密化策略、损失与正则项，含基元不透明度/尺度正则 $\mathcal{R}_{\alpha}=\frac{1}{P}\sum_i\alpha_i$、$\mathcal{R}_{s}=\frac{1}{P}\sum_i\lVert\mathbf{s}_i\rVert_1$。最终损失 $\mathcal{L}=(1-\lambda)\mathcal{L}_{L_1}+\lambda\mathcal{L}_{D\text{-}SSIM}+\lambda_\alpha\mathcal{R}_\alpha+\lambda_s\mathcal{R}_s$。
- **调度**：对特征与 MLP 学习率采用余弦退火（类比 3DGS 对位置的学习率指数调度）；对 MLP 权重 $\theta$ 施加 EMA 滤波（$\bar{\theta}_t\leftarrow\gamma\bar{\theta}_{t-1}+(1-\gamma)\theta_t$）以增强鲁棒性、抑制对单帧过拟合。
- **精修阶段**：最后 3000 次迭代仅优化特征与 MLP 权重，关闭所有正则并冻结其余参数，略微提升颜色保真度（尤其大场景）。
- **实现**：基于 *gsplat* + 3DGUT 公式实现，新增前向/反向自定义 CUDA kernel；光栅化时对特征向量用半精度内存读取降低寄存器压力；MLP 用 tiny-cuda-nn 的 JIT 协作向量 MLP，FP16 训练；对损失加自动缩放因子提升半精度稳定性。

## Results & Comparisons

在 MipNeRF360、Tanks & Temples、Deep Blending 上与纯神经场（Mip-NeRF 360、ZipNeRF）、哈希网格神经场（Instant NGP）、纯基元方法（2DGS、3DGS-MCMC、3DGUT、Beta Splatting、Triangle Splatting，配 SH 或更复杂外观模型如 [[Spherical Voronoi|SV]]、Textured Gaussians）、以及混合方法（NeST、Radiance Meshes）全面对比。

**表 1（原始 JPEG 参考，MipNeRF360 不降采样）关键结果：**

| 方法 | MipNeRF360 PSNR | T&T PSNR | DeepBlending PSNR |
| --- | --- | --- | --- |
| 3DGS-MCMC | 27.99 | 24.46 | 29.49 |
| 3DGUT-MCMC | 27.82 | 24.20 | 29.87 |
| Spherical Voronoi | 28.56 | 24.80 | 30.34 |
| **Neural Harmonic Textures (Ours)** | **28.74** | **25.68** | **30.94** |

NHT 在三项基准 PSNR 均居首，LPIPS 亦最优（MipNeRF360 0.216、T&T 0.141），尤其擅长高频细节、镜面高光与反射。

**表 2（受控实验，同框架 gsplat、1M 基元、30k 迭代、同参数量）隔离外观模型影响：**

| 方法 | MipNeRF360 PSNR / FPS | T&T PSNR / FPS | DeepBlending PSNR / FPS |
| --- | --- | --- | --- |
| 3DGS + SH | 27.94 / 251 | 24.25 / 294 | 29.98 / 331 |
| 3DGUT + SH | 27.93 / 201 | 23.99 / 245 | 30.21 / 282 |
| 3DGUT + SV | 28.15 / 202 | 24.18 / 242 | 30.29 / 267 |
| **3DGUT + NHT (Ours)** | **28.46 / 140** | **24.79 / 226** | **30.88 / 240** |

NHT 在所有基准优于 SH 与 SV，且占用更少存储；推理仍可实时（MipNeRF360 140+ FPS），但因额外神经解码器比纯 3DGS 略慢（见 Limitations）。

**表 3（泛化性）**：将 NHT 接入 Triangle Splatting（27.00→27.52）、2DGS（27.48→28.27）、3DGUT-MCMC（27.93→28.46）均带来一致提升。

训练效率：MipNeRF360 上约 14.5 分钟训到 30k 迭代（1M 基元，RTX 5090）。

## Related Work Analysis

- **与 Spherical Voronoi（SV）**：SV 用可微球面 Voronoi 划分替代 SH 作为 3DGS 外观表示，解决 SH 高频受限与 ringing 问题；NHT 则从"基元作为局部位置编码 + 周期激活"角度切入，把外观解码放到延迟着色阶段的单次 MLP。两者都试图突破 SH 表达瓶颈，但 NHT 额外将几何（特征锚定）与高频外观统一在同一显式基元上，并保留运动/编辑友好性。表 2 显示 NHT 在相同设定下 PSNR 优于 SV。
- **与 Textured Gaussians / NeST / Radiance Meshes（混合基元+神经场）**：这类方法用基元做加速、用神经场补表达。NHT 不引入独立神经场，而是把特征直接绑在基元上、用谐波+轻 MLP 解码，结构更简洁、更显式。
- **与 3DGS-MCMC / 3DGUT / Beta Splatting**：这些是基元式骨架，NHT 作为可插拔的外观/表达增强叠加其上，不改变几何优化流程。

## Ablations

- **基元数量（1K–4M）**：NHT 在整个区间均优于此前方法，且在低基元数区间优势最大——仅用 1/3 基元数即可达到此前方法约 1M 基元的质量（bonsai 仅 10K 基元时平均 +3.7 dB PSNR），在显存-速度-质量权衡上更灵活。
- **特征编码**：补充实验表明选用谐波（sin/cos）函数作为插值特征的编码在结果上最优。
- **优化策略**：学习率调度、MLP 权重 EMA、损失缩放、颜色精修阶段、不透明度/尺度正则各自贡献（非叠加）均在补充表中隔离验证。
- **特征维度与 MLP 架构**：改变每基元特征维度与 MLP 规模呈现明确的质量-速度权衡。

## Limitations

- **稀疏监督下易过拟合**：在监督极稀疏的场景中，NHT 可能过拟合到单视角，导致新视角合成质量下降。
- **推理略慢于纯 3DGS**：额外神经解码器使渲染比纯 3DGS 方法稍慢（但仍保持 140+ FPS 实时），是以少量算力换取高表达力的代价。

## 评论与启示

NHT 的洞见在于把"基元"重新理解为**几何载体 + 局部傅里叶式位置编码**：不是给每个基元配一个全局 MLP 解码 RGB，而是让特征随基元移动、用周期激活在基元内部产生高频变化，再用一次延迟着色 MLP 收口。这既保留了 Lagrangian 显式表示的编辑/运动优势，又逼近了神经场的局部表达力，且实现上只需在现有 3DGS 光栅化里加少量 CUDA kernel。对大规模/实时 3DGS 落地（机器人、AR/VR、数字孪生）有直接价值：同样画质下可用更少基元、更低显存。

## Connections

- 与 [[3D Gaussian Splatting]]、[[Spherical Voronoi]]、[[2DGS]]、[[Triangle Splatting]]、3DGUT、Beta Splatting 构成"基元式重建+外观表示"技术族。
- 与 [[Neural Radiance Field]] / 哈希网格 的位置编码思想同源（用周期/傅里叶基提升高频表达）。
- 与延迟着色（deferred shading）、SNERG 等"先累积再图像空间解码"的渲染范式一致。
- 应用面延伸至语义重建、2D 图像拟合、未来可能的辐射缓存 / 神经 PBR / 几何重建。

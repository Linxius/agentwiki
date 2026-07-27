---
title: "Toward Richer Material Generation via Procedural Data Enhancement"
type: source
tags: [paper, material-generation, neural-material, pbr, brdf, diffusion]
date: 2026-07-28
source_file: raw/papers/Toward-Richer-Material-Generation-via-Procedural-Data-Enhancement.md
url: https://arxiv.org/abs/2606.14988
venue: arXiv
published: 2026
links:
  - https://arxiv.org/abs/2606.14988
---

## Summary

本文提出一种通过程序化数据增强来提升简单 PBR 材质表达能力的方法。核心思路是将简单的单瓣 GGX 高光 BRDF 扩展为多层模型（core + haze + decorator lobes），然后将增强后的 BRDF 压缩到 6 维神经材质隐空间，最后利用视频扩散模型在 3D 物体上生成神经材质。该方法解决了生成材质训练数据表达力不足的根本问题。

## 原始出处

arXiv: 2606.14988, Yunchen Yu, Jacob Munkberg, Jon Hasselgren, Chris Cummings, Steve Marschner, Andrea Weidlich (Cornell University & NVIDIA)

## Key Contributions

1. **程序化材质增强**：将简单的 PBR 材质（Diffuse + 单瓣 GGX）自动提升为包含 8 种非漫射分层的丰富材质模型
2. **神经材质压缩**：将 22 参数的增强 BRDF 压缩到 6D 隐空间（2xRGB 纹理），使用 Universal MLP 编解码器
3. **隐空间正则化**：通过随机填充（infill class）和隐编码抖动（latent jittering）获得平滑的生成友好隐空间
4. **扩散模型材质生成**：利用 Cosmos 视频扩散模型，在 3D 物体上生成神经材质纹理（CLIP-FID 3.907）
5. **微尺度增强**：结合 Simplex noise 实现色彩闪烁效果

## Method

![材质增强管线——程序化规则将简单 PBR 材质提升为多层 BRDF，再通过通用 MLP 编解码器压缩为 6D 神经材质](https://arxiv.org/html/2606.14988v1/x2.png)

### 整体思路

论文的核心观察是：现有的 PBR 材质生成模型受限于训练数据的表达力——简单的 Diffuse + 单瓣 GGX 不足以捕捉真实世界丰富的视觉效果。作者的解决方案分为三步：

1. **增强**：用程序化方法将简单 PBR 自动提升为包含 haze、dust、clearcoat、subsurface scattering 等的多层 BRDF
2. **压缩**：将 22 参数的多层 BRDF 通过神经材质编解码器压缩到 6D 隐空间
3. **生成**：用视频扩散模型在已知几何上生成神经材质隐空间纹理

### 程序化材质增强

广义非漫射反射模型包含 8 个可选的 lobe：
- Core GGX：保留原始粗糙度特征的 dielectric 或 conductive GGX
- Haze：辉光瓣，更宽更亮的高光（q<2, s>1）
- Dust/Fuzz：灰尘/绒毛层
- Clearcoat：透明涂层
- Inner/Sub-scatter：内部和次表面散射（仅介质材质）

Type 0-5 共 6 种增强类型，核心参数：
alpha_core = r^p, alpha_haze = s * r^q

### 神经材质表示

Universal MLP 编解码器：
- 4 层隐藏层 x 64 神经元，指数激活函数
- 输入：6D 隐向量 + 方向对 (omega_i, omega_o)
- 输出：BRDF 值 f_neu + 传输反照率 T_neu + 亮度反射率 R_neu

组合 BRDF：
f(omega_i,omega_o) = f_neu(omega_i,omega_o) + T_neu(omega_i) * c/pi

训练数据：5 个材质类 x 8192x8192 参数网格（约 3.35 亿材质样本）

隐空间正则化：
- Infill class（20%）填充隐空间未覆盖区域
- Latent jittering (+/-0.005) 提高扰动的鲁棒性

逐材质优化损失：
L = 0.95*||f_neu - f_ref||_1 + 0.04*||T_neu - T_ref||_1 + 0.01*||R_neu - R_ref||_1

### 扩散模型材质生成

使用 Cosmos-1.0-Diffusion-7B-Video2World，以 3D 模型的多视角法线、世界坐标和底色作为条件，生成 6 通道神经材质纹理。

数据集：10,640 个 Objaverse + BlenderVault 3D 模型

生成流程：
1. VAE 编码条件几何信息和神经材质纹理
2. DiT 去噪生成神经材质隐空间帧
3. 通过 texture splatting 反投影到 UV 空间

## Training

- Universal MLP：约 3.35 亿材质样本
- 逐材质优化：80x L40/L40S GPU x 22 小时
- 扩散模型微调：64x A100 GPU x 20K iterations，AdamW，lr=5e-5

## Results & Comparisons

| Method | CLIP-FID | CMMD | LPIPS | PSNR |
|--------|----------|------|-------|------|
| TRELLIS.2 | 8.642 | 0.132 | 0.0510 | 24.54 |
| Ours (trellis base) | 6.527 | 0.058 | 0.0444 | 28.28 |
| Ours (ref base) | **3.907** | **0.020** | **0.0215** | **32.53** |

## Related Work Analysis

- **Procedural Enhancement**：首次将程序化增强用于材质生成训练数据
- **Neural Materials**：基于 Zeltner 等的实时神经外观模型
- **Diffusion Models**：利用 Cosmos 视频扩散模型的时序一致性

## Ablations

- 物理信息偏置 vs 随机训练数据：偏置数据显著降低 FLIP 误差
- Infill class + Latent jittering 消除约 50% 生成无效材质
- BRDF loss 权重主导（0.95）

## Limitations

1. 视频扩散模型分辨率限制导致高频细节被平滑
2. 白炉测试约 90% 通过率
3. 空间变化 mask 依赖预定义纹理
4. 多瓣模型仅覆盖选定视觉效果子集

## Connections

- [[NeuralMaterial]]：本文代表神经材质方向最新进展
- [[PBR]]：基于 PBR 材质框架扩展
- [[DiffusionModels]]：使用 Cosmos 视频扩散模型

## Contradictions

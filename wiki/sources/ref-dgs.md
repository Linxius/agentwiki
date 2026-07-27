---
title: "Ref-DGS: Reflective Dual Gaussian Splatting"
type: source
tags: [paper]
date: 2026-07-28
source_file: raw/papers/arxiv-260307664-8748a994.md
url: "https://arxiv.org/abs/2603.07664"
venue: ""
published: 2026
links: []
---

## Summary

本文提出 Ref-DGS，一个反射性双高斯溅射框架，通过解耦表面重建与镜面反射，在基于光栅化的高效管线中处理近场镜面反射。核心创新在于**双高斯场景表示**：几何高斯（$\mathcal{G}_{\mathrm{geo}}$）捕捉视角无关的场景结构和漫反射颜色，局部反射高斯（$\mathcal{G}_{\mathrm{local}}$）捕捉近场镜面交互。远场镜面反射通过可学习球面特征图的 Sph-Mip 编码建模。轻量级物理感知镜面自适应混合着色器融合全局和局部镜面特征，在保持光栅化效率的同时实现高质量镜面渲染。实验表明 Ref-DGS 在反射场景表面重建和新视角合成上达到 SOTA，训练速度显著快于基于光线追踪的 Gaussian 方法（ShinySynthetic 上法线 MAE 1.43，76 FPS）。

## 原始出处

- 原始文件: [raw/papers/arxiv-260307664-8748a994.md](../../raw/papers/arxiv-260307664-8748a994.md)
- 原文链接: [https://arxiv.org/abs/2603.07664](https://arxiv.org/abs/2603.07664)

## Key Contributions

1. **双高斯场景表示**：将几何与近场镜面反射解耦到两组互补高斯中，避免镜面反射被错误吸收进几何表示
2. **全局-局部镜面特征**：远场环境光照（Sph-Mip）与近场局部反射高斯双组件建模
3. **物理感知镜面自适应混合着色器**：基于材质粗糙度和几何角度因子融合全局/局部特征

## Method

![Ref-DGS 框架总览](images/ref-dgs/fig2.png)

### 整体思路

反射表面（尤其是近场镜面反射）违反了多视角一致性假设，使 Gaussian Splatting 在反射场景中几何重建不稳定。现有方法要么无法建模近场镜面（Ref-GS），要么依赖昂贵光线追踪（Ref-Gaussian, EnvGS）。Ref-DGS 的核心洞察是：**镜面反射不应作为几何属性处理**。通过引入第二组专门建模近场反射的高斯，将视角相关的反射效果与几何完全解耦，在光栅化管线内实现高效高质量的反射渲染。

### 双高斯场景表示

**几何高斯 $\mathcal{G}_{\mathrm{geo}}$**：基于 [[2D Gaussian Splatting (2DGS)]]，每个表面原语由 3D 中心 $\mathbf{p}_k$、不透明度 $\alpha_k$、旋转矩阵 $\mathbf{R}_k$ 和缩放矩阵 $\mathbf{S}_k$ 参数化。扩展存储漫射颜色和表面粗糙度等材质属性。光栅化时产生屏幕空间漫射图 $\mathbf{C}_{\mathrm{diff}}(\mathbf{p})$、粗糙度 $\rho(\mathbf{p})$、深度和法线。

**局部反射高斯 $\mathcal{G}_{\mathrm{local}}$**：每个原语存储可学习局部镜面特征 $\mathbf{f}\in\mathbb{R}^d$，光栅化产生屏幕空间特征图 $\mathbf{F}_{\mathrm{local}}(\mathbf{p})$。这些高斯**不影响几何重建**，仅捕捉近场自反射和互反射。物理原理：根据镜面反射定律，虚像位于反射表面后方，$\mathcal{G}_{\mathrm{local}}$ 的法线图展现出从物理表面向内延伸的凹面结构，显式建模虚拟反射几何。

### 全局-局部镜面特征

**远场全局镜面（Sph-Mip）**：类似 [[Ref-GS]]，使用可学习球面特征图 $\mathbf{M}$。基于反射方向 $\mathbf{r}$（由法线和视线计算）和粗糙度 $\rho$ 选择 mipmap 层级，查询得到 $\mathbf{F}_{\mathrm{global}}(\mathbf{p})$。

$$\mathbf{F}_{\mathrm{global}}(\mathbf{p})=\mathrm{Sph\text{-}Mip}\big(\mathbf{x}(\mathbf{r}),\;\ell(\rho(\mathbf{p})),\;\mathbf{M}\big)$$

**近场局部镜面**：从 $\mathcal{G}_{\mathrm{local}}$ 渲染得到 $\mathbf{F}_{\mathrm{local}}(\mathbf{p})$。

### 物理感知镜面自适应混合着色器

轻量级 MLP $f_\Theta$（3 层隐藏层，宽度 64）融合全局和局部特征：

$$\mathbf{C}_{\mathrm{spec}}(\mathbf{p})=f_\Theta\big(\mathbf{F}_{\mathrm{global}}(\mathbf{p}),\;\mathbf{F}_{\mathrm{local}}(\mathbf{p}),\;\rho(\mathbf{p}),\;\cos_{NV}\big)$$

其中 $\cos_{NV}=\max(\mathbf{n}\cdot\mathbf{v},0)$。最终颜色：$\mathbf{C}(\mathbf{p})=\mathbf{C}_{\mathrm{diff}}(\mathbf{p})+\mathbf{C}_{\mathrm{spec}}(\mathbf{p})$。

## Training

双组高斯联合优化，采用与 2DGS 相同的优化和致密化策略。Sph-Mip 使用 $H_{\mathbf{M}}=512$、$W_{\mathbf{M}}=1024$、特征维度 $d=4$、$N=9$ 层 mipmap。所有实验在单张 RTX 4090 上运行。ShinySynthetic 数据集平均训练时间 12.6 分钟。

## Results & Comparisons

| 方法 | 类型 | 训练时间 (ShinySynthetic) | 法线 MAE (ShinySynthetic) | FPS |
|-----|------|--------------------------|--------------------------|-----|
| Ours | 光栅化 | **12.6m** | **1.43** | **76.34** |
| Ref-GS | 光栅化 | 23.5m | 2.21 | 67.63 |
| MaterialRefGS | 光线追踪 | 2.42h | 2.20 | 30.07 |
| EnvGS | 光线追踪 | — | — | 26.22 |

**表面重建**：在 GlossySynthetic 数据集上 Chamfer Distance 0.62×10²（最佳），法线 MAE 1.88（最佳）。在 RefReal 真实数据集上仍保持领先。

**新视角合成**：ShinySynthetic PSNR 35.21、SSIM 0.975、LPIPS 0.053，全面超越所有基线。

## Related Work Analysis

与 [[NeRFReN]] 的关键差异：NeRFReN 假设平面镜反射，需要反射分数图的额外监督；Ref-DGS 的 $\mathcal{G}_{\mathrm{local}}$ 建模一般近场镜面，无需额外标注。

与 [[Ref-GS]] 的差异：Ref-GS 将视角相关效果编码进单组高斯的空间特征 $\mathbf{K}$，导致几何-外观纠缠；Ref-DGS 通过双高斯显式解耦。

## Ablations

- **无局部特征 + 无 $\mathcal{G}_{\mathrm{local}}$**：近场镜面被吸收进漫射分量，PSNR 下降 0.85dB，法线 MAE 升至 1.53
- **无双高斯（单组高斯）**：特征从 $\mathcal{G}_{\mathrm{geo}}$ 导出，几何质量下降（法线 MAE 1.46）
- **无自适应混合（直接求和）**：新视角泛化不稳定
- **无物理感知条件**：轻微退化

## Limitations

- 依赖多视角校准图像
- 对极度复杂光路（如多次折射）仍有挑战
- 场景规模受单 GPU 显存限制

## Connections

- [[2D Gaussian Splatting (2DGS)]] — 基础几何表示
- [[Ref-GS]] — 远场镜面建模的基线方法
- [[3D Gaussian Splatting (3DGS)]] — 可微光栅化框架
- [[NeRFReN]] — 反射场景分解方法
- [[NovelViewSynthesis]] — 新视角合成任务

## Contradictions

- 与 Ref-GS 在是否需要显式近场建模上存在根本分歧：Ref-GS 认为单组高斯+环境映射足够，Ref-DGS 证明需要双高斯解耦
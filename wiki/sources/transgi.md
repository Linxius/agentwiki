---
title: "TransGI: Real-Time Dynamic Global Illumination With Object-Centric Neural Transfer Model"
type: source
tags: [paper]
date: 2026-07-28
source_file: raw/papers/TransGI-Real-Time-Dynamic-Global-Illumination-With-Object-Centric-Neural-Transfer-Model.md
url: "https://arxiv.org/abs/2506.09909"
venue: ""
published: 2025
links: []
---

## Summary

本文提出 TransGI，一种面向实时高保真全局光照的神经渲染方法。核心由两部分组成：**以物体为中心的神经迁移模型**（Object-Centric Neural Transfer Model）用于材质表示，和**辐射度共享光照系统**（Radiance-Sharing Lighting System）用于高效照明。神经迁移模型通过 MLP 解码器和顶点附加潜变量（vertex-attached latent features）实现紧凑且有表达力的材质表示，支持光泽效果且内存开销低。辐射度共享系统采用局部光照探针与跨探针辐射度共享策略，实时生成高质量动态照明。在 Falcor 渲染引擎中实现，单帧渲染 <10ms，显著优于 [[DDGI]] 基线。

## 原始出处

- 原始文件: [raw/papers/TransGI-Real-Time-Dynamic-Global-Illumination-With-Object-Centric-Neural-Transfer-Model.md](../../raw/papers/TransGI-Real-Time-Dynamic-Global-Illumination-With-Object-Centric-Neural-Transfer-Model.md)
- 原文链接: [https://arxiv.org/abs/2506.09909](https://arxiv.org/abs/2506.09909)

## Key Contributions

1. **以物体为中心的神经迁移模型**：基于顶点潜变量 + MLP 解码器，压缩稠密采样的物体迁移函数，内存 <1MB + 每顶点 1D 向量
2. **跨探针辐射度共享策略**：探针间共享光线能量，将生成高分辨率辐照度图的计算与探针数量解耦
3. **实时实现**：Falcor 引擎中集成 CUDA 神经网络和计算着色器，支持物体移动/旋转/增删

## Method

![TransGI 管线总览](images/transgi/fig2.png)

### 整体思路

实时全局光照面临两难：传统 [[PRT]]（预计算辐射度传输）速度快但假设远距离光照、静态场景；[[DDGI]] 支持动态但仅限漫反射材质。TransGI 的核心洞察：**将 PRT 的传输函数从场景级压缩到物体级**，用神经网络和顶点潜变量表示，从而支持物体级别的动态操作。

TransGI 将渲染分解为两个独立流程：
1. **传输系数解码**：神经网络输出材质传输系数 $t_k(x_o, \omega_o)$，编码了材质对光的频率域响应
2. **光照系数生成**：光照探针实时捕获场景辐射度，投影到球谐基得到 $l_k(x_o, \omega_o)$

最终颜色为传输系数与光照系数的点积。

### 以物体为中心的神经迁移模型

**顶点潜变量**：每个顶点附加 $d$ 维向量 $z(i)$，编码该顶点的传输属性。查询时用重心坐标插值：
$$z(x_0)=\lambda_1 z(i_1)+\lambda_2 z(i_2)+\lambda_3 z(i_3)$$

**神经传输解码器** $\Phi$：Fullyfused MLP（3 层隐藏层 × 128 维），输入插值后的潜变量 + 出射方向 + 法线 + 反照率，输出 75 维球谐系数（4阶，$(L+1)^2=25$ 通道 × 3 颜色分量）：
$$t_{0-K}(x_o,\omega_o)=\Phi(z(x_o),\omega_o,n,\alpha)$$

**数据采集与训练**：
1. 在物体表面均匀采样位置和出射方向（40,960,000 点/场景）
2. 对每个样本，用 2000 个入射方向 Monte Carlo 积分计算 GT 传输系数
3. 联合优化顶点潜变量和解码器，L1 损失

### 辐射度共享光照系统

**SH 光照探针**：场景中放置 $8\times8\times8$ 个探针，每个探针存储投影到球谐基的光照系数。

**跨探针辐射度共享**：
1. 每个探针发射 $M=100$ 条光线，计算着色点位置和辐射度颜色
2. 每个探针用自己的 $M$ 个着色点 + 最近 26 个探针的 $M$ 个着色点进行原子式点云光栅化，生成辐照度图
3. 辐照度图投影为球谐光照系数

传统方法中辐照度图分辨率与光线数线性相关；本策略通过共享将二者解耦。

**探针插值**：三线性插值 8 个最近探针，结合 DDGI 风格的剪枝避免光/阴影泄露。

## Results & Comparisons

**场景级 GI**（Bitterli 数据集）：
| 场景 | 指标 | Ours | DDGI |
|-----|------|------|------|
| Bathroom | RMSE | **0.108** | 0.282 |
| Dining Room | RMSE | **0.033** | 0.061 |
| Living Room | RMSE | **0.069** | 0.185 |

**效率**：单帧 6.7ms（<10ms 实时），DDGI 1.7ms。内存占用 <50MB（含 80 万顶点场景）。

**物体级光泽效果**：能正确表现金属茶壶、水壶、光泽罐子的镜面反射，与路径追踪参考接近。

**动态支持**：物体平移/旋转/增删后 GI 保持物理合理。

## Related Work Analysis

与 [[DDGI]] 的关键差异：DDGI 仅支持漫反射材质，无法表现光泽反射；TransGI 的神经迁移模型支持复杂材质（Disney BSDF 甚至测量数据），RMSE 降低 50-70%。

与 [[Neural-PRT]] 的差异：Neural-PRT 是场景级拟合，不支持物体动态；TransGI 以物体为中心，支持物体变换。

与 [[NRC]] 的差异：NRC 单个 MLP 缓存辐射度，受限于样本数会产生噪点；TransGI 用 PRT 公式避免采样噪声。

## Ablations

- **传输系数质量**：预测系数与 GT 高度一致，误差主要集中在高频光泽表面
- **跨探针辐射度共享**：与独立探针生成比较，低阶球谐 ($\ell=1$) 几乎无差异，高阶 ($\ell=2$) 有轻微精度损失
- **探针剪枝**：严格剪枝有效避免光/阴影泄露，DDGI 中明显可见的边缘泄露被消除

## Limitations

- 目前仅支持刚性变换，不支持布料等非刚性变形
- 预计算传输系数需要离线训练（~2 小时/场景）
- 跨探针辐射度共享在高阶球谐上有精度损失
- 相比 DDGI 慢约 4 倍（1.7ms vs 6.7ms），但仍满足实时需求

## Connections

- [[DDGI]] — 动态漫反射全局光照基线方法
- [[Precomputed Radiance Transfer (PRT)]] — 理论基础
- [[Neural-PRT]] — 用神经网络编码辐射度传输
- [[Spherical Harmonics]] — 光照和传输系数的基函数
- [[Tiny-CUDA-NN]] — 神经网络实现框架

## Contradictions

- 与 DDGI 在是否需要支持光泽材质上立场不同：DDGI 认为简单漫反射足够实时渲染，TransGI 证明光泽材质可在 <10ms 内实时渲染
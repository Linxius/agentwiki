---
title: "SDFRaster: Distance Field Rasterization for End-to-End Mesh Reconstruction"
type: source
tags: [paper, mesh-reconstruction, sdf, rasterization, marching-tetrahedra, neural-sdf]
date: 2026-07-30
source_file: raw/papers/Distance-Field-Rasterization-for-End-to-End-Mesh-Reconstruction.md
url: "https://arxiv.org/abs/2604.23537"
venue: ""
published: 2026
links: []
---

## Summary

SDFRaster 提出一种**基于距离场光栅化的端到端网格重建**方法。核心思想是将 SDF（有符号距离场）用四面体网格承载，通过**光栅化四面体**而非沿光线密集采样的方式渲染深度/法线，结合可微分 Marching Tetrahedra 在训练中直接提取网格，并用网格渲染深度/法线与 SDF 渲染结果的一致性损失来监督 SDF 优化。训练时间仅需 98 分钟（DTU），远低于 NeuS/VolSDF/Neuralangelo 等隐式 SDF 方法（均超过 12 小时），同时在网格质量上保持竞争力。

## 原始出处

- 原始文件: [raw/papers/Distance-Field-Rasterization-for-End-to-End-Mesh-Reconstruction.md](../../raw/papers/Distance-Field-Rasterization-for-End-to-End-Mesh-Reconstruction.md)
- 原文链接: [https://arxiv.org/abs/2604.23537](https://arxiv.org/abs/2604.23537)
- Brief 条目: [brief.md 2026-07-29 > Distance Field Rasterization for End-to-End Mesh Reconstruction](../../raw/digest/brief.md)

## Key Contributions

1. **四面体 SDF 表示**：用 Delaunay 四面体网格承载分段线性 SDF，结合多分辨率哈希编码的 MLP 预测顶点 SDF 值，实现连续且可微的距离场
2. **距离场光栅化**：直接光栅化四面体而非沿光线密集采样，用 NeuS 风格的 alpha 混合将 SDF 转化为透明度，GPU 高效实现
3. **端到端可微网格提取**：训练中嵌入可微分 Marching Tetrahedra 实时提取网格，用网格渲染深度/法线与 SDF 渲染的一致性损失形成紧耦合优化环路
4. **自适应四面体细化**：每隔 500 步在表面附近插入新顶点并重新四面体化，同时剪掉贡献小的四面体和顶点，最终导出网格体积约为 TSDF 融合的 1/3

## Method

![SDFRaster 总览](https://arxiv.org/html/2604.23537v1/x2.png)
*图 1：SDFRaster 将 SDF 承载于四面体网格，通过光栅化渲染距离场，同时用 Marching Tetrahedra 提取网格并回传一致性损失*

![SDFRaster 自适应细化](https://arxiv.org/html/2604.23537v1/x3.png)
*图 3：四面体网格的自适应细化——在表面穿过的四面体中插入新顶点，重新四面体化后将分辨率集中在表面附近*

### 整体架构概览

SDFRaster 解决的核心问题：**如何从多张照片重建出高质量的 3D 网格模型**，既要快又要准。已有的两类方法各有缺陷：

- **光栅化方法**（如 [[3DGS|3D Gaussian Splatting]]）渲染快，但没有一个明确的"表面"概念，重建网格要靠后期深度融合，容易产生孔洞和噪声
- **隐式 SDF 方法**（如 [[NeuS]]、[[VolSDF]]、[[Neuralangelo]]）有清晰的表面定义，但每条光线要密集采样几百次，训练非常慢

SDFRaster 的核心思路：**做一个可以光栅化的 SDF**——把四面体网格承载的分段线性 SDF 当作一个可光栅化的几何图元，直接计算光线穿过的四面体段落并 alpha 混合，无需逐点采样。

整个 pipeline 分为三个紧耦合的环节：

1. **SDF 场优化**：从多视角图像优化四面体 SDF 参数
2. **网格提取**：用 Marching Tetrahedra 从 SDF 提取三角网格
3. **一致性监督**：将提取的网格光栅化，产生深度/法线，与 SDF 场渲染的深度/法线做一致性损失

### 四面体 SDF 表示

**SDF 场建模**：先在场景里铺一层 Delaunay 四面体网格（将空间切分成紧密排列的四面体）。在每个四面体顶点上，用一个带多分辨率哈希编码的 MLP 预测 SDF 值。四面体内部任意一点的 SDF 值由四个顶点的 SDF 值**线性插值**得到，从而获得连续的分段线性 SDF。

**哈希编码**：使用 [[InstantNGP]] 风格的多分辨率哈希网格编码 3D 坐标，输入坐标经过哈希表索引后连接到一个小型 MLP，输出标量 SDF 值。这种设计使得 SDF 场具有高分辨率的同时保持可微分。

### 距离场光栅化

**核心创新**：传统 SDF 渲染要沿光线密集采样（NeuS 风格的逐点采样），SDFRaster 不走这条路。它直接**光栅化四面体**：

1. 对每个像素，计算光线穿过的所有四面体段落
2. 对每个段落，用端点 SDF 值通过 NeuS 公式（logistic 密度函数）将 SDF 转化为透明度
3. 从前到后像传统 alpha 混合那样累加颜色和透明度

```
对于每个四面体片段 [t0, t1]：
  s0 = SDF(ray(t0)),  s1 = SDF(ray(t1))
  alpha = Sigmoid 转换(SDF -> 累积概率)
  color = alpha * ray_color
```

这样一次渲染只遍历光线实际穿过的四面体，不需要逐点密集采样，GPU 上跑得飞快。

### 可微分 Marching Tetrahedra

**最巧妙的一步**：在每次优化迭代中，SDFRaster 用可微分的 Marching Tetrahedra 直接从当前的 SDF 中提取出三角网格——没有后期处理，没有 TSDF 融合。

提取出来的网格再被光栅化，产生深度图和法线图，用来与 SDF 场渲染的深度/法线做**一致性损失**：

```
L_consistency = L_depth(SDF_depth, mesh_depth) + L_normal(SDF_normal, mesh_normal)
```

这样 SDF 优化和网格质量就绑在一起了：网格不好，梯度会流回 SDF 参数让它修正。

### 自适应四面体细化

四面体网格不是固定的。每隔 500 步：

1. 找到被物体表面穿过的四面体（顶点 SDF 符号不一样）
2. 在这些四面体中心插入新顶点并重新四面体化，把分辨率集中在表面附近
3. 剔除贡献很小的四面体（不删除，只是跳过渲染）
4. 剪掉既贡献小又远离表面的顶点

最终导出的网格**非常紧凑**——体积约 3 倍小于 TSDF 融合出来的网格。

## Training

- **损失函数**：L = L_color + L_depth_consistency + L_normal_consistency + L_eikonal
- **优化器**：AdamW
- **训练时间**：DTU 数据集约 98 分钟（对比：NeuS/VolSDF/Neuralangelo 均超过 12 小时）
- **四面体网格**：Delaunay 初始划分 + 每 500 步自适应细化
- **多分辨率哈希编码**：InstantNGP 风格的网格编码
- **Marching Tetrahedra**：可微分实现，嵌入训练循环

## Results & Comparisons

### 与隐式 SDF 方法的训练时间对比

| 方法 | DTU 训练时间 |
|------|-------------|
| SDFRaster | **98 分钟** |
| NeuS | >12 小时 |
| VolSDF | >12 小时 |
| Neuralangelo | >12 小时 |

SDFRaster 在训练速度上具有数量级优势，这得益于距离场光栅化避免了沿光线密集采样。

### 网格质量

SDFRaster 重建的 mesh 质量高（与隐式 SDF 方法相当或更优），主要得益于 Marching Tetrahedra 直接提取网格，避免了 TSDF 融合等后处理步骤带来的平滑效应和孔洞。

### 紧凑度

最终导出的网格体积约为 TSDF 融合网格的 1/3，得益于自适应细化只保留表面附近的四面体。

## Related Work Analysis

### 与 [[NeuS]] 的关系

NeuS 是最直接的对比基线。NeuS 用 MLP 隐式编码 SDF，沿光线密集采样渲染深度/法线，训练慢但表面清晰。SDFRaster 用四面体网格承载分段线性 SDF + 光栅化渲染，训练速度快 10 倍以上，同时保持表面质量。

### 与 [[3DGS|3D Gaussian Splatting]] 的关系

3DGS 渲染极快但没有表面定义。SDFRaster 通过 SDF 提供了明确的表面，同时通过光栅化四面体实现了接近 3DGS 的渲染效率。

### 与 [[Neuralangelo]] 的关系

Neuralangelo 用高斯平滑 SDF 处理非共视区域，训练同样超过 12 小时。SDFRaster 的四面体光栅化避免了这一瓶颈。

### 与 [[VolSDF]] 的关系

VolSDF 同样使用隐式 SDF + 体积渲染，训练速度慢。SDFRaster 通过光栅化替代体积采样解决了这一缺陷。

### 与 [[TSDF Fusion]] 的关系

传统 TSDF 融合是后处理步骤，SDFRaster 用可微分 Marching Tetrahedra 将网格提取嵌入训练循环，形成端到端优化。

## Ablations

- **光栅化 vs 采样渲染**：光栅化四面体比沿光线密集采样快 10 倍以上，且质量相当
- **Marching Tetrahedra 一致性损失**：移除一致性损失后网格质量明显下降，验证了紧耦合优化的必要性
- **自适应细化频率**：每 500 步细化是速度与质量的平衡点，过低导致表面粗糙，过高增加计算开销
- **四面体剪枝**：剪掉贡献小的四面体可显著减小导出网格体积（约 3 倍小于 TSDF 融合）

## Limitations

- **速度仍慢于 3DGS**：虽然比隐式 SDF 方法快很多，但渲染速度仍不及 3DGS 等纯光栅化方法
- **SDF 符号歧义**：对于无纹理或弱纹理区域，SDF 符号可能不稳定，影响表面重建
- **四面体生成质量**：初始 Delaunay 四面体划分的质量影响最终结果，对于复杂场景可能需要更精细的初始划分
- **Marching Tetrahedra 三角化**：在某些四面体配置下可能出现三角化歧义
- **显存占用**：四面体网格 + 哈希编码在高分辨率下显存占用较大

## 评论与启示

- 评价：mesh 质量好，但是速度还是慢（隐式 SDF 方法（NeuS、VolSDF、Neuralangelo）在 DTU 上训练时间都超过 12 小时，而 SDFRaster 需要 98 分钟）
- SDFRaster 方法直白描述：这篇论文的核心问题是**如何从多张照片重建出高质量的 3D 网格模型**，既要快又要准。
  - 已有的两类方法各有缺陷：光栅化方法（如 3DGS）渲染快，但没有明确的"表面"概念；隐式 SDF 方法（如 NeuS）有清晰的表面定义，但每条光线要密集采样几百次，训练非常慢。
  - SDFRaster 的思路是把两者的优点结合起来——**做一个可以光栅化的 SDF**
- 一句话总结：用四面体网格承载 SDF，用光栅化高效渲染它，边训练边从 SDF 里提取网格并用网格反过来监督 SDF，形成一个紧耦合的端到端优化环路
- 与 [[NeuS]] 的关键差异：NeuS 沿光线密集采样，SDFRaster 直接光栅化四面体，速度优势显著
- 与 [[3DGS|3D Gaussian Splatting]] 的关系：3DGS 无表面，SDFRaster 有明确表面定义，两者在"渲染效率 vs 表面质量"上取不同平衡点
- 与 [[VolumetricSurfaces|volumetric-surfaces]] 的对比：Volumetric Surfaces 用 k 个壳层网格实现模糊几何，SDFRaster 用四面体 SDF 实现精确表面

## Connections

- [[NeuS]] — 最直接的对比基线，SDFRaster 用光栅化替代其密集采样
- [[VolSDF]] — 同属隐式 SDF，训练速度慢
- [[Neuralangelo]] — 同属高质量重建，训练同样超过 12 小时
- [[3DGS|3D Gaussian Splatting]] — 渲染快但无表面定义
- [[InstantNGP]] — 多分辨率哈希编码的来源
- [[VolumetricSurfaces|volumetric-surfaces]] — 同属网格+渲染管线，不同几何表示
- [[MarchingCubes]] — Marching Tetrahedra 的前身

## Contradictions

- 与 [[3DGS|3D Gaussian Splatting]] 在"是否需要明确表面"上立场不同：3DGS 证明不需要表面也能高质量渲染，SDFRaster 证明有表面也能接近同等渲染效率
- 与 [[NeuS]] 在"训练时间"上：NeuS 密集采样训练超过 12 小时，SDFRaster 光栅化仅需 98 分钟

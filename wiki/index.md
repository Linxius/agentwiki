# Wiki Index

This file is maintained by the LLM. Updated on every ingest.

## Overview
- [Overview](overview.md) — living synthesis across all sources

## Sources

- [RaDe-GS: Rasterizing Depth in Gaussian Splatting](sources/ra-de-gs.md) — 在 3D-GS 上栅格化深度与法线，DTU CD 0.68mm 媲美 Neuralangelo，训练 8.3 分钟
- [CGVQM: Computer Graphics Video Quality Metric](sources/cgvqm.md) — Intel Labs 全参考视频质量指标，针对渲染失真校准，配套 CGVQD 数据集

- [World Tracing](sources/world-tracing-generative-pixel-aligned-geometry-beyond-the-visible) — 像素对齐多层几何扩散，单图生成完整3D场景（可见+遮挡），SOTA 几何 F1
## Papers
- [TransparentGS: Fast Inverse Rendering of Transparent Objects with Gaussians](sources/transparent-gs-fast-inverse-rendering-of-transparent-objects-with-gaussians) — 3D-GS 透明物体逆向渲染：透明高斯基元 + 延迟折射 + 高斯光场探针
- [A LoD of Gaussians](sources/a-lod-of-gaussians) — 消费级 GPU 城市级 3DGS 无分块训练：核外存储 + HSPT + 流式渲染
- [SDFRaster](sources/sdfraster) — 可光栅化 SDF 端到端网格重建：Delaunay 四面体化 + 可微 Marching Tetrahedra
- [Rectified Flow](sources/rectified-flow) — Rectified Flow：学习直线轨迹 ODE 实现快速生成和传输
## Papers
- [Arm Neural Super Sampling (NSS)](sources/arm-neural-super-sampling) — ARM 神经网络超采样项目（页面返回 404）
## Papers
- [Arm Neural Technology for Mobile Games](sources/arm-neural-technology-for-mobile-games) — ARM 移动端神经网络技术官方文档（访问受限）
- [Ref-DGS: Reflective Dual Gaussian Splatting](sources/ref-dgs.md) — 双高斯解耦的近场镜面反射建模，表面重建+新视角合成 SOTA
- [Spherical Voronoi Directional Appearance](sources/spherical-voronoi-directional-appearance.md) — 基于可微分 Spherical Voronoi 划分的 3DGS 外观建模，统一了辐射度和反射表示
- [Proxy-GS](sources/proxy-gs.md) — 利用代理网格的统一遮挡先验加速结构化3DGS训练与推理
- [Volumetric Surfaces](sources/volumetric-surfaces.md) — k-SDF 多层网格表示的模糊几何实时视图合成，移动端 42 FPS
- [SuGaR: Surface-Aligned Gaussian Splatting](sources/su-ga-r.md) -- 从 3DGS 高效提取高质量网格并绑定高斯体实现可编辑渲染
- [Adaptive Shells](sources/adaptive-shells.md) — 自适应窄带渲染加速 NeRF（空间变化核+显式壳提取+窄带采样）
- [TransGI: Real-Time Dynamic Global Illumination With Object-Centric Neural Transfer Model](sources/transgi.md) — 以物体为中心的神经迁移模型实现实时动态全局光照，支持光泽材质和物体变换
## Papers
- [Toward Richer Material Generation via Procedural Data Enhancement](sources/toward-richer-material-generation-via-procedural-data-enhancement) — 简单 PBR 自动提升为多层 BRDF + 神经材质 + 视频扩散生成，CLIP-FID 3.907
- [NeuMatEx: Extracting Neural Materials from Multi-view Images](sources/neumatex.md) — 首个性从多视角图像提取神经材质的方法，LMRM + 不确定性引导 TTO
- [Bake It Till You Make It: Ultrafast Spatial Texture-Atlas Splatting](sources/bake-it-till-you-make-it.md) — 哈希网格烘焙为纹理图集，4K@60FPS 新视角合成
- [AMD FidelityFX Super Resolution (FSR 1.0)](sources/fidelityfx-fsr-1.md) — 代码分析
- [Extracting Neural Materials from Multi-view Images](sources/extracting-neural-materials-from-multi-view-images.md) — 神经材质提取管线
- [Snapdragon Game Super Resolution (SGSR)](sources/snapdragon-gsr.md) — 代码分析
- [Volumetric Surfaces](sources/volumetric-surfaces.md) — 多层网格表示模糊几何的实时视图合成
- [Adaptive Shells](sources/adaptive-shells.md) — 自适应窄带渲染加速 NeRF
## Papers
- [TopoMesh: High-Fidelity Mesh Autoencoding via Topological Unification](sources/topomesh.md) — 拓扑统一框架实现显式网格级 VAE 监督，锐边 F1 提升超 8%
- [GS-2M: Material-aware Gaussian Splatting for High-fidelity Mesh Reconstruction](sources/gs-2m.md) — 材料感知联合优化，PBR + 多视角粗糙度监督实现反射表面高质量网格重建
## Papers
- [Surflo](sources/surflo.md) — 全局 latent + 流匹配实现前馈式任意密度 3D 表面重建，从无位姿多视图直接生成定向点云和网格
- [Neural Harmonic Textures for High-Quality Primitive Based Neural Reconstruction](sources/neural-harmonic-textures.md) — 基元绑定谐波特征 + 延迟着色 MLP，提升 3DGS 单基元表达力，新视角合成 SOTA
## Entities

## Concepts

## Issues
- [issues](issues.md) — pending entities, phantom links, contradictions

## References
- [interests](interests.md) — user interests for filter matching

## Syntheses

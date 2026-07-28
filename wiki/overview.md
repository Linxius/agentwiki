---
title: "Overview"
type: synthesis
tags: []
sources: []
last_updated: "2026-07-28"
---

# Overview

当前 wiki 包含以下已合入的源文档：

### 论文

- [[Adaptive Shells|adaptive-shells]] — 自适应窄带渲染加速 NeRF（空间变化核+显式壳提取+窄带采样）
- [[AMD FidelityFX Super Resolution (FSR 1.0)|fidelityfx-fsr-1]] — 代码分析
- [[Arm Neural Super Sampling (NSS)|arm-neural-super-sampling]] — ARM 神经网络超采样项目（页面返回 404）
- [[Arm Neural Technology for Mobile Games|arm-neural-technology-for-mobile-games]] — ARM 移动端神经网络技术官方文档（访问受限）
- [[Bake It Till You Make It: Ultrafast Spatial Texture-Atlas Splatting|bake-it-till-you-make-it]] — 哈希网格烘焙为纹理图集，4K@60FPS 新视角合成
- [[Extracting Neural Materials from Multi-view Images|extracting-neural-materials-from-multi-view-images]] — 神经材质提取管线
- [[GS-2M: Material-aware Gaussian Splatting for High-fidelity Mesh Reconstruction|gs-2m]] — 材料感知联合优化，PBR + 多视角粗糙度监督实现反射表面高质量网格重建
- [[NeuMatEx: Extracting Neural Materials from Multi-view Images|neumatex]] — 首个性从多视角图像提取神经材质的方法，LMRM + 不确定性引导 TTO
- [[Proxy-GS|proxy-gs]] — 利用代理网格的统一遮挡先验加速结构化3DGS训练与推理
- [[Rectified Flow|rectified-flow]] — Rectified Flow：学习直线轨迹 ODE 实现快速生成和传输
- [[Ref-DGS: Reflective Dual Gaussian Splatting|ref-dgs]] — 双高斯解耦的近场镜面反射建模，表面重建+新视角合成 SOTA
- [[Snapdragon Game Super Resolution (SGSR)|snapdragon-gsr]] — 代码分析
- [[Spherical Voronoi Directional Appearance|spherical-voronoi-directional-appearance]] — 基于可微分 Spherical Voronoi 划分的 3DGS 外观建模，统一了辐射度和反射表示
- [[Surflo|surflo]] — 全局 latent + 流匹配实现前馈式任意密度 3D 表面重建，从无位姿多视图直接生成定向点云和网格
- [[TopoMesh: High-Fidelity Mesh Autoencoding via Topological Unification|topomesh]] — 拓扑统一框架实现显式网格级 VAE 监督，锐边 F1 提升超 8%
- [[Toward Richer Material Generation via Procedural Data Enhancement|toward-richer-material-generation-via-procedural-data-enhancement]] — 简单 PBR 自动提升为多层 BRDF + 神经材质 + 视频扩散生成，CLIP-FID 3.907
- [[TransGI: Real-Time Dynamic Global Illumination With Object-Centric Neural Transfer Model|transgi]] — 以物体为中心的神经迁移模型实现实时动态全局光照，支持光泽材质和物体变换
- [[Volumetric Surfaces|volumetric-surfaces]] — k-SDF 多层网格表示的模糊几何实时视图合成，移动端 42 FPS

### 其他源

- [[World Tracing|world-tracing-generative-pixel-aligned-geometry-beyond-the-visible]] — 像素对齐多层几何扩散，单图生成完整3D场景（可见+遮挡），SOTA 几何 F1

## [2026-07-28] ingest | Rectified Flow

Added source. Key claims: Rectified Flow 通过学习直线轨迹的 ODE 实现两个分布间的传输映射，Reflow 过程进一步直化轨迹，可实现单步 Euler 生成。

## [2026-07-28] ingest | Arm Neural Super Sampling

Added source. Key claims: ARM 神经网络超采样项目，托管于 Hugging Face，页面返回 404 未找到。

## [2026-07-28] ingest | Arm Neural Technology for Mobile Games

Added source. Key claims: ARM 移动端神经网络技术官方文档，因访问受限未获取到完整内容。

## [2026-07-28] ingest | Ref-DGS: Reflective Dual Gaussian Splatting

Added source. Key claims: 双高斯解耦表示实现近场镜面反射的高效光栅化渲染；Sph-Mip 编码远场环境镜面；物理感知混合着色器；在 ShinySynthetic 和 GlossySynthetic 上表面重建和新视角合成 SOTA，训练仅 12.6 分钟。

## [2026-07-28] ingest | Spherical Voronoi Directional Appearance as a Differentiable Partition of the Sphere

Added source. Key claims: Spherical Voronoi 作为一种新的球面函数显式表示，在 3DGS 辐射度建模上一致超越 SH/SG/SB，在反射建模上通过 Voronoi Light Probes 达到 SOTA。主要局限：Ref-Real 未达 SOTA，推理速度 0.45× 3DGS。

## [2026-07-28] ingest | Proxy-GS

- Source: https://arxiv.org/abs/2509.24421
- Category: papers
- Tags: 3dgs, occlusion-culling, neural-rendering, real-time-rendering, gaussian-splatting
- Key claims: 代理网格 + Hi-Z 遮挡剔除使 anchor 减少 80-90%，MatrixCity 中实现 2.5× FPS 提升同时改善渲染质量；对代理网格分辨率不敏感，可在 824KB 粗略网格上运行

## [2026-07-28] ingest | Volumetric Surfaces: Representing Fuzzy Geometries with Layered Meshes

Added source. Key claims: k-SDF 多层网格表示在移动端实现 42 FPS 实时渲染，PSNR 34.50 (Shelly 7-Mesh)，显著优于 MobileNeRF。质量低于 3DGS 但速度远胜。

## [2026-07-28] ingest | SuGaR: Surface-Aligned Gaussian Splatting for Efficient 3D Mesh Reconstruction and High-Quality Mesh Rendering

Added source. Key claims: (1) 正则化项使高斯体沿场景表面排列，解决了 3DGS 无法提取网格的核心问题；(2) 深度图水平集采样+Poisson 重建实现分钟级网格提取（vs NeRF 方法的数小时）；(3) 网格绑定高斯体联合优化在保持可编辑性的同时达到 PSNR=27.50，超越所有使用网格的 IBR 方法。

## [2026-07-28] ingest | Adaptive Shells for Efficient Neural Radiance Field Rendering

Updated source. Key claims: 空间变化核大小使NeRF渲染自适应场景复杂度；显式壳+隐式场的混合表示兼顾效率和保真度；固体区域单采样点渲染达到262 FPS（Shelly）。新增SIGGRAPH Asia 2023发表信息和项目页面链接。

## [2026-07-28] ingest | TransGI: Real-Time Dynamic Global Illumination With Object-Centric Neural Transfer Model

Added source. Key claims: 物体级神经迁移模型支持光泽材质和物体变换；跨探针辐射度共享实现实时光照探针生成；Falcor 引擎中 <10ms/帧渲染；在 Bitterli 数据集上 RMSE 比 DDGI 降低 50-70%。

## [2026-07-28] ingest | Toward Richer Material Generation via Procedural Data Enhancement

Added source. Key claims: (1) 简单 PBR 自动增强为 8 层 BRDF 模型； (2) 压缩到 6D 神经材质隐空间； (3) 用 Cosmos 视频扩散在 3D 物体上生成神经材质； CLIP-FID 3.907。

## [2026-07-28] ingest | NeuMatEx: Extracting Neural Materials from Multi-view Images

Added source. Key claims: 首个从多视角图像提取神经材质的端到端方法；LMRM 基于 Wan2.1 DiT 单步预测三平面+不确定性；不确定性引导 TTO 防止光照-材质分解失败；比 PBR 更高质量的多瓣高光表达。

## [2026-07-28] ingest | Bake It Till You Make It: Ultrafast Spatial Texture-Atlas Splatting

Added source. Key claims: 视图无关哈希网格烘焙为纹理图集消除神经查询瓶颈；可变形 Beta 核 + 衰减减少正则化实现高稀疏度；4K@60FPS 消费级硬件实时渲染；0.14M 原语达 26.75 PSNR。

## [2026-07-28] filter | 23 files processed

## [2026-07-28] filter | 23 files processed

## [2026-07-28] filter | 23 files processed

## [2026-07-28] filter | 23 files processed

## [2026-07-28] filter | 23 files processed

## [2026-07-28] filter | 23 files processed

## [2026-07-28] filter | 23 files processed

## [2026-07-28] filter | 23 files processed

## [2026-07-28] filter | 23 files processed

## [2026-07-27] filter | 23 files processed

## [2026-07-27] filter | 23 files processed

## [2026-07-27] filter | 23 files processed

## [2026-07-27] filter | 23 files processed

## [2026-07-27] filter | 23 files processed

## [2026-07-27] filter | 23 files processed

## [2026-07-27] filter | 23 files processed

## [2026-07-27] filter | 23 files processed

## [2026-07-27] filter | 23 files processed

## [2026-07-27] filter | 23 files processed

## [2026-07-27] filter | 23 files processed

## [2026-07-27] filter | 23 files processed

# Wiki Log

## [2026-07-26] ingest | Volumetric Surfaces
- Source: https://arxiv.org/abs/2409.02482
- Category: papers
- Tags: view-synthesis, real-time-rendering, mesh-representation, fuzzy-geometry, mobile-rendering

## [2026-07-26] ingest | Adaptive Shells
- Source: https://arxiv.org/abs/2311.10091
- Category: papers
- Tags: NeRF, volume-rendering, implicit-surface, adaptive-sampling, real-time-rendering

## [2026-07-26] ingest | Extracting Neural Materials from Multi-view Images
- Source: https://arxiv.org/abs/2606.26715
- Category: papers
- Tags: neural-materials, inverse-rendering, differentiable-rendering, material-extraction

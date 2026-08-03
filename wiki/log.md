## [2026-08-04] lint | Wiki health check

Ran lint. See lint-report.md for details.

## [2026-08-04] lint | Wiki health check

Ran lint. See lint-report.md for details.

## [2026-08-04] ingest | ARM Neural Super Sampling (NSS)

Added source. Note: Hugging Face page returns 404.

## [2026-08-04] ingest | ARM Neural Technology for Mobile Games

Added source. Note: ARM Developer documentation access denied.

## [2026-08-04] ingest | [A LoD of Gaussians: Unified Training and Rendering for Ultra-Large Scale Reconstruction with External Memory](sources/a-lod-of-gaussians.md) — SIGGRAPH 2026，外部存储 + HSPT 层级结构，消费级 GPU 6000 万高斯体训练与渲染

## [2026-08-04] ingest | AMD FidelityFX Super Resolution (FSR 1.0)

Added source. Key claims: Header-only EASU + RCAS 空间超分，12-tap 各向异性 Lanczos 滤波 + 2x2 邻域去振铃，噪声感知锐化。

## [2026-08-04] ingest | Rectified Flow

Added source. Key claims: 流匹配学习直线 ODE 传输映射，Reflow 直化过程实现单步 Euler 推理。

## [2026-08-04] ingest | Snapdragon Game Super Resolution (SGSR)

Added source. Key claims: 高通 Adreno GPU 超分着色器，V1 单 pass 空间上采样 + V2 时间性融合，YCoCg 色彩空间 + R32UI 位打包。

## [2026-08-04] ingest | World Tracing: Generative Pixel-Aligned Geometry Beyond the Visible

Added source. Key claims: 像素对齐多层几何表示，WT-DiT 流匹配扩散 Transformer，forward-filling + 混合噪声调度，超越单层基线和 3D 生成器。

# Wiki Log

## [2026-08-04] ingest | Sparse Voxels Rasterization: Real-time High-fidelity Radiance Field Rendering

Added source. Key claims: SVRaster 使用神经自由体素光栅化，方向相关 Morton 排序消除 popping artifact，Mip-NeRF360 LPIPS 0.185 优于 3DGS。

## [2026-08-04] ingest | Ref-GS: Directional Factorization for 2D Gaussian Splatting

Added source. Key claims: Ref-GS 通过延迟高斯着色和方向分解实现反射场景的 SOTA 渲染质量和法线重建精度。

## [2026-08-04] ingest | [8DNA: 8D Neural Asset Light Transport by Distribution Learning](sources/8dna-8d-neural-asset-light-transport-by-distribution-learning.md) — UCSD+NVIDIA，归一化流学习 8D 光传输，支持近场照明

## [2026-08-04] ingest | [1.5万字速通LLM主流模型结构](sources/llm-architecture-overview.md) — 知乎文章，系统讲解 LLM 结构组件（Tokenizer、Norm、Attention、FFN、LM Head、MTP、MoE）

## [2026-08-03] filter | 4 files processed (2 excluded)

## [2026-07-31] ingest | GlossyGS: Inverse Rendering of Glossy Objects with 3D Gaussian Splatting
Added source. Key claims: 3D-GS 光泽物体逆渲染，法线图预滤波 + 微表面分割先验，Shiny Blender 重光照 PSNR 25.72，实时 30 FPS。

## [2026-07-31] ingest | RadiosityGS: Differentiable Light Transport with Gaussian Surfels via Adapted Radiosity
Added source. Key claims: 高斯 surfels + 经典辐射度理论，球谐系数空间操作，全局光照 5-10h 训练，推理 515 FPS。

## [2026-07-31] ingest | Mobile-GS: Real-time Gaussian Splatting for Mobile Devices
Added source. Key claims: 移动端 3DGS，无排序渲染 + 球谐蒸馏 + 神经量化 + 剪枝，骁龙 8 Gen 3 上 116 FPS。

## [2026-07-31] ingest | GLINT: Modeling Scene-Scale Transparency via Gaussian Radiance Transport
Added source. Key claims: 场景尺度透明度重建，分解高斯表示（界面/传输/反射），混合光栅化/光线追踪，3D-FRONT-T 基准 SOTA。

## [2026-07-31] ingest | STREAM3D: Generating 3D Meshes from Videos
Added source. Key claims: 视频到 mesh 生成，多视角一致性约束，直接从视频序列输出流形网格。

## [2026-07-31] ingest | Ref-GS: Directional Factorization for 2D Gaussian Splatting
Added source. Key claims: 反射场景 3DGS，Sph-Mip 编码 + 延迟渲染 + 方向分解，ShinySynthetic PSNR 34.00，训练 12.6 分钟。

## [2026-07-31] ingest | A Generalizable Light Transport 3D Embedding for Global Illumination
Added source. Key claims: 可泛化全局光照，点云 + 线性 Transformer + 局部解码，14k 室内场景基准，推理 O(K) 常数时间。

## [2026-07-30] ingest | RaDe-GS: Rasterizing Depth in Gaussian Splatting
Added source. Key claims: 3D-GS 栅格化深度/法线，DTU CD 0.68mm 媲美 Neuralangelo，训练 8.3 分钟，远快于 NeRF 类方法。

## [2026-07-30] ingest | CGVQM: Computer Graphics Video Quality Metric
Added source. Key claims: Intel Labs 全参考视频质量指标，针对渲染失真（空间+时序伪影）校准，输出可解释感知等级与误差图，配套 CGVQD 数据集（CGF 2025）。

## [2026-07-30] ingest | TransparentGS: Fast Inverse Rendering of Transparent Objects with Gaussians
Added source. Key claims: 基于 3D-GS 的透明物体逆向渲染框架，透明高斯基元 + 延迟折射策略 + 高斯光场探针，1 小时内完成重建，实时新视角合成。

## [2026-07-30] ingest | A LoD of Gaussians: Out-of-Core Training and Rendering for Seamless Ultra-Large Scene Reconstruction
Added source. Key claims: 消费级 GPU 上城市级 3DGS 无分块训练与渲染，核外存储 + 层级顺序点树 (HSPT) + 流式加载，24GB 显存处理上亿高斯体。

## [2026-07-30] ingest | SDFRaster: Distance Field Rasterization for End-to-End Mesh Reconstruction
Added source. Key claims: 可光栅化的 SDF 框架，Delaunay 四面体化 + 四面体光栅化 + 可微 Marching Tetrahedra，DTU 上 Chamfer 距离优于 2DGS，训练 98 分钟（远快于 NeRF 类方法 12+ 小时）。

## [2026-07-29] filter | 17 files processed（含 2 篇 alphaXiv 补全：GlossyGS、RaDe-GS）

## [2026-07-29] ingest | Neural Harmonic Textures for High-Quality Primitive Based Neural Reconstruction
Added source. Key claims: 将可学习特征锚定在基元外包的虚拟支架上，于光线交点插值并经 sin/cos 周期激活，使 alpha 混合变为谐波分量加权和，最后用轻量 MLP 延迟解码像素颜色；在 3DGS 上以更低基元数取得新视角合成 SOTA，并可无缝接入 3DGUT / 2DGS / Triangle Splatting。

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

## [2026-07-28] ingest | TopoMesh: High-Fidelity Mesh Autoencoding via Topological Unification

- Source: https://arxiv.org/abs/2603.24278
- Category: papers
- Tags: mesh-autoencoding, VAE, topological-unification, dual-marching-cubes, 3d-generation
- Key claims: (1) 拓扑统一范式使 GT 和预测网格共享 DMC 拓扑，首次实现顶点/面级显式监督；(2) Topo-Remesh 全 GPU 加速 + L∞ 度量，15 秒 1024³ 重网格；(3) 稀疏体素-点交叉注意力压缩注意力图 74GB→3.8MB；(4) Teacher Forcing + 渐进分辨率稳定训练；(5) 锐边 F1 提升超 8%（0.932 vs 0.873），CD 降低超 30%

## [2026-07-28] ingest | GS-2M: Material-aware Gaussian Splatting for High-fidelity Mesh Reconstruction

- Source: https://arxiv.org/abs/2509.22276
- Category: papers
- Tags: 3dgs, mesh-reconstruction, material-decomposition, pbr, neural-rendering
- Key claims: (1) 材料-网格联合优化框架，每个高斯体增加 albedo + roughness 可学习参数；(2) 多视角 NCC 粗糙度监督完全消除神经组件依赖；(3) 遮挡感知滤波 + 多视角法线一致性增强几何鲁棒性；(4) DTU CD 0.53 与 SOTA 持平，Shiny Blender 反射表面显著优于 2DGS/GOF/PGSR；(5) 训练 51min（完整版）/ 22.4min（无 BRDF 版）

## [2026-07-28] filter | 23 files processed

## [2026-07-28] ingest | Volumetric Surfaces
- Source: https://arxiv.org/abs/2409.02482
- Category: papers
- Tags: view-synthesis, real-time-rendering, mesh-representation, fuzzy-geometry, mobile-rendering

## [2026-07-28] ingest | Adaptive Shells
- Source: https://arxiv.org/abs/2311.10091
- Category: papers
- Tags: NeRF, volume-rendering, implicit-surface, adaptive-sampling, real-time-rendering

## [2026-07-28] ingest | Extracting Neural Materials from Multi-view Images
- Source: https://arxiv.org/abs/2606.26715
- Category: papers
- Tags: neural-materials, inverse-rendering, differentiable-rendering, material-extraction

## [2026-07-28] ingest | Surflo: Consistent 3D Surface Flow Model with Global State
- Source: https://arxiv.org/abs/2606.13644
- Category: papers
- Tags: surface-reconstruction, flow-matching, feed-forward-3d, global-latent, multi-view-3d
- Key claims: 前馈式 3D 表面重建，用 Perceiver 压缩多视图为固定大小全局 latent，流匹配解码为任意密度定向点云，推理时渲染引导保证一致性。8 个基准匹配或超越 SOTA，比优化方法快一个数量级。

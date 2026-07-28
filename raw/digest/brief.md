# 资讯简报  2026-07-29


## [感兴趣]

#### SplatSDF: Boosting SDF-NeRF via Architecture-Level Fusion with Gaussian Splats
- 来源: https://arxiv.org/abs/2411.15468
- 源文件: [raw/digest/sources/2026-07-29/arxiv-241115468-4b988725.md](/raw/digest/sources/2026-07-29/arxiv-241115468-4b988725.md)
- 标题: SplatSDF：通过架构级融合高斯泼溅加速 SDF-NeRF
- 领域: 三维重建 / 神经辐射场 / 表面重建
- 关键词: 3D Gaussian Splatting, SDF-NeRF, surface reconstruction, fusion, robotics, convergence
- 匹配: 3DGS, 表面重建
- 理由: 论文第 II 节与 Figure 2（Overview）直接阐述将 3D Gaussian splats (3DGS) 在架构层面融合进 SDF-NeRF，用于加速表面/几何重建收敛；核心方法是用预训练 3DGS 作为 SDF-NeRF 的输入指导训练，直接对应 3DGS 与表面重建兴趣。
- [ ] 深度阅读
- [ ] 合入 wiki
- [ ] 不感兴趣
- [ ] 不处理

![Overview](https://arxiv.org/html/2411.15468v2/figures/overview.png)
**Overview**

**简介**：本文提出 SplatSDF，将 3D Gaussian Splatting 在架构层面（而非仅靠一致性损失）融合进 SDF-NeRF，以加速其收敛。通过稀疏的“表面 3DGS 融合”策略，仅在物体表面附近将 3DGS 的神经嵌入注入 SDF-NeRF，训练时利用 3DGS 快速预训练的优势，推理时无需 3DGS 即可得到兼具几何与光度精度的 SDF 表示。

**详细报告**（主要思路与方法流程）：
解决的问题：SDF-NeRF 能同时提供逼真渲染和几何推理（如机器人避障），但训练慢、收敛难，实际难部署。
简单来说就是：3DGS 用光栅化训练极快但做不了距离查询，SDF-NeRF 能做几何查询却训练慢；SplatSDF 让 3DGS 先快速训好，再把它的几何信息“喂”给 SDF-NeRF 当提示，帮后者更快找准表面位置。
方法流程：先光栅化预训练 3DGS→用 3DGS 渲染深度定位表面锚点→设计 3DGS 聚合器把高斯属性（均值、协方差、颜色、球谐）编码成嵌入→仅在锚点附近做“表面融合”注入 SDF 网络→体渲染监督得到 SDF-NeRF；推理时丢弃 3DGS 只留 SDF。
实验结果：达到相同几何精度比最佳基线快 3 倍，Chamfer 距离与 PSNR 均优于 SOTA SDF-NeRF 方法。
局限性：仍依赖 SDF-NeRF 的体渲染训练范式，复杂度高于纯显式表示。

#### TransparentGS: Fast Inverse Rendering of Transparent Objects with Gaussians
- 来源: https://arxiv.org/abs/2504.18768
- 源文件: [raw/digest/sources/2026-07-29/arxiv-250418768-d85018a2.md](/raw/digest/sources/2026-07-29/arxiv-250418768-d85018a2.md)
- 标题: TransparentGS：基于高斯表示的透明物体快速逆向渲染
- 领域: 三维重建 / 逆向渲染 / 3D Gaussian Splatting
- 关键词: 3D Gaussian Splatting, inverse rendering, transparent objects, refraction, reflection, GaussProbe
- 匹配: 3DGS, 实时渲染
- 理由: 论文摘要与第 3 节（Preliminaries: 3D Gaussian Splatting）及 Figure 2 管道图直接基于 3D-GS 构建透明物体逆向渲染框架；核心表示是透明 Gaussian primitives，并强调 1 小时内重建且支持实时新视角合成，直接对应 3DGS 与实时渲染兴趣。
- [ ] 深度阅读
- [ ] 合入 wiki
- [ ] 不感兴趣
- [ ] 不处理

**简介**：本文提出 TransparentGS，一个基于 3D-GS 的透明物体快速逆向渲染框架。它设计透明高斯原语表达几何与材质，用延迟折射策略处理高光折射，并提出高斯光场探针（GaussProbe）与基于深度的迭代探针查询（IterQuery）刻画环境光与邻近物体的间接光，实现含二次光线效果的实时新视角合成与重光照。

**详细报告**（主要思路与方法流程）：
解决的问题：透明物体的反射与折射使 3D 重建极难，现有 NeRF/3DGS 方法要么慢、要么不支持实时，且光栅化式 3D-GS 无法处理折射等二次光线。
简单来说就是：把透明物体也用 3D 高斯来表示，但给每个高斯额外记录“法线、粗糙度、折射率”等材质属性，再用“延迟着色”方式先整体混色再算折射方向，并用环绕物体的多个“光探针”缓存环境光照来解决视差。
方法流程：用 SAM2 分割场景→透明物体用透明高斯原语、环境用普通 3D-GS 重建→把环境烘焙成高斯光场探针→对折射/反射光线用 IterQuery 迭代查探针取色→可结合网格做二次光线追踪并提取表面网格。
实验结果：1 小时内完成重建（比 NeRF 方法快 20 倍以上），实时帧率 31–51 FPS，新视角与法线/折射重建质量优于 GShader、NU-NeRF 等。
局限性：复杂多 bounce 光路（如空心物体）仍有歧义，且依赖分割精度。

#### A LoD of Gaussians: Out-of-Core Training and Rendering for Seamless Ultra-Large Scene Reconstruction
- 来源: https://arxiv.org/abs/2507.01110
- 源文件: [raw/digest/sources/2026-07-29/arxiv-250701110-d74ea026.md](/raw/digest/sources/2026-07-29/arxiv-250701110-d74ea026.md)
- 标题: A LoD of Gaussians：面向无缝超大规模场景重建的核外训练与渲染
- 领域: 三维重建 / 3D Gaussian Splatting / 大规模场景
- 关键词: 3D Gaussian Splatting, large-scale, level-of-detail, out-of-core, streaming, novel view synthesis
- 匹配: 3DGS, 场景表示
- 理由: 论文摘要与第 1、3、4 节直接以 3D Gaussian Splatting 为核心，提出无需分块、基于核外存储与细节层级（LoD）的城市级超大规模场景训练与渲染框架，直接对应 3DGS 与场景表示/实时渲染兴趣。
- [ ] 深度阅读
- [ ] 合入 wiki
- [ ] 不感兴趣
- [ ] 不处理

**简介**：本文提出“A LoD of Gaussians”，一种在单张消费级 GPU 上无需空间分块、无缝训练与渲染城市级超大规模 3D Gaussian Splatting 场景的框架。它把全部高斯存于 CPU 内存，按视角动态流式加载，并用层级顺序点树（HSPT）做高效的视角相关 LoD 选择，配合缓存与视图调度降低传输开销。

**详细报告**（主要思路与方法流程）：
解决的问题：3DGS 在大规模场景受显存限制，现有方法靠切块训练，但会在块边界产生渗色、重影等伪影，且渲染时仍需所有可见块同时在显存。
简单来说就是：干脆不分块，把海量高斯主要放在内存里，只把“当前相机看到的、按距离该显示的细节层级”的高斯流式传进显存；再用一种树状层级结构（HSPT）快速决定每个视角该用多粗多细的高斯。
方法流程：全部高斯属性存 CPU RAM→构建高斯层级树并转为顺序点树存显存→按相机距离用 HSPT 选出合适的 LoD 裁剪集→CPU 上做 densification 后回传→仅流式加载未缓存的 SPT 到 GPU 训练/渲染。
实验结果：在 Uni10k、MatrixCity 等 aerial/street/indoor 数据集上达到 SOTA，单卡即可无缝重建城市级场景。
局限性：依赖 CPU-GPU 传输带宽，极端无局部性的视角切换仍有加载开销。

#### Distance Field Rasterization for End-to-End Mesh Reconstruction
- 来源: https://arxiv.org/abs/2604.23537
- 源文件: [raw/digest/sources/2026-07-29/arxiv-260423537-215ed516.md](/raw/digest/sources/2026-07-29/arxiv-260423537-215ed516.md)
- 标题: 用于端到端网格重建的距离场光栅化
- 领域: 三维重建 / 表面重建 / 网格提取
- 关键词: mesh reconstruction, signed distance field, rasterization, Marching Tetrahedra, Delaunay, surface
- 匹配: 网格重建, 表面重建
- 理由: 论文摘要与第 3 节（Method）及 Figure 2 直接提出可光栅化的 SDF 表示用于端到端网格重建（end-to-end mesh reconstruction），从多视角图像直接提取表面网格，并广泛讨论对比 3DGS 表面重建方法的局限，核心主题即网格/表面重建，直接对应兴趣中的网格重建与表面重建。
- [ ] 深度阅读
- [ ] 合入 wiki
- [ ] 不感兴趣
- [ ] 不处理

**简介**：本文提出 SDFRaster，一种可光栅化的有符号距离场（SDF）框架，用于从多视角图像端到端重建网格。它在 Delaunay 四面体化上学习连续 SDF，用四面体光栅化与 alpha 混合高效渲染，并将可微 Marching Tetrahedra 融入优化循环直接提取网格，避免了 3DGS 等体素方法所需的后处理网格提取。

**详细报告**（主要思路与方法流程）：
解决的问题：光栅化方法（如 3DGS）渲染快但体素原语没有明确定义的表面，网格提取只能靠深度融合作后处理，易产生噪声与不完整；而隐式 SDF 虽有好表面却需昂贵的沿光线密集采样。
简单来说就是：把场景用四面体网格剖分，在每个顶点上用一个小网络预测“到表面的距离”（SDF），渲染时像 3DGS 一样光栅化四面体并混色，但几何由零等值面直接定义，所以训练过程中就能随时切出干净网格。
方法流程：Delaunay 四面体化场景→哈希编码预测顶点 SDF 与外观→光栅化四面体、用 SDF 转不透明度做 alpha 混合渲染→每轮用可微 Marching Tetrahedra 提取网格并渲染深度/法线做一致性监督→表面附近自适应加密四面体保持细节紧凑。
实验结果：在 DTU 上 Chamfer 距离低于 2DGS、MILo 等显式方法，TnT 上 F1 有竞争力且网格体积小约 3 倍。
局限性：SDF 仍由哈希 MLP 参数化，存在网络推理开销。

#### 3DGS : Joint Super Sampling and Frame Interpolation for Real-Time Large-Scale 3DGS Rendering
- 来源: https://arxiv.org/abs/2605.11489
- 源文件: [raw/digest/sources/2026-07-29/arxiv-260511489-16e0cf47.md](/raw/digest/sources/2026-07-29/arxiv-260511489-16e0cf47.md)
- 标题: 3DGS³：面向实时大规模3DGS渲染的联合超采样与帧插值
- 领域: 3D高斯泼溅实时渲染加速
- 关键词: 3D高斯泼溅, 实时渲染, 超采样, 帧插值, 后渲染加速, GRU
- 匹配: 3D高斯泼溅（3DGS）, 实时渲染
- 理由: 文档标题与摘要直接以3D Gaussian Splatting（3DGS）为核心，第1节与第3节提出针对3DGS的后渲染实时加速框架（GASS超采样 + LTFI帧插值），属于3DGS实时渲染的直接研究。
- [ ] 深度阅读
- [ ] 合入 wiki
- [ ] 不感兴趣
- [ ] 不处理

**简介**：3DGS³提出一种后渲染框架，通过超采样与帧插值联合加速大规模3D高斯泼溅的实时渲染。GASS模块利用高斯的可微性提取图像梯度引导高分辨率重建，LTFI模块用轻量U-Net融合时序与可微空间线索合成中间帧。在三个公开基准上，该方法在保持画质的同时达到最高FPS，且与现有3DGS加速方法兼容。目前仅针对静态场景。

**详细报告**（主要思路与方法流程）：
问题：3D高斯泼溅（3DGS）虽能实时渲染，但在超大规模或超高分辨率场景下因计算瓶颈难以保持高帧率。核心思路：简单来说就是不在泼溅管线内部优化，而是借鉴DLSS的思路，在渲染之后用神经网络对低分辨率输出做超采样和帧插值，从而把低分辨率、低帧率“撑”成高分辨率、高帧率。方法流程：输入低分辨率3DGS渲染图，GASS模块利用高斯的可微性提取图像梯度，结合历史特征通过GRU网络重建高分辨率图；LTFI模块用轻量U-Net融合前后帧与可微空间线索，合成中间帧。实验在Mip-NeRF360、Tanks&Temples、Deep Blending上显示本方法FPS最高且画质具竞争力，并能与现有加速方法互补。局限：目前仅针对静态场景，动态3DGS与移动端部署是未来方向。

#### CAdam: Context-Adaptive Moment Estimation for 3D Gaussian Densification in Generative Distillation
- 来源: https://arxiv.org/abs/2605.20872
- 源文件: [raw/digest/sources/2026-07-29/arxiv-260520872-0a3c7300.md](/raw/digest/sources/2026-07-29/arxiv-260520872-0a3c7300.md)
- 标题: CAdam：生成式蒸馏中用于3D高斯稠密化的上下文自适应矩估计
- 领域: 3D高斯泼溅与生成式3D
- 关键词: 3D高斯泼溅, 稠密化, 生成式蒸馏, 文生3D, 动量估计, 信噪比门控
- 匹配: 3D高斯泼溅（3DGS）, 显式表示
- 理由: 文档标题与摘要直接以3D Gaussian Splatting（3DGS）的稠密化为核心，第3.1节给出3DGS图元定义，全文围绕生成式3DGS（文生3D）的显式高斯表示展开密度控制研究。
- [ ] 深度阅读
- [ ] 合入 wiki
- [ ] 不感兴趣
- [ ] 不处理

**简介**：CAdam指出生成式3DGS（文生3D）沿用重建式稠密化会因随机监督导致噪声与几何信号混淆，提出把稠密化视为统计信号验证问题。它用动量累积抵消随机噪声、仅保留一致几何漂移，再以分位数与内在SNR门控筛选可靠区域进行克隆/分裂。在多个生成式3DGS主干上，高斯数量减少85%–97%而感知质量基本持平。这是一种即插即用的密度控制模块。

**详细报告**（主要思路与方法流程）：
问题：基于优化的生成式3DGS（如文生3D）沿用重建场景的稠密化机制，但生成式监督是随机伪目标，导致梯度噪声与几何信号纠缠，要么高斯冗余爆炸、要么欠拟合。核心思路：简单来说就是把稠密化从“看梯度大小”改成“看信号是否可靠”——利用动量让随机噪声因正负抵消而消失，只留下一致的几何漂移，再用量化和信噪比门控筛选真正需要细化的区域。方法流程：输入文本提示经SDS/ISM/VFDS等蒸馏优化3DGS；CAdam累积世界空间梯度的一阶矩作信号验证，用分位数排名和内在SNR门控选候选，仅在可靠区域执行克隆/分裂，并用选择性不透明度重置抑制噪声图元。实验在GaussianDreamer、LucidDreamer、FlowDreamer上表明高斯数量降低85%–97%而感知质量相当。局限：阈值仍需调参，底层生成主干的多视角信号不一致时仍可能失败。

#### Learning View-Dependent Splatting Kernels
- 来源: https://arxiv.org/abs/2605.25426
- 源文件: [raw/digest/sources/2026-07-29/arxiv-260525426-cfd1f60d.md](/raw/digest/sources/2026-07-29/arxiv-260525426-cfd1f60d.md)
- 标题: 学习视角相关的泼溅核
- 领域: 3D高斯泼溅与溅射核设计
- 关键词: 3D高斯泼溅, 泼溅核, 视角相关, 可微渲染, 新视角合成, 重心坐标
- 匹配: 3D高斯泼溅（3DGS）
- 理由: 文档第1节与第3节明确以3D Gaussian Splatting（3DGS）的泼溅核为研究对象，提出自动学习视角相关的2D溅射核，直接属于3DGS表示与渲染的改进。
- [ ] 深度阅读
- [ ] 合入 wiki
- [ ] 不感兴趣
- [ ] 不处理

**简介**：本文提出一个可微框架，自动学习溅射管线中视角相关的2D泼溅核，以改善新视角合成的质量与表达效率。方法用投影MLP把3D核潜码转为视角相关的2D核，再由解码器输出以马氏距离度量的径向对称核，避免了一般3D图元线积分的难题。在Mip-NeRF360等四个基准上，体积与平面图元均取得最优或次优重建质量。该工作拓展了3DGS核设计的表达力。

**详细报告**（主要思路与方法流程）：
问题：3DGS等溅射方法的效果高度依赖泼溅核形状，但手工设计的解析核表达力有限，且已有可学习核缺乏视角一致性。核心思路：简单来说就是不直接对3D密度场做难算的线积分，而是显式建模图元投影后的2D核，用一个投影MLP把3D核潜码变成视角相关的2D核，再解码成以马氏距离度量的径向对称形状，从而让核随视角和数据自适应变化。方法流程：每个体积图元含包围椭球和3D核潜码；先投影椭球得2D包围椭圆，再用投影MLP结合椭球位姿把3D核转为2D核潜码；核解码器依像素马氏距离输出不透明度；平面图元同理扩展。实验在4个基准（Mip-NeRF360等）上重建质量与表达效率均优于或持平SOTA。局限：渲染速度低于部分SOTA，未考虑抗锯齿，且未用高级位置编码。

#### SubSplat: High-Resolution Pixel-aligned 3DGS via Sub-pixel Gaussian Reparameterization
- 来源: https://arxiv.org/abs/2607.20813
- 源文件: [raw/digest/sources/2026-07-29/arxiv-260720813-bbde6b0d.md](/raw/digest/sources/2026-07-29/arxiv-260720813-bbde6b0d.md)
- 标题: SubSplat：通过亚像素高斯重参数化实现高分辨率像素对齐3DGS
- 领域: 3D高斯泼溅与新视角合成
- 关键词: 3D高斯泼溅, 像素对齐, 亚像素重参数化, 新视角合成, 前馈网络, 实时渲染
- 匹配: 3D高斯泼溅（3DGS）, 显式表示, 场景表示
- 理由: 文档标题与摘要直接以像素对齐3DGS为核心，第1节与第3节提出Sub-pixel Gaussian Reparameterizer对3D高斯进行亚像素重参数化，属于3DGS显式表示与渲染的直接研究。
- [ ] 深度阅读
- [ ] 合入 wiki
- [ ] 不感兴趣
- [ ] 不处理

**简介**：SubSplat针对像素对齐3DGS高分辨率渲染时的二次方计算瓶颈，提出亚像素高斯重参数化器（SPGR）。它保持低分辨率骨干输入，把每个主高斯细分为多个亚像素子高斯并做保不透明度重分配，从而把输出密度与骨干计算量解耦。结合可变形注意力跨视角聚合特征，该方法以256×256输入渲染512/1024分辨率时PSNR/SSIM优于基线且实现实时。局限是细分因子固定。

**详细报告**（主要思路与方法流程）：
问题：像素对齐的3DGS（前馈高斯预测）在高分辨率渲染时陷入两难——提高输入分辨率会让骨干网络计算量平方增长，而用低分辨率输入则高斯密度不足、出现模糊与光晕。核心思路：简单来说就是不让骨干网络去处理高分辨率，而是维持低分辨率输入，再在输出端把每个主高斯“拆”成多个亚像素子高斯来补密度，从而把细节增强与高昂的骨干计算解耦。方法流程：用MVSplat初始化主高斯；经可变形注意力跨视角聚合几何与外观特征；子像素重参数化器把每个主高斯细分为K个亚像素图元，预测位置/深度/尺度/旋转残差并做保不透明度的权重重分配；用L2+LPIPS损失训练。实验在RealEstate10K与ACID上以256×256输入渲染512/1024分辨率，PSNR/SSIM优于基线且延迟仅42ms。局限：细分因子K固定，对极端遮挡和大视角变化仍敏感。

#### Deformable Triangle Splatting: Flexible Primitives for Real-Time Radiance Field Rendering
- 来源: https://arxiv.org/abs/2607.22446
- 源文件: [raw/digest/sources/2026-07-29/arxiv-260722446-54fc681b.md](/raw/digest/sources/2026-07-29/arxiv-260722446-54fc681b.md)
- 标题: 可变形三角面泼溅：面向实时辐射场渲染的柔性图元
- 领域: 辐射场渲染与显式图元溅射
- 关键词: 三角面泼溅, 辐射场渲染, 表面重建, 实时渲染, 可微渲染, 网格重建
- 匹配: 表面重建, 实时渲染
- 理由: 文档标题与摘要以实时辐射场渲染为核心，并在补充材料S6节给出DTU数据集上的网格重建（TSDF融合）Chamfer距离评估，同时通篇属于溅射/显式表示家族，直接对应兴趣中的“表面重建”与“实时渲染”。
- [ ] 深度阅读
- [ ] 合入 wiki
- [ ] 不感兴趣
- [ ] 不处理

![$\sigma$ and $\delta$ interpretation](https://arxiv.org/html/2607.22446v1/Figures_min/sigma_delta_grid/heart_s0.1_d0.01.jpg)
**$\sigma$ and $\delta$ interpretation**

**简介**：DETRIS（可变形三角面泼溅）给三角形每条边加入K个可学习控制点，使单图元即可表示凹形等非凸形状，用于实时辐射场渲染。所有变形在重心坐标空间完成以保证视角无关，并用环绕数测试、多项式光滑最小距离场与幂律窗函数实现可微渲染。在Mip-NeRF360与Tanks&Temples上作为非体积方法取得最佳LPIPS，并在DTU上实现优于3DGS的网格重建。代价是每像素距离计算使渲染速度略降。

**详细报告**（主要思路与方法流程）：
问题：辐射场渲染中高斯等体积图元难以表达锐利边界与平坦表面，而三角形溅射用刚性三角形又需过度细分才能表示曲线与凹形。核心思路：简单来说就是给每个三角形每条边加K个可学习的控制点，沿边法线方向内外位移，使一个图元就能弯成箭头、月牙等凹形，且所有变形都在重心坐标空间完成以保证视角无关。方法流程：每个三角形由三个顶点定义，每边用K个控制点位移边界；用射线投射环绕数判定像素内外，用多项式光滑最小距离场与幂律窗函数生成平滑不透明度；沿用三角形溅射的剪枝与细分策略并适配可变形边界；用光度+法线一致性等损失优化。实验在Mip-NeRF360与Tanks&Temples上作为非体积方法取得最佳LPIPS，并在DTU上实现优于3DGS的网格重建。局限：每像素距离计算使FPS低于原三角形溅射，且训练时间约2倍。

#### GlossyGS: Inverse Rendering of Glossy Objects with 3D Gaussian Splatting
- 来源: https://arxiv.org/abs/2410.13349
- 源文件: [raw/digest/sources/2026-07-29/arxiv-241013349-glossygs.md](/raw/digest/sources/2026-07-29/arxiv-241013349-glossygs.md)
- 标题: GlossyGS：面向光泽物体逆渲染的 3D 高斯泼溅方法
- 领域: 计算机图形学 / 神经渲染 / 逆渲染
- 关键词: 3D Gaussian Splatting, inverse rendering, glossy objects, BRDF, Cook-Torrance, normal map prefiltering, micro-facet segmentation
- 匹配: 3D高斯泼溅/3DGS, 逆向渲染, 实时渲染
- 理由: 论文直接在 3D-GS 框架内做光泽物体逆渲染，提出法线图预滤波（先 α-blend 材质图再着色，解决镜面反射非线性问题）与微表面几何分割先验（基于 DINOv2+DPT 的粗糙度分割约束），实现几何/材质解耦并达到实时（约 30 FPS）重光照，与 "3DGS 逆渲染" 兴趣高度吻合。
- [ ] 深度阅读
- [ ] 合入 wiki
- [ ] 不感兴趣
- [ ] 不处理

**简介**：GlossyGS 用 3D 高斯泼溅对光泽/高反射物体做逆渲染，从多视角图像恢复几何与材质（反照率、粗糙度、金属度、法线），并支持物理重光照。

**详细报告**（主要思路与方法流程）：
解决的问题：现有 3D-GS 逆渲染方法在漫反射物体上表现好，但难以处理镜面高光与环境反射带来的几何/材质歧义，且着色顺序与微观法线建模不准。
简单来说就是：过去的高斯泼溅把"打光"和"叠加"顺序搞反了，导致反光物体表面糊成一团；本文把顺序调过来并给表面贴上"材质先验"，让反光看起来更真实。
方法流程：
1. 混合显隐式表示：以 COLMAP 稀疏点为 anchor，经 GS 解码器生成神经高斯，材质编码器输出微表面特征并由材质解码器得到 BRDF 属性（适用于 Cook-Torrance 模型）。
2. 法线图预滤波：先将高斯投影出的材质属性图（法线/粗糙度/反照率/金属度）做 α-blend 得到统一表面材质图，再用可微环境光照做基于物理的着色，避免镜面非线性导致的模糊。
3. 微表面几何分割先验：用 DINOv2+DPT 分割模型预测像素级粗糙度类别，并以粗糙度约束损失 L_e 强制同区域内粗糙度一致，消解"低频法线高频粗糙度"与"高频法线低频粗糙度"的歧义。
4. 端到端优化：联合 L1/SSIM 重建损失、平滑正则、粗糙度约束损失、法线损失进行训练。
实验结果：Shiny Blender 上重光照 PSNR 25.72、SSIM 0.930、LPIPS 0.103，法线 MAE 2.82 最优；Stanford-ORB 法线 MAE 1.75；Glossy Synthetic 新视角 PSNR 30.46；训练约 1 小时（V100），渲染约 30 FPS，较 NeRF 方法提速约 4 倍。
局限性：假设远场光照，难以处理近场互反射；对凹面与互反射建模不足，复杂凹面几何易出错。

#### RaDe-GS: Rasterizing Depth in Gaussian Splatting
- 来源: https://arxiv.org/abs/2406.01467
- 源文件: [raw/digest/sources/2026-07-29/arxiv-240601467-radegs.md](/raw/digest/sources/2026-07-29/arxiv-240601467-radegs.md)
- 标题: RaDe-GS：在高斯泼溅中栅格化深度
- 领域: 计算机视觉 / 三维重建 / 高斯泼溅
- 关键词: 3D Gaussian Splatting, depth rasterization, surface normal, surface reconstruction, TSDF, mesh extraction
- 匹配: 3D高斯泼溅/3DGS, 表面重建, 实时渲染
- 理由: 论文针对 3D-GS 难以提取精确几何的痛点，提出在通用 3D 高斯上栅格化计算逐像素空间变化深度与法线（利用局部仿射投影下高斯交点近似共面的性质），并融合 TSDF 提取网格，在 DTU 上 CD 0.68mm 且与 Neuralangelo 竞争的同时保持 3D-GS 的实时效率，与 "3DGS 表面重建" 兴趣直接相关。
- [ ] 深度阅读
- [ ] 合入 wiki
- [ ] 不感兴趣
- [ ] 不处理

**简介**：RaDe-GS 提出一种栅格化的深度/法线计算方法，让通用 3D 高斯泼溅既能保持实时新视角合成，又能高精度重建三维表面并提取网格。

**详细报告**（主要思路与方法流程）：
解决的问题：原始 3D-GS 以高斯中心深度近似几何，离散无结构导致表面粗糙噪声；平面化高斯（SuGaR/2D GS）牺牲渲染质量，光线追踪法（GOF/GSDF）又引入高昂计算开销。
简单来说就是：给每个高斯"切"出一个平面来求深度和法线，像传统光栅化一样逐像素算，而不是用慢速光线追踪，从而既不掉画质又保速度。
方法流程：
1. 推导透视投影下光线与 3D 高斯的"交点"为高斯值最大处（闭式解 t*）。
2. 利用 GS 的局部仿射投影，证明在光线空间中这些交点近似共面，得到深度 d = z_c + p·(Δu, Δv) 的可栅格化线性形式。
3. 由该平面方程求光线空间法线，再用仿射变换矩阵 J 变换回相机空间得到逐像素 3D 法线。
4. 在光度损失 L_c 上增加深度畸变损失 L_d 与法线一致性损失 L_n 约束几何。
5. 训练后渲染各视角深度图，融合进 TSDF 体并用 Marching Cubes 提取网格。
实验结果：DTU 平均 Chamfer 距离 0.68mm（优于 GOF 0.74、2D GS 0.80，媲美 Neuralangelo 0.61）；Tanks&Temples F1 0.40（TSDF 融合类最优）；Synthetic-NeRF PSNR 33.60 最优，Mip-NeRF360 LPIPS 最优；DTU 训练约 8.3 分钟、TNT 约 11.5 分钟，远快于 NeRF 类方法。
局限性：大规模场景 TSDF 融合受显存限制只能用低分辨率体素；对高反射表面处理仍困难，作者建议结合多分辨率 TSDF 与 GaussianShader 类着色改进。

## [可能感兴趣]

#### Mix3R: Mixing Feed-forward Reconstruction and Generative 3D Priors for Joint Multi-view Aligned 3D Reconstruction and Pose Estimation
- 来源: https://arxiv.org/abs/2605.03359
- 源文件: [raw/digest/sources/2026-07-29/arxiv-260503359-880f8b99.md](/raw/digest/sources/2026-07-29/arxiv-260503359-880f8b99.md)
- 标题: Mix3R：混合前馈重建与生成式3D先验以实现联合多视角对齐3D重建与位姿估计
- 领域: 多视角3D重建与相机位姿估计
- 关键词: 3D重建, 相机位姿估计, 前馈重建, 生成式3D, 混合Transformer, 3DGS, NeRF, 网格重建
- 匹配: 网格重建, 表面重建, 神经辐射场
- 理由: 文档第3.1节明确说明TRELLIS解码器可将结构化潜码解码为mesh、3DGS点云或NeRF，整体框架核心是联合3D物体重建与位姿估计，并以显式/隐式表示为最终输出；但本方法的核心创新（MoT对齐、注意力偏置）并非直接针对3DGS或表面重建本身，故判为可能相关。
- [ ] 深度阅读
- [ ] 合入 wiki
- [ ] 不感兴趣
- [ ] 不处理

![The overall architecture of our two-stage framework](https://arxiv.org/html/2605.03359v1/figs/fig_architecture_img.png)
**The overall architecture of our two-stage framework**

**简介**：Mix3R提出将前馈重建（如π³的像素对齐点图）与生成式3D生成（如TRELLIS的稀疏体素）通过混合Transformer（MoT）统一起来，实现多视角对齐的3D物体重建与相机位姿估计。第一阶段联合生成粗体素、点图与位姿，第二阶段基于体素-图像重叠计算注意力偏置，免训练地引导带纹理几何生成。在Toys4K和GSO上，该方法在输入对齐、几何纹理精度与位姿准确性上均优于纯生成与前馈方法。其输出可解码为mesh、3DGS或NeRF等显式/隐式表示。

**详细报告**（主要思路与方法流程）：
问题：多视角3D重建常面临两难——前馈方法只重建可见区域、对视角重叠依赖强，而生成式方法虽能补全几何却与输入图像对齐差。核心思路：简单来说就是把前馈重建（像素对齐点图）和生成式3D生成（稀疏体素）用一个混合Transformer拧在一起，让两者互相提供信息，从而实现既完整又对齐的重建。方法流程：输入多视角无位姿图像，第一阶段用MoT联合生成粗体素、点图和相机位姿及其对齐变换；第二阶段基于体素与图像块的重叠计算注意力偏置，以免训练方式引导带纹理几何生成，并用可微渲染精修相机。实验在Toys4K与GSO上表明本方法在输入对齐、几何纹理精度与位姿估计上均优于TRELLIS、ReconViaGen等。局限：测试视角偏离训练分布时性能可能下降，且受限于TRELLIS冻结解码器与合成训练数据的光照表现。

#### CGVQM: Computer Graphics Video Quality Metric
- 来源: https://github.com/IntelLabs/cgvqm
- 源文件: [raw/digest/sources/2026-07-29/cgvqm.md](/raw/digest/sources/2026-07-29/cgvqm.md)
- 标题: CGVQM：面向计算机图形的视频质量评价指标
- 领域: 渲染质量评估 / 视频质量指标 / 计算机图形
- 关键词: video quality metric, computer graphics, full-reference, perceptual, CGVQD, rendering artifacts
- 匹配: 可能相关（渲染画质评测，非 3DGS 核心）
- 理由: CGVQM 是首个针对先进渲染技术失真（空间+时序伪影）校准的全参考视频质量指标，并配套 CGVQD 数据集；虽不直接研究 3DGS/神经渲染，但可作为实时渲染（含 3DGS）画质评测工具，故判为可能相关。关联论文 arXiv 2506.11546（CGVQM+D, CGF 2025）。
- [ ] 深度阅读
- [ ] 合入 wiki
- [ ] 不感兴趣
- [ ] 不处理

**简介**：CGVQM 是 Intel 提出的全参考视频质量指标，预测两路视频（参考 vs 失真）之间的感知差异；首个针对现代计算机图形渲染失真（模糊、噪声、走样等空间与时序伪影）做校准，并输出可解释的感知等级与误差热力图。

**详细报告**（主要思路与方法流程）：
解决的问题：现有视频质量指标（PSNR/SSIM）主要针对自然视频压缩失真，未校准计算机图形渲染特有的失真（如实时光栅化/神经渲染产生的时序闪烁、几何走样）。
简单来说就是：给渲染出来的画面打一个"人眼看有多糟"的分，且专门考虑游戏/实时图形里才会有的那种失真，而不是传统视频压缩失真。
方法流程：
1. 在 CGVQD 数据集（覆盖风格化、写实开放世界及多种渲染技术的失真样本）上训练/校准全参考网络。
2. 输入参考帧与失真帧对，输出单一感知分数（imperceptible→annoying 的可解释区间）。
3. 同时输出误差图（error map），可视化错误出现的位置与原因。
4. 提供 PyTorch/CUDA 实现与训练脚本（cgvqm.py / train.py），可作为渲染管线的画质评测工具。
实验结果：论文（CGVQM+D, CGF 2025）在 CGVQD 上给出指标校准与对比结果；作为指标侧重于对渲染失真的敏感度与可解释性，而非重建精度。
局限性：关注渲染画质评价本身，不直接改进 3DGS/神经渲染的生成或重建质量；与 wiki 核心兴趣（3DGS/表面重建）仅间接相关。

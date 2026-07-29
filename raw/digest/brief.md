# 资讯简报  2026-07-29


## [感兴趣]

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
- [x] 已合入 wiki
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

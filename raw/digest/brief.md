# 资讯简报  2026-07-28


## [感兴趣]

#### Proxy-GS: Unified Occlusion Priors for Training and Inference in Structured 3D Gaussian Splatting
- 来源: https://arxiv.org/abs/2509.24421
- 源文件: [raw/digest/sources/2026-07-28/arxiv-250924421-bd77fe07.md](/raw/digest/sources/2026-07-28/arxiv-250924421-bd77fe07.md)
- 标题: Proxy-GS: 利用代理实现高斯遮挡感知以提升3DGS效率
- 领域: 3D重建/计算机图形学
- 关键词: 3D高斯泼溅, 遮挡剔除, 实时渲染, 场景重建, 显式表示
- 匹配: 3D高斯泼溅
- 理由: 直接针对3DGS在大规模场景中的冗余和高计算成本问题，提出基于代理的遮挡感知优化方案
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

![Proxy-GS 框架](https://arxiv.org/html/2509.24421v5/figures/framework.png)
**Proxy-GS 框架**
Proxy-GS 框架。我们首先构建一个轻量级 proxy mesh。渲染时，硬件光栅化在 1 ms 内生成深度图，用于高效剔除被遮挡的 anchor。训练时，在同样的渲染管线基础上，进一步引入结构感知的 anchor 稠密化，促使 anchor 沿着 proxy mesh 几何自适应生长。

**简介**：提出Proxy-GS方法，通过快速代理系统引入遮挡深度图，优化高斯锚点剔除与密化过程，显著加速渲染并提升遮挡场景下的视觉质量。

**详细报告**（主要思路与方法流程）：
3DGS在大规模场景中存在严重的计算冗余问题。Proxy-GS提出<1ms即可产出1000×1000分辨率遮挡深度图的快速代理系统，在训练时引导锚点向表面密化避免遮挡区域不一致，在推理时剔除被遮挡的高斯基元加速渲染。在MatrixCity Streets等重度遮挡场景下，Proxy-GS比Octree-GS实现2.5倍加速同时提升渲染质量。

#### Spherical Voronoi: Directional Appearance as a Differentiable Partition of the Sphere
- 来源: https://arxiv.org/abs/2512.14180
- 源文件: [raw/digest/sources/2026-07-28/arxiv-251214180-81c10972.md](/raw/digest/sources/2026-07-28/arxiv-251214180-81c10972.md)
- 标题: 球面Voronoi：可微球面划分的方向外观表示
- 领域: 3D重建/计算机图形学
- 关键词: 3D高斯泼溅, 球面Voronoi, 外观表示, 镜面反射, 球谐函数
- 匹配: 3D高斯泼溅
- 理由: 提出球面Voronoi划分替代球谐函数作为3DGS的外观表示，解决SH无法表示高频信号和镜面反射的根本缺陷
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

![延迟渲染管线——2DGS场景光栅化为位置、法线等缓冲，SV在延迟着色阶段逐像素评估](https://arxiv.org/html/2512.14180/figures/pipeline.png)
**延迟渲染管线——2DGS场景光栅化为位置、法线等缓冲，SV在延迟着色阶段逐像素评估**
延迟渲染管线——2DGS场景光栅化为位置、法线等缓冲，SV在延迟着色阶段逐像素评估

**简介**：提出球面Voronoi (SV) 作为3DGS中的统一外观表示框架。SV将方向域划分为可学习平滑边界区域，对漫反射外观达到竞争效果。对于反射采用SV作为可学习反射探针，在合成和真实数据集上达到SOTA。

**详细报告**（主要思路与方法流程）：
Spherical Harmonics (SH) 作为3DGS的默认外观表示存在根本性局限：无法表示高频信号、产生Gibbs ringing伪影、无法捕获镜面反射。SV通过可微分球面划分替代SH，每个Voronoi单元有平滑边界可优化。对漫反射外观优化更简单直观，对镜面反射则利用传统图形学中的反射方向输入作为反射探针。同时解决了SH的高频限制和球面高斯(SG)的优化复杂度问题。

#### Adaptive Shells for Efficient Neural Radiance Field Rendering
- 来源: https://arxiv.org/abs/2311.10091
- 源文件: [raw/digest/sources/2026-07-28/arxiv-231110091-c74a8bff.md](/raw/digest/sources/2026-07-28/arxiv-231110091-c74a8bff.md)
- 标题: 自适应壳层：高效神经辐射场渲染
- 领域: 神经渲染
- 关键词: 神经辐射场, 表面渲染, 体积渲染, 网格包络, 实时渲染
- 匹配: 神经辐射场, 场景表示, 实时渲染
- 理由: 构建显式网格包络面约束神经体积表示，在表面区域退化为单采样点渲染，大幅加速NeRF渲染
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

![方法概览——自适应壳层通过显式薄壳包围神经隐式场景，在壳内高效采样实现高保真渲染](https://ar5iv.labs.arxiv.org/html/2311.10091/assets/x3.png)
**方法概览——自适应壳层通过显式薄壳包围神经隐式场景，在壳内高效采样实现高保真渲染**
方法概览——自适应壳层通过显式薄壳包围神经隐式场景，在壳内高效采样实现高保真渲染

**简介**：构建显式网格包络面空间约束神经体积表示。通过学习空间变化核大小，在固体区域退化为单采样点表面渲染，在体积区域保留多采样。提取的网格可用于动画和仿真。

**详细报告**（主要思路与方法流程）：
神经辐射场虽质量高但采样成本大。基于“多数场景由固体表面构成”的观察，提出自适应壳层：用NeuS推广到学习空间变化的核大小，编码密度分布宽度。宽核拟合体积区域，窄核拟合表面。然后提取核确定宽度范围的窄带网格包络面，在包络内微调辐射场。推理时射线仅需在包络内采样，大幅减少采样数量。网格包络还可用于动画和仿真等下游任务。

#### SuGaR: Surface-Aligned Gaussian Splatting for Efficient 3D Mesh Reconstruction
- 来源: https://arxiv.org/abs/2311.12775
- 源文件: [raw/digest/sources/2026-07-28/arxiv-231112775-6b1b0a2c.md](/raw/digest/sources/2026-07-28/arxiv-231112775-6b1b0a2c.md)
- 标题: SuGaR：面向高效网格重建的表面对齐高斯泼溅
- 领域: 3D重建/计算机图形学
- 关键词: 3D高斯泼溅, 网格重建, 表面重建, 泊松重建, 可编辑网格
- 匹配: 3D高斯泼溅, 网格重建, 表面重建
- 理由: 从3DGS提取网格的第一个系统方法，正则化高斯与表面对齐后通过泊松重建提取网格
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

**简介**：提出从3DGS高斯点中提取网格的首个方法。正则化项使高斯与表面对齐，利用泊松重建快速提取高质量网格。提供将高斯绑定到网格表面的可选项，支持编辑、雕刻、动画和重照明。

**详细报告**（主要思路与方法流程）：
3DGS能实现逼真渲染但难以提取网格。SuGaR通过正则化项促使数万个微小的3D高斯点与场景表面对齐，利用泊松重建从对齐的高斯点快速提取高质量网格。进一步的可选细化策略将高斯绑定到网格表面并联合优化GS和网格，使GS可编辑。整个过程数分钟完成，比SDF方法快数量级，同时渲染质量优于SDF。

#### Volumetric Surfaces: Representing Fuzzy Geometries with Layered Meshes
- 来源: https://arxiv.org/abs/2409.02482
- 源文件: [raw/digest/sources/2026-07-28/arxiv-240902482-7d990975.md](/raw/digest/sources/2026-07-28/arxiv-240902482-7d990975.md)
- 标题: 体积表面：多层网格表示的模糊几何
- 领域: 实时渲染
- 关键词: 多层网格, 体积渲染, 实时渲染, SDF壳层, 移动端渲染
- 匹配: 场景表示, 实时渲染
- 理由: 提出半透明多层网格表示，兼具表面渲染速度和体积渲染的模糊几何建模能力，与场景表示和实时渲染高度相关
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

![体积表面多层网格表示——k-SDF定义k个带透明度的隐式表面](https://arxiv.org/html/2409.02482v2/x4.png)
**体积表面多层网格表示——k-SDF定义k个带透明度的隐式表面**
体积表面多层网格表示——k-SDF定义k个带透明度的隐式表面，按固定顺序合成渲染

**简介**：将物体表示为半透明多层网格，固定顺序渲染免除排序。学习SDF壳层最优间距后烘培为网格+UV纹理。模糊物体用多层表示建模，在低功耗设备上实时渲染。

**详细报告**（主要思路与方法流程）：
表面渲染快但难以建模模糊几何，体积/泼溅渲染表现好但需要大量采样和排序。Volumetric Surfaces将两者优势结合：多层网格在空间上堆叠，每层是SDF壳层，层间间距在学习过程中自动确定。训练完成后烘培为网格+UV纹理。渲染时固定顺序从内到外alpha混合，不需要排序。在模糊物体（毛发、烟雾）上优于单表面方法，在速度和能效上优于体积方法，可在笔记本和手机上实时运行。

#### Ref-DGS: Reflective Dual Gaussian Splatting
- 来源: https://arxiv.org/abs/2603.07664
- 源文件: [raw/digest/sources/2026-07-28/arxiv-260307664-8748a994.md](/raw/digest/sources/2026-07-28/arxiv-260307664-8748a994.md)
- 标题: Ref-DGS：反射双高斯泼溅
- 领域: 3D重建/计算机图形学
- 关键词: 3D高斯泼溅, 镜面反射, 双高斯表示, 环境反射, 逆向渲染
- 匹配: 3D高斯泼溅, 表面重建
- 理由: 直接针对3DGS在反射表面重建的挑战，提出双高斯场景表示解耦表面与反射
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

![Ref-DGS 框架概览](https://arxiv.org/html/2603.07664v3/x2.png)
**Ref-DGS 框架概览**
Ref-DGS 框架概览

**简介**：提出反射双高斯泼溅框架，用几何高斯+局部反射高斯+全局环境反射场解耦表面重建与镜面反射。轻量物理感知着色器融合全局/局部镜面特征，训练速度远快于光追方法。

**详细报告**（主要思路与方法流程）：
反射表面尤其是近场镜面反射是3DGS重建的根本挑战。Ref-DGS引入双高斯场景表示：几何高斯负责表面重建，互补的局部反射高斯捕获近场镜面交互（无需显式光追），全局环境反射场建模远场镜面反射。物理感知的自适应混合着色器融合全局和局部镜面特征。在反射场景上达到SOTA，训练速度远快于基于光追的高斯方法。

#### JointEdit3D: Feed-Forward 3D Scene Editing in a Unified Latent Space
- 来源: https://arxiv.org/abs/2606.13345
- 源文件: [raw/digest/sources/2026-07-28/arxiv-260613345-5b8f3898.md](/raw/digest/sources/2026-07-28/arxiv-260613345-5b8f3898.md)
- 标题: JointEdit3D：统一潜空间中的前馈3D场景编辑
- 领域: 3D场景编辑
- 关键词: 3D场景编辑, RGB-几何重建, 潜空间, 神经场景表示, 数据集
- 匹配: 场景表示
- 理由: 3D场景编辑依赖RGB-几何联合重建潜空间，与场景表示和3D重建直接相关
- [ ] 深度阅读
- [ ] 合入 wiki
- [ ] 不感兴趣

![JointEdit3D 管线](https://arxiv.org/html/2606.13345v1/x1.png)
**JointEdit3D 管线**
JointEdit3D 管线。JointEdit3D 从源视频和一帧编辑后的参考帧执行 RGB-几何联合潜在空间修补。

**简介**：基于统一RGB-几何重建生成潜空间的3D场景编辑方法。不对称潜空间修补：单张编辑后RGB潜变量在源场景锚定下生成其余RGB视图和几何。发布15K配对数据集和100样本基准。

**详细报告**（主要思路与方法流程）：
现有3D场景编辑方法通常分别处理RGB和几何，难以保证多视图一致性。JointEdit3D将RGB重建和几何重建整合到单一生成潜空间。不对称潜空间修补以编辑后单视图RGB潜变量为起点，在SceneAnchor Branch引导下联合预测其余RGB视图和完整几何。编辑/背景感知损失平衡编辑区域与未编辑内容保真度。在自建15K数据集上展示优于现有方法的多视图一致性和几何保真度。

#### MoVerse: Real-Time Video World Modeling with Panoramic Gaussian Scaffold
- 来源: https://arxiv.org/abs/2606.13376
- 源文件: [raw/digest/sources/2026-07-28/arxiv-260613376-13213e60.md](/raw/digest/sources/2026-07-28/arxiv-260613376-13213e60.md)
- 标题: MoVerse：基于全景高斯骨架的实时视频世界建模
- 领域: 3D重建/神经渲染
- 关键词: 3D高斯泼溅, 场景表示, 视频世界模型, 全景合成, 实时渲染
- 匹配: 3D高斯泼溅, 场景表示, 实时渲染
- 理由: 直接利用3DGS作为核心表示形式，从单图构建可交互视频世界，完全契合3DGS及场景表示兴趣
- [ ] 深度阅读
- [ ] 合入 wiki
- [ ] 不感兴趣

![MoVerse 管线概览](https://ar5iv.labs.arxiv.org/html/2606.13376/assets/pipeline_overview.png)
**MoVerse 管线概览**
MoVerse 管线概览。从一张窄视场输入图像出发，Stage I 合成对齐重力的 360° 全景图，Stage II 将全景图提升为持久化的 3D Gaussian 支架，Stage III 沿用户指定的相机轨迹渲染高斯条件视频，实现实时交互漫游。

**简介**：从单张窄视场图像创建可交互导航场景。先扩散扩展为360°全景，提升为3D高斯骨架，再通过高斯条件视频渲染器沿用户轨迹生成视频。RTX 4090上8 FPS实时漫游。

**详细报告**（主要思路与方法流程）：
MoVerse将世界构建与观测渲染分离：用拓扑感知扩散将单图补全为重力对齐360°全景，用全景几何感知残差预测将全景提升为持久3D高斯骨架。高斯条件视频渲染器将骨架渲染沿用户轨迹转为视频。双向扩散教师→因果自回归学生蒸馏实现低延迟流式输出。结合了显式3D表示的鲁棒性和生成视频模型的画质。

#### Extracting Neural Materials from Multi-view Images
- 来源: https://arxiv.org/abs/2606.26715
- 源文件: [raw/digest/sources/2026-07-28/Extracting-Neural-Materials-from-Multi-view-Images.md](/raw/digest/sources/2026-07-28/Extracting-Neural-Materials-from-Multi-view-Images.md)
- 标题: 从多视图图像中提取神经材质
- 领域: 神经渲染
- 关键词: 神经材质, 多视图重建, 逆渲染, 不确定性建模, 材质分解
- 匹配: 场景表示, 神经辐射场
- 理由: 从多视图提取空间变化神经材质，涉及场景级材质重建和神经表示
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

![NeuMatEx 包含两个阶段](https://arxiv.org/html/2606.26715v2/figures/images/system_v2.png)
**NeuMatEx 包含两个阶段**
NeuMatEx 包含两个阶段。(a) 神经材质初始化：LMRM 单次前向预测特征 triplane，由两个 MLP 解码为神经材质和不确定性。(b) 测试时优化：通过可微分路径追踪进一步优化。

**简介**：训练Large Material Reconstruction Model(LMRM)预测初始基础色、神经材质潜变量和不确定性。不确定性引导防止光照镜像烘培入材质。

**详细报告**（主要思路与方法流程）：
神经材质紧凑表示复杂镜面效果但难以优化。LMRM从多视图直接预测初始值和偶然不确定性：高不确定区域（镜面高光、复杂光照）允许自由调整，低不确定区域（漫反射）强制靠近预测。有效分离光照和材质。局限：需要多视图输入，极端光照条件处理有限。

#### GS-2M: Material-aware Gaussian Splatting for High-fidelity Mesh Reconstruction
- 来源: https://arxiv.org/abs/2509.22276
- 源文件: [raw/digest/sources/2026-07-28/GS-2M-Material-aware-Gaussian-Splatting-for-High-fidelity-Mesh-Reconstruction.md](/raw/digest/sources/2026-07-28/GS-2M-Material-aware-Gaussian-Splatting-for-High-fidelity-Mesh-Reconstruction.md)
- 标题: GS-2M：材料感知的高保真网格重建高斯泼溅
- 领域: 3D重建
- 关键词: 3D高斯泼溅, 网格重建, 材质分解, 表面重建, 反射表面
- 匹配: 3D高斯泼溅, 网格重建, 表面重建
- 理由: 基于3DGS的网格重建方法，专门解决高反射表面重建问题
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

![从 Shiny Blender Synthetic 数据集上重建的反射物体 mesh，实验对比了 2DGS、GOF 和 PGSR 等方法](https://arxiv.org/html/2509.22276v2/figures/sota-reflective.jpg)
**从 Shiny Blender Synthetic 数据集上重建的反射物体 mesh，实验对比了 2DGS、GOF 和 PGSR 等方法**
从 Shiny Blender Synthetic 数据集上重建的反射物体 mesh，实验对比了 2DGS、GOF 和 PGSR 等方法。

**简介**：材料感知的网格重建优化框架。联合优化影响渲染深度和法线质量的属性，基于多视图光度变化的粗糙度监督消除复杂神经组件。在反射表面上也能输出精确三角网格。

**详细报告**（主要思路与方法流程）：
3DGS显式表示方法在新型视图合成中表现优异，但高反射表面重建仍是难题。GS-2M联合优化与渲染深度和法线质量相关的属性，保持几何细节同时对反射表面鲁棒。基于多视图光度变化的粗糙度监督策略替代复杂神经组件。在多个数据集上验证，在反射表面也能达到SOTA网格重建质量。

#### Bake It Till You Make It: Ultrafast Spatial Texture-Atlas Splatting
- 来源: https://arxiv.org/abs/2607.13808
- 源文件: [raw/digest/sources/2026-07-28/Bake-It-Till-You-Make-It-Ultrafast-Spatial-Texture-Atlas-Splatting.md](/raw/digest/sources/2026-07-28/Bake-It-Till-You-Make-It-Ultrafast-Spatial-Texture-Atlas-Splatting.md)
- 标题: 烘培直到成功：超快空间纹理图集泼溅
- 领域: 实时渲染
- 关键词: 3D高斯泼溅, 纹理图集, 实时渲染, surfel, 哈希网格
- 匹配: 3D高斯泼溅, 实时渲染
- 理由: 对3DGS的辐射度表示进行解耦优化，将高频纹理烘培到纹理图集实现5倍加速，直接提升3DGS渲染效率
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

![方法概览](https://arxiv.org/html/2607.13808v1/x2.png)
**方法概览**
方法概览。训练过程中，球面颜色模型捕捉视角依赖性，空间视角无关的颜色通过多分辨率哈希网格学习。训练后将哈希网格采样到纹理图集用于推理。

**简介**：解耦辐射度表示：低频几何+视角相关外观用2D surfel，高频纹理烘培到纹理图集。稀疏性优化激进裁剪surfel，比3DGS加速5倍，消费硬件上4K 60FPS。

**详细报告**（主要思路与方法流程）：
3DGS的哈希网格外观参数化细粒度高但片段渲染成本大。该工作将辐射度解耦为：2D surfel建模低频几何和视角相关外观，视角无关的空间哈希网格烘培到紧凑纹理图集表示高频纹理。稀疏性增强优化（惩罚半透明和逐基元衰减）激进裁剪不重要surfel，实现稀疏且快速的表示。比3DGS达5倍加速，4K 60FPS实时渲染。

#### Native and Compact Structured Latents for 3D Generation
- 来源: https://arxiv.org/abs/2512.14692
- 源文件: [raw/digest/sources/2026-07-28/arxiv-251214692-f7110812.md](/raw/digest/sources/2026-07-28/arxiv-251214692-f7110812.md)
- 标题: 面向3D生成的原生紧凑结构化潜变量
- 领域: 3D生成
- 关键词: 3D生成, 结构化潜变量, 体素表示, 流匹配, PBR材质
- 匹配: 场景表示, 显式表示
- 理由: 从原生3D数据学习结构化潜变量O-Voxel，统一编码几何和PBR材质，直接对应场景表示和显式表示
- [ ] 深度阅读
- [ ] 合入 wiki
- [ ] 不感兴趣

![方法概览](https://arxiv.org/html/2512.14692v1/x1.png)
**方法概览**
方法概览。我们引入 O-Voxel 用于形状和材质表示。

**简介**：提出O-Voxel表示统一编码几何和PBR材质，支持任意拓扑。基于此训练4B参数流匹配3D生成模型，质量和材质远超现有模型。

**详细报告**（主要思路与方法流程）：
现有方法依赖2D扩散或多视图重建。该工作从原生3D数据学习O-Voxel表示（体素级几何+PBR材质），支持开流形、非流形等任意拓扑。稀疏压缩VAE实现体素到紧凑潜变量的高效压缩。4B参数流匹配模型直接从原生3D数据生成，无需2D中间监督。展示了scaling law在3D生成中的有效性。局限：体素分辨率限制细粒度细节。

## [可能感兴趣]

### TransGI-Real-Time-Dynamic-Global-Illumination-With-Object-Centric-Neural-Transfer-Model.md
  ↳ 包含 1 条资讯

#### TransGI: Real-Time Dynamic Global Illumination With Object-Centric Neural Transfer Model
- 来源: https://arxiv.org/abs/2506.09909
- 源文件: [raw/digest/sources/2026-07-28/TransGI-Real-Time-Dynamic-Global-Illumination-With-Object-Centric-Neural-Transfer-Model.md](/raw/digest/sources/2026-07-28/TransGI-Real-Time-Dynamic-Global-Illumination-With-Object-Centric-Neural-Transfer-Model.md)
- 标题: TransGI：以物体为中心的神经迁移模型实时全局光照
- 领域: 实时渲染
- 关键词: 全局光照, 实时渲染, 神经渲染, MLP, 动态场景
- 匹配: 实时渲染
- 理由: 实时全局光照与实时渲染直接对应，但不涉及3DGS或场景表示方法，与核心兴趣3DGS距离较远
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

![方法管线](https://arxiv.org/html/2506.09909v1/x2.png)
**方法管线**
方法管线。指定新视角后，渲染引擎生成 G-Buffer 和特征图，通过神经迁移解码器输出迁移系数，与光照系数相乘得到渲染图像。

**简介**：以物体为中心的神经迁移模型：MLP解码器+顶点附加潜特征表达材质，支持光泽效果且内存开销低。局部光照探针+跨探针辐射共享实现动态光照下每帧<10ms实时渲染。

**详细报告**（主要思路与方法流程）：
实时动态全局光照是图形学长期挑战。TransGI以物体为中心设计：每个物体顶点附带潜特征表示材质，MLP解码器从顶点特征渲染光照颜色。局部探针捕获空间入射辐射，跨探针辐射共享减少冗余计算。每帧<10ms满足实时需求。局限：间接光质量依赖探针密度，复杂场景可能退化。

#### TopoMesh: High-Fidelity Mesh Autoencoding via Topological Unification
- 来源: https://arxiv.org/abs/2603.24278
- 源文件: [raw/digest/sources/2026-07-28/TopoMesh-High-Fidelity-Mesh-Autoencoding-via-Topological-Unification.md](/raw/digest/sources/2026-07-28/TopoMesh-High-Fidelity-Mesh-Autoencoding-via-Topological-Unification.md)
- 标题: TopoMesh：基于拓扑统一的高保真网格自编码
- 领域: 3D生成/几何处理
- 关键词: 网格自编码, VAE, 拓扑统一, Dual Marching Cubes, 3D生成
- 匹配: 网格重建, 场景表示
- 理由: 聚焦网格VAE拓扑统一和重建保真度，与网格重建和显式表示相关，但核心是生成而非新型视图合成或实时渲染
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

![TopoMesh 包含两个核心模块](https://arxiv.org/html/2603.24278v2/x1.png)
**TopoMesh 包含两个核心模块**
TopoMesh 包含两个核心模块。Topo-Remesh 将真实网格转换为 DMC 格式表示。Topo-VAE 以顶点和法线为输入重建网格。

**简介**：基于稀疏体素的VAE，通过Dual Marching Cubes统一GT网格和预测网格的拓扑结构。在顶点/面层级建立显式对应，获得拓扑/顶点/面朝向的显式监督。显著提升重建保真度，特别是锐边和几何细节。

**详细报告**（主要思路与方法流程）：
3D生成中VAE的重建能力决定生成质量上限。现有VAE面临GT网格（任意拓扑）和预测网格（固定结构隐式场）的表示不匹配。TopoMesh引入DMC框架统一拓扑：通过L∞度量重网格将任意输入转为DMC兼容格式，解码器输出同样DMC格式。顶点/面层级显式对应允许拓扑、顶点位置和面朝向的显式监督信号。训练采用Teacher Forcing和渐进分辨率。在重建保真度上显著优于现有VAE。

#### Surflo: Consistent 3D Surface Flow Model with Global State
- 来源: https://arxiv.org/abs/2606.13644
- 源文件: [raw/digest/sources/2026-07-28/arxiv-260613644-a3aea4c1.md](/raw/digest/sources/2026-07-28/arxiv-260613644-a3aea4c1.md)
- 标题: Surflo：具有全局状态的连贯3D表面流模型
- 领域: 3D重建
- 关键词: 3D重建, 流匹配, 表面重建, 全局状态, 点云生成
- 匹配: 场景表示, 表面重建
- 理由: 从前馈角度做3D表面重建，压缩多视图为全局隐状态并通过流匹配生成表面点，与场景表示和表面重建相关
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

![Surflo 的三个关键组成部分](https://arxiv.org/html/2606.13644v1/x2.png)
**Surflo 的三个关键组成部分**
Surflo 的三个关键组成部分。编码器用 VGGT+Perceiver 压缩多视图为固定潜变量。解码器将查询扩散为表面速度。

**简介**：将任意数量未定位RGB视图压缩为K个隐式token全局状态，通过流匹配从噪声解码为定向3D表面点。支持可变分辨率，推理时注入光度梯度关联邻近点。

**详细报告**（主要思路与方法流程）：
现有前馈方法每视图输出未对齐点云或固定分辨率。Surflo将变数量未定位视图压缩为全局隐token，然后通过流匹配独立从噪声传输到表面生成定向点。输出分辨率自由，单一隐状态可解码数千到百万点。推理时光度梯度引导邻近点保持一致，避免局部不一致。比前馈基线匹配或更优，比优化方法快一个数量级。

#### World Tracing: Generative Pixel-Aligned Geometry Beyond the Visible
- 来源: https://arxiv.org/abs/2606.13652
- 源文件: [raw/digest/sources/2026-07-28/arxiv-260613652-a19415e2.md](/raw/digest/sources/2026-07-28/arxiv-260613652-a19415e2.md)
- 标题: World Tracing：超越可视范围的生成式像素对齐几何
- 领域: 3D重建/计算机视觉
- 关键词: 3D重建, 像素对齐, 几何生成, 遮挡重建, 扩散变换器
- 匹配: 场景表示, 表面重建
- 理由: 提出像素对齐多层几何表示，重建可见表面同时生成遮挡部分几何，与场景表示和重建相关但侧重于几何补全
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

![WT-DiT 架构](https://arxiv.org/html/2606.13652v1/x3.png)
**WT-DiT 架构**
WT-DiT 架构。MoGe 编码器提供像素对齐图像特征，带噪多层 XYZ 经 patch 化后与图像特征融合，送入 DiT 解码器。

**简介**：生成式像素对齐几何表示。对每个像素预测对齐3D点堆栈（第一层可见表面，后续层遮挡表面）。基于World-Tracing Diffusion Transformer，多几何层作为独立去噪token。

**详细报告**（主要思路与方法流程）：
现有深度估计器仅预测可见表面，图生3D模型完整但不对齐输入。World Tracing结合两者：预测有序相机空间3D点堆栈，第一层表示可见表面，后续层表示从前到后的遮挡表面。WT-DiT将多层几何作为独立去噪token，通过因子化和全局注意力耦合。像素空间流匹配+混合噪声调度平衡可见表面重建和遮挡几何生成。在物体/场景/动态基准上均优于深度预测器和图生3D模型。支持文本驱动3D编辑和几何条件新视角视频合成。

#### Toward Richer Material Generation via Procedural Data Enhancement
- 来源: https://arxiv.org/abs/2606.14988
- 源文件: [raw/digest/sources/2026-07-28/Toward-Richer-Material-Generation-via-Procedural-Data-Enhancement.md](/raw/digest/sources/2026-07-28/Toward-Richer-Material-Generation-via-Procedural-Data-Enhancement.md)
- 标题: 通过程序化数据增强实现更丰富的材质生成
- 领域: 材质生成
- 关键词: 材质生成, 程序化增强, 神经材质, 扩散模型, PBR
- 匹配: 场景表示
- 理由: 涉及神经材质表示和生成，与场景表示相关，但核心是材质而非完整场景
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

![简单的 PBR 材质模型无法复现真实材料的复杂表面效果，例如双重高光、灰尘、清漆层或半透明薄层](https://arxiv.org/html/2606.14988v1/figures/haze.jpg)
**简单的 PBR 材质模型无法复现真实材料的复杂表面效果，例如双重高光、灰尘、清漆层或半透明薄层**
简单的 PBR 材质模型无法复现真实材料的复杂表面效果，例如双重高光、灰尘、清漆层或半透明薄层。

**简介**：将简单PBR材质程序化增强为多层模型（灰尘、清漆、分层散射），编码为6D潜空间神经材质。微调视频扩散模型生成神经潜纹理。

**详细报告**（主要思路与方法流程）：
高质量PBR材质获取成本高。该工作将单GGX高光瓣PBR通过程序化规则增强为多层材质。增强后材质编码到共享6D潜空间（双潜纹理+通用MLP解码），实现紧凑连续的材质表示。视频扩散模型在潜空间生成，利用时间一致性学习材质参数。局限：程序化规则覆盖不完全，MLP表达能力有限。

#### Arm Neural Technology for Mobile Games
- 来源: 
- 源文件: [raw/digest/sources/2026-07-28/developer.arm.com-mobile-graphics-and-gaming-neural-technology.md](/raw/digest/sources/2026-07-28/developer.arm.com-mobile-graphics-and-gaming-neural-technology.md)
- 标题: Arm移动端神经图形技术
- 领域: 移动端实时图形
- 关键词: 神经超采样, 实时渲染, 移动GPU
- 匹配: 实时渲染
- 理由: AI驱动的实时渲染画质提升，与实时渲染相关但为产品介绍非技术方法
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

**简介**：Arm神经技术套件：NSS/NFRU/NSSD覆盖超采样/帧率提升/去噪。移动端AI推理降低GPU负载。

**详细报告**（主要思路与方法流程）：
Arm在移动端部署的神经渲染技术，包括时域超采样和帧生成，目标减少GPU像素着色负载。与Sumo Digital合作生产级游戏Neural Dawn展示。优势：本地推理无云端依赖。局限：延迟敏感场景中推理时间不可忽视。

#### Arm Neural Super Sampling on HuggingFace
- 来源: 
- 源文件: [raw/digest/sources/2026-07-28/huggingface.co-Arm-neural-super-sampling.md](/raw/digest/sources/2026-07-28/huggingface.co-Arm-neural-super-sampling.md)
- 标题: Arm神经超采样模型发布页
- 领域: 移动端实时图形
- 关键词: 神经超采样, 移动GPU, 模型部署
- 匹配: 实时渲染
- 理由: 神经超采样技术用于实时渲染画质提升，但内容为模型发布和集成指南
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

**简介**：Arm在HuggingFace发布NSS模型，移动端时域超采样，低分辨率→高分辨率上采样节省GPU。

**详细报告**（主要思路与方法流程）：
与Arm Neural Technology同产品线的模型发布。提供三种质量模式权衡画质和性能。局限：快速运动可能拖影。

#### Rectified Flow
- 来源: 
- 源文件: [raw/digest/sources/2026-07-28/www.cs.utexas.edu-lqiang-rectflow-html-intro.html.md](/raw/digest/sources/2026-07-28/www.cs.utexas.edu-lqiang-rectflow-html-intro.html.md)
- 标题: Rectified Flow教程
- 领域: 生成模型
- 关键词: rectified flow, ODE, 扩散模型
- 匹配: 无
- 理由: Rectified Flow是3D生成中流匹配的基础方法，与3DGS之外的3D生成技术链相关
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

**简介**：Rectified Flow教程：通过学习ODE在两个分布间找传输映射，核心在直线路径和重流快速生成。

**详细报告**（主要思路与方法流程）：
连接扩散模型和神经ODE的生成方法。学习从噪声到数据的ODE轨迹并鼓励走直线，减少推理步数。重流逐步矫正路径使其更直，更接近最优传输。直路径优势：推理步数少，质量高。局限：直路径假设可能限制表达力。

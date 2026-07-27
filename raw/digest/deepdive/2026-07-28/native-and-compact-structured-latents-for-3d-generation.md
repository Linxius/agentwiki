# Native and Compact Structured Latents for 3D Generation

## Native and Compact Structured Latents for 3D Generation — 深度阅读报告

> arXiv: 2512.14692 | Microsoft Research + Tsinghua + USTC | TRELLIS.2 项目

---

## 论文概览

### 1. 问题与背景

**解决的问题：** 3D 生成领域缺少一种既能完整表示任意拓扑（开曲面、非流形、全封闭结构）又能承载 PBR（基于物理的渲染）材质信息的结构化表示，且该表示需要足够紧凑以支持高效高分辨率生成。

**之前怎么做：** 主流大模型（CLAY、Direct3D、TRELLIS、Dora）依赖等值面场来编码几何（SDF、Flexicubes），有三大缺陷：
1. 无法处理开曲面、非流形、封闭内腔等复杂拓扑
2. 只关注形状，忽略材质/外观
3. SLAT（TRELLIS）虽联合编码几何与外观，但依赖多视角二维图像特征输入和渲染监督，对复杂结构和材质的捕捉能力有限

**本文的不同：** 从原生 3D 数据直接学习的结构化隐空间，不依赖 2D 渲染，不需要 SDF 等中间场。

### 2. 方法

核心创新是 **O-Voxel**——一种"全场无关"的稀疏体素表示，关键组件：

- **柔性双网格（Flexible Dual Grid）**：基于 Dual Contouring 的场无关方案，每个活动体素含一个对偶顶点 + 3 个边交叉标志 + 分裂权重，支持任意拓扑
- **体素材质属性**：每个体素存储 PBR 参数（Base Color, Metallic, Roughness, Alpha），支持半透明表面和重光照
- **即时双向转换**：Mesh ↔ O-Voxel 无需优化和渲染，CPU 秒级完成

基于 O-Voxel 设计 **Sparse Compression VAE (SC-VAE)**，实现 16× 空间下采样——1024³ 资产仅编码为 ~9.6K 隐式 token，是已知体素方法中最高的压缩率。

在此基础上训练 **4B 参数流匹配（Flow Matching）模型**，用于 Image-to-3D 生成。

### 3. 效果

| 维度 | 指标 |
|------|------|
| 重建几何 | Mesh Distance 和 CD 远超基线（如 Direct3D-S2 的 1/3） |
| 重建材质 | PSNR 40+ vs 基线 30 左右 |
| 生成质量 | 用户偏好率显著优于 Hunyuan3D、Direct3D、TRELLIS 等 |
| 推理效率 | 512³ 仅 ~3s，1024³ ~17s，1536³ ~60s（H100）|

### 4. 局限

1. **分辨率依赖**：细节小于体素时产生混叠/模糊（如两平行面落入同体素时，QEF 将对偶顶点置于中间而非任一面）
2. **偶发空洞**：解码器预测的高分辨率稀疏结构偶尔不保证封闭流形，需后续孔洞填充
3. **语义缺失**：O-Voxel 不支持部件级分割或拓扑图结构，缺少高层语义信息

---

## 技术拆解

### 一、O-Voxel — 原生 3D 表示

#### 1. 柔性双网格（Flexible Dual Grid）

**输入/目的：** 以稀疏体素编码任意拓扑的 mesh 表面几何，无需依赖 SDF 等标量场。

**原理（通俗解释）：** 在常规网格（primal grid）基础上构建一个对偶网格（dual grid）——每个体素中心放一个对偶顶点，每条体素边上放一个四边形面。通过调整对偶顶点的位置和四边形面的存在性来拟合任意曲面。

![O-Voxel 和即时双向转换示意](https://arxiv.org/html/2512.14692v1/x2.png)
*图：O-Voxel 结构及 Mesh ↔ O-Voxel 即时双向转换流程*

**关键公式——QEF 损失函数：**

```
min e(v) = Σ d²Π,i + λ_bound · Σ d²L,j + λ_reg · d²q_avg
```

- **d²Π,i = (n_i · (v − q_i))²**：平面距离项，v 到每个交叉点切平面的平方距离（来自原 Dual Contouring）
- **d²L,j = ‖(v − o_j) − ((v − o_j) · d_j)d_j‖²**：边界线距离项，v 到 mesh 边界边的距离（**新引入**，改善开曲面表示）
- **d²q_avg = ‖v − q̄‖²**：正则项，将 v 拉向交叉点平均值（稳定优化，防止奇异性）

**输出：** 每个活动体素存储三项几何特征：
- **对偶顶点 v_i ∈ R³[0,1]**：局部形状的顶点位置
- **边交叉标志 δ_i ∈ {0,1}³**：3 条预定义边（X/Y/Z 轴各一条）上是否有面交叉，决定四边形连接关系
- **分裂权重 γ_i ∈ R>0**：控制四边形自适应分裂为两个三角形的方式

**效果：** Mesh → O-Voxel 转换 CPU 秒级完成，O-Voxel → Mesh 毫秒级完成。支持开曲面、自交面、封闭内腔。保留尖锐边和法线不连续。

![方法整体概览](https://arxiv.org/html/2512.14692v1/x1.png)
*图：整体方法流程图 — O-Voxel → SC-VAE → 流匹配生成*

#### 2. 体素材质属性（Volumetric Material Attributes）

**输入/目的：** 为每个活动体素赋予 PBR 材质参数，与几何对齐。

**原理：** 每个活动体素的材质特征为 6 通道向量：
```
f_mat_i = (c_i, m_i, r_i, α_i)
```
- **c_i ∈ R³**：Base Color（基础色）
- **m_i ∈ R**：Metallic（金属度）
- **r_i ∈ R**：Roughness（粗糙度）
- **α_i ∈ R**：Opacity（不透明度）— 支持半透明！

**Texture → O-Voxel：** 投影体素中心到相交三角形，用 UV 坐标从纹理图采样，按点到面距离加权平均。

**O-Voxel → Texture：** 对查询点（顶点或纹素）做三线性插值，直接生成带 PBR 材质的 mesh，无需后处理。

**效果：** 支持重光照、半透明表面，这是此前方法不具备的能力。

---

### 二、Sparse Compression VAE (SC-VAE)

#### 1. 架构设计

**输入/目的：** 将 O-Voxel 的稀疏结构（几何 + 材质特征）压缩到紧凑隐空间，实现 16× 空间下采样。

**原理：** 全稀疏卷积 U-Net，关键创新点：

![SC-VAE 网络结构](https://arxiv.org/html/2512.14692v1/x3.png)
*图：SC-VAE 网络结构*

**稀疏残差自编码层（Sparse Residual Autoencoding Layer）：** 受 Deep Compression Autoencoder 启发，将下采样/上采样分解为：
- 下采样：稀疏卷积（stride 2）→ 修剪空体素
- 上采样：最近邻插值扩张稀疏结构 → 稀疏卷积

**提前剪枝上采样器（Early-pruning Upsampler）：** 常规上采样先扩张后剪枝会产生大量中间体素。本文在上采样前先剪枝，减少 3× 计算量。具体做法：解析邻域体素的活动状态，跳过全空的区域。

**优化残差块：** SubMConv → LayerNorm → Linear(×4) → Linear(×1) 的 ConvNeXt 风格，用 1×1×1 卷积替代 3×3×3 的深度可分离部分以适配 3D 稀疏卷积。

**编码器参数：** 354M，解码器 474M，总计 ~800M。

**效果：** 1024³ 资产编码为 ~9.6K token（对应 64³ 稀疏结构），是 SLAT（~20K token）的一半，Mesh Distance 和 CD 远低于所有基线。

#### 2. VAE 训练

**两阶段策略：**

**Stage 1（稳定训练）：** 256³ 分辨率，直接回归 O-Voxel 特征
```
L = ||f_pred - f_gt||²
```

**Stage 2（感知质量）：** 512³ 分辨率，引入渲染损失
```
L_shape_render = ||m̂ − m||₁ + 10·||d̂ − d||₁ + d_p(n̂, n)
L_mat_render = d_p(ĉ, c) + d_p(mrâ, mra)
```
其中 d_p 合并了 L1 + SSIM + LPIPS 感知距离，m 是 silhouette mask，d 是深度图，n 是法线图。

**效果：** 渲染损失显著提升了几何锐度和高频材质细节，且模型可泛化到 1536³ 甚至更高分辨率。

---

### 三、流匹配生成模型（Flow Matching）

#### 1. 模型概览

**输入/目的：** 在 SC-VAE 的隐空间中训练生成模型，实现 Image-to-3D。

**生成管线：** 两阶段级联：

1. **形状生成：** 在 32 维隐空间中生成稀疏结构（64³ → 64 通道）
2. **材质生成：** 以生成形状为条件，再生成 32 维材质隐码

**模型规格：3 个 Transformer，总计 4B 参数：**
- 每个 Transformer：30 层，1536 隐维度，12 头注意力，FFN 8192
- 输入图像通过 DINOv2 编码后以 cross-attention 注入
- 时间步通过 AdaLN-single 注入
- 形状信息作为材质生成的 channel-wise 拼接条件

**训练目标：Rectified Flow + Conditional Flow Matching**
```
L_CFM(θ) = E_{t,x₀,ε} ||v_θ(x(t), t) − (ε − x₀)||²₂
```
其中 x(t) = (1−t)x₀ + tε 是线性插值路径，t 从 logitNorm(1,1) 采样。

#### 2. 推理效率

| 分辨率 | 形状生成 | 材质生成 | 总时间 |
|--------|---------|---------|-------|
| 512³   | ~3s     | ~4s     | ~7s   |
| 1024³  | ~10s    | ~7s     | ~17s  |
| 1536³  | ~35s    | ~25s    | ~60s  |

#### 3. 级联推理（Cascaded Inference）

在推理时，先生成低分辨率隐结构，再上采样到高分辨率 O-Voxel 并用 SC-VAE 解码。或者：先生成高分辨率 O-Voxel，下采样回稀疏结构再重新上采样 → 修正局部错误 → 提升质量。这提供了计算效率与生成质量的可控权衡。

![分辨率与计算扩展](https://arxiv.org/html/2512.14692v1/x7.png)
*图：推理时通过分辨率与计算量扩展提升质量*

---

### 四、FlexGEMM — 高性能稀疏卷积后端

**问题：** 现有稀疏卷积库（Spconv, Torchsparse, fvdb, WarpConvNet）性能受限于 CUDA 生态。

**方案：** 用 Triton 实现的 Masked Implicit GEMM 策略，融合 im2col（特征收集）和 GEMM（矩阵乘法）为单一优化 kernel，最小化全局内存 I/O。同时支持 NVIDIA 和 AMD GPU。

**效果：** 前向计算比 Spconv 快 2-3×，反向传播快更多。

![FlexGEMM 性能对比](https://arxiv.org/html/2512.14692v1/x8.png)
*图：FlexGEMM 与各基线（Spconv, Torchsparse, fvdb, WarpConvNet）速度对比*

---

### 五、实验数据补充

#### 重建对比

在 ABO 和 3D-FUTURE 数据集上的形状重建结果：

| 方法 | Token 数 ↓ | Mesh Distance ↓ | CD ↓ | F-Score ↑ |
|------|-----------|----------------|------|-----------|
| SLAT | ~20K | 3.38 | 18.6 | 0.973 |
| SparseFlex | ~9.6K | 3.19 | 15.7 | 0.978 |
| Direct3D-S2 | ~2.2K | 11.77 | 56.8 | 0.914 |
| **Ours** | **~9.6K** | **1.60** | **7.5** | **0.994** |

材质重建 PSNR 达 40+，远超 SLAT 的 ~30。

#### 生成对比

Image-to-3D 生成用户偏好率显著优于 STEP1X-3D、TRELLIS、Direct3D-S2、Hunyuan3D 2.0 等基线。在几何质量（法线图）和 PBR 材质质量上均列第一。

#### 消融

- 稀疏残差自编码层：移除后质量下降 15-20%
- 提前剪枝上采样器：移除后计算增加 3 倍
- 渲染损失：移除后 PSNR 从 40+ 降至 ~35

---

### 六、总结与展望

O-Voxel + SC-VAE + Flow Matching 的组合为 3D 生成提供了一条完整的技术路线：从原生 3D 数据紧凑编码、高效压缩、到高质量生成。未来的改进方向包括引入部件级语义和拓扑图结构，以及解决体素粒度导致的亚体素混叠问题。

---
- [ ] 合入 wiki

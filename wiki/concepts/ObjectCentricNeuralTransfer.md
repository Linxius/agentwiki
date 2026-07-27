---
title: "Object-Centric Neural Transfer"
type: concept
tags: [rendering, global-illumination, neural-networks]
---

以物体为中心的神经迁移（Object-Centric Neural Transfer）是由 [[TransGI]] 提出的一种材质表示方法，将 [[PRT]] 的传输函数从场景级压缩到物体级。

**关键组件**：
- **顶点潜变量**：每个物体顶点附加 1D 向量，编码传输属性
- **神经传输解码器**：MLP 将潜变量 + G-Buffer 输入解码为球谐传输系数

**优势**：
1. 支持物体级别动态（移动、旋转、增删）
2. 紧凑表示（<1MB 网络 + 每顶点 7 维向量）
3. 支持复杂材质（Disney BSDF、测量材质）
4. 无 Monte Carlo 噪声（传输系数已预积分）

与 [[Neural-PRT]] 的区别：场景级 vs 物体级。
与 [[DDGI]] 的区别：支持光泽材质 vs 仅漫反射。
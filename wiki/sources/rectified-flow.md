---
title: "Rectified Flow"
type: source
tags: [paper, generative-model, flow, optimal-transport, ode]
date: 2026-07-28
source_file: raw/papers/www.cs.utexas.edu-lqiang-rectflow-html-intro.html.md
url: https://www.cs.utexas.edu/~lqiang/rectflow/html/intro.html
venue: UT Austin / Jupyter Book
published: 2024
links:
  - https://www.cs.utexas.edu/~lqiang/rectflow/html/intro.html
---

## Summary

Rectified Flow 是一种学习两个分布之间传输映射的简单方法。核心思想是通过学习一个常微分方程（ODE）来构建传输映射，关键特点是鼓励轨迹走直线（straight paths）。直线轨迹在数值求解时不会引入离散化误差，因此可以用极少的 Euler 步数（甚至单步）实现快速推理。这与最优传输理论有深刻联系。

## 原始出处

[Rectified Flow - Jupyter Book](https://www.cs.utexas.edu/~lqiang/rectflow/html/intro.html)，作者 L. Qiang，德克萨斯大学奥斯汀分校。

## Key Contributions

1. 提出 Rectified Flow 框架，通过 linear interpolation 配对数据点，学习从 pi_0 到 pi_1 的 ODE 传输映射
2. 通过 reflow 过程（直化）不断使轨迹更直，实现快速生成（单步 Euler）
3. 将 rectified flow 与扩散模型、最优传输建立理论联系
4. 支持生成建模（pi_0 为高斯分布）和迁移建模（pi_0,pi_1 均为经验分布）

## Method

### 整体思路

Rectified Flow 的核心思想是：给定两个分布 pi_0 和 pi_1，存在无穷多个 ODE/SDE 可以将 pi_0 传输到 pi_1。现有方法隐式选择了各自的轨迹路径，但没有明确标准。Rectified Flow 则显式偏好直线轨迹，因为直线轨迹在数值求解时没有离散化误差。

具体做法：
1. 对观测数据对 (X_0, X_1) 做线性插值：X_t = t*X_1 + (1-t)*X_0
2. 学习一个速度场 v 使得 ODE dZ_t = v(Z_t,t)dt 的轨迹匹配线性插值的边际分布
3. 通过 Reflow（重流）过程，用前一步的 ODE 输出重新配对，进行直化

### 数学框架

给定 X_0 ~ pi_0, X_1 ~ pi_1，线性插值 X_t = t*X_1 + (1-t)*X_0 满足 ODE：
dX_t = (X_1 - X_0)dt

Rectified Flow 学习 v 使得：
min_v E[||v(X_t, t) - (X_1 - X_0)||^2]

这就是一个简单的回归问题，不需要模拟 ODE。

### Reflow（直化）

Reflow 过程迭代地进行：
1. 从当前的 rectified flow ODE 采样轨迹
2. 用 ODE 的端点 (Z_0, Z_1) 重新配对
3. 在新的配对数据上重新训练 rectified flow

重复这一过程可以使轨迹越来越直，最终达到完美直线（单步可解）。

## Results & Comparisons

- Rectified Flow 可以使用单步 Euler 实现与扩散模型数十步相当的质量
- 直线轨迹从根本上消除了离散化误差
- Reflow 过程在保持生成质量的同时逐步减少所需步数

## Connections

- [[DiffusionModels]]：Rectified Flow 与扩散模型的 ODE 变体（如 DDIM）密切相关
- [[OptimalTransport]]：直线轨迹与最优传输中的 Monge 问题有深刻联系
- [[NeuralODE]]：Rectified Flow 本质上是在学习一个 Neural ODE

## Contradictions

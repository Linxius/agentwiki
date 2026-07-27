---
title: "Rectified Flow"
type: concept
tags: [flow, generative-model, optimal-transport, ode]
---

## 概述

Rectified Flow 是一种学习概率分布间传输映射的框架，通过学习 ODE 来构建传输映射。核心特点是鼓励直线轨迹，使得数值求解时无离散化误差，实现快速生成。

## 核心公式

学习一个速度场 v 最小化：
min_v E[||v(X_t,t) - (X_1-X_0)||^2]
其中 X_t = t*X_1 + (1-t)*X_0 是数据点的线性插值。

## Reflow

Reflow 过程通过重新配对 ODE 端点和重新训练，使轨迹逐渐直化。

## 相关页面

- [[RectifiedFlow]]
- [[DiffusionModels]]
- [[OptimalTransport]]

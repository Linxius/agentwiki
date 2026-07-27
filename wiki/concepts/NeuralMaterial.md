---
title: "Neural Material"
type: concept
tags: [brdf, neural-network, rendering, material]
---

## 概述

神经材质（Neural Material）使用神经网络来表示和压缩 BRDF 或材质参数。典型方法训练一个 Universal MLP 编解码器，将高维材质参数压缩到低维隐空间，实现高效存储和实时渲染。

## 关键方法

- Universal MLP：在所有材质上联合训练的编解码器
- 逐材质优化：对每个材质在隐空间中微调
- 隐空间正则化：确保生成模型可以产生有效编码

## 相关页面

- [[TowardRicherMaterialGenerationViaProceduralDataEnhancement]]

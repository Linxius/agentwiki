---
title: "1.5万字速通LLM主流模型结构（Llama、Qwen、GLM、Deepseek...）"
type: source
tags: [LLM, Transformer, Attention, MoE, 模型结构]
date: 2026-08-04
source_file: raw/inbox/(99+ 封私信 _ 80 条消息) 1.5万字速通LLM主流模型结构（Llama、Qwen、GLM、Deepseek...） - 知乎.html
url: https://zhuanlan.zhihu.com/p/2060741715095560795
links: []
---

## Summary

本文是【模型结构设计】系列的提纲文章，综合 Llama、DeepSeek、GLM、Qwen 等主流大模型的结构设计，从 Tokenizer 到 LM Head 逐组件讲解一个 token 在 LLM 中的完整计算流程，并系统介绍 MoE 结构。核心观点：2023 年至今 LLM 结构变化不大，GLM 5.2 与 Llama 的差异主要是 GQA→DSA+MLA 和密集→MoE，本质是"效率革命"。

## 原始出处

- 原始文件: [HTML](raw/inbox/(99+ 封私信 _ 80 条消息) 1.5万字速通LLM主流模型结构（Llama、Qwen、GLM、Deepseek...） - 知乎.html)
- 原文链接: [知乎专栏](https://zhuanlan.zhihu.com/p/2060741715095560795)

## Key Points

### 1. Tokenizer 与 Embedding

- **BPE 及其变体**是主流 LLM 的选择。Byte-level BPE (BBPE) 直接在 UTF-8 字节序列上操作，天然支持多语言，不会出现 OOV。
- **SentencePiece**（Google）：内置 BPE 和 Unigram，不依赖预分词，空格用 ▁ 表示，对中文/日文等无空格语言友好。
- **tiktoken**（OpenAI）：专为 BBPE 优化的 Rust 实现，推理速度极快。使用正则表达式分块，BPE 合并不跨越块边界。训练器效率较低，常配合 HuggingFace tokenizers 训练词表后转为 tiktoken 格式。
- **评估指标**：Fertility（英文 1.0-1.5，中文差的可达 4-6）、Parity（跨语言 token 数量差异度，影响 API 计费）。

### 2. 归一化与残差连接

- **RMSNorm** 取代 LayerNorm：移除均值计算，仅保留均方根作为缩放因子，成为主流 LLM 标配。公式：`RMS(x) = sqrt(mean(x^2))`，归一化 `x / RMS(x)`。
- **Pre-Norm vs Post-Norm**：Pre-Norm（`x = x + Sublayer(LayerNorm(x))`）通过恒等映射提供无损梯度通道，解决深层网络梯度消失，已成为标准配置；Post-Norm 每层输出稳定但深层训练需小心。

### 3. Attention 模块

#### 3.1 降低 KV Cache：MHA → GQA → MLA

- **KV Cache 机制**：推理分 Prefill（并行计算 GEMM）和 Decode（逐 token 生成 GEMV）两阶段。KV Cache 用空间换时间，避免 O(N²) 计算，但带来显存和带宽压力。
- **MQA**（Multi-Query Attention）：所有 Head 共享一组 KV，KV Cache 缩减 N 倍但表达能力受限。
- **GQA**（Group Query Attention）：Head 分 G 组，每组共享 KV。如 G=8 时 KV Head 从 32 降至 8，KV Cache 缩减 4 倍，质量无明显损失，是主流选择。
- **MLA**（Multi-head Latent Attention，DeepSeek-V2 提出）：将 KV 压缩到低维潜在空间再存储，推理时解压还原。同时对 Q 也进行低秩压缩（降低训练激活显存，不降低 KV Cache）。使用 **Decoupled RoPE**：引入携带位置信息的 Decoupled Query/Key，RoPE 仅作用于这部分，压缩恢复的 K/Q 保持纯内容信息。
- **RoPE**（Rotary Position Embedding）：乘法式位置编码，通过旋转 Q/K 向量使内积依赖相对位置，具备平移不变性。
- **QK-Norm**（ViT-22B 提出）：在注意力计算前对 Q、K 分别做 LayerNorm/RMSNorm，强制范数稳定，避免 logits 过大导致 softmax 退化为 one-hot。
- **Flash Attention**：IO 感知注意力算法，通过分块（Tiling）避免构建完整 N×N 注意力矩阵，仅在 SRAM 内计算，大幅减少 HBM↔SRAM 数据传输。

#### 3.2 Sparse Attention：DSA（DeepSeek-V3.2）

解决 MLA 未减少的计算量瓶颈（仍是 O(L²)），将复杂度降至 O(Lk)：
- **Lightning Indexer**：FP8 精度、ReLU 激活的轻量索引器，为每个历史 token 打分。
- **细粒度 token 选择**：保留得分最高的 top-K（2048）个 token 进行注意力计算。

### 4. Feed Forward 层（FFN）

- **SwiGLU** 取代 GELU：Swish（`x·sigmoid(x)`）计算比 GELU（需 erf 误差函数）更高效。
- **GLU 结构**：引入 gate、up、down 三个矩阵，`output = down_proj(silu(gate_proj(x)) * up_proj(x))`，中间维度 8/3d，总参数量与原来持平。门控引入非线性和条件计算能力。

### 5. LM Head

- 将 d 维向量映射为词表大小的 logits，经 softmax 转化为概率分布。
- 大模型不建议与 Embedding 共享参数，Embedding 参数占比小，共享会牺牲表达能力。
- **解码方式**：贪心解码、束搜索、Top-K 采样、Top-P 采样（均含温度缩放）。

### 6. Multi-Token Prediction (MTP)

- 预测未来多个 token，增加训练信号密度，促使模型学习前瞻性表示。
- MTP loss 与主 LM loss 联合计算，推理时可丢弃 MTP 模块。
- **投机解码**：MTP 模块可作为 draft model 生成候选 token，主模型并行验证，接受-拒绝机制保证分布一致，显著降低推理延迟。

### 7. Mixture of Experts (MoE)

#### 7.1 整体结构

- 将 FFN 替换为多个并行 FFN + Router，每 token 只激活部分专家，实现稀疏激活。
- **设计模式**：DeepSeek V3.2 前 3 层密集、后层 MoE；Llama 4 每层交替使用 MoE 和 Dense。前层学共性语义、后层分化专家。

#### 7.2 细粒度专家

- 将大 FFN 专家拆为 m 个小专家，总专家数 N→mN，总参数量不变。
- 组合爆炸：16 选 2 仅 120 种组合；64 选 8 达 44 亿种，token 可更精准组合知识。
- 代价：路由和 all-to-all 通信开销大，需 infra 优化。

#### 7.3 共享专家

- 隔离部分专家为共享专家，每 token 无条件经过。减少可路由专家激活数以保持计算量不变。
- 共享专家学共性知识，路由专家更聚焦独特知识。
- 输出 = 共享专家输出之和 + 路由专家加权输出之和 + 残差。

#### 7.4 负载均衡

**辅助损失体系**：
1. **专家级平衡损失**：防止路由坍塌，确保每专家收到 token 数相等。
2. **设备级均衡损失**：每个 GPU 计算量均衡，避免瓶颈。
3. **通信平衡损失**：每个设备收发数据量均衡，解决接收端带宽瓶颈。

- **Device-Limited Routing**（DeepSeek-V2）：限制 token 目标专家最多分布在 M 个设备上，控制发送侧通信开销。

**Auxiliary-Loss-Free 方案**：
- 为每专家设动态偏置 b_i，影响路由选择但不影响实际权重，保护模型性能上限。
- 训练步骤结束时根据负载统计以步长 γ 更新偏置。

**Token Drop**：
- 超容量时丢弃亲和度最低的 token，仅走残差连接。capacity_factor 通常 1.25。
- 问题：信息丢失、训推不一致。主流模型转向无 token drop 设计，靠辅助损失自然均衡。

#### 7.5 All-to-All 通信

MoE 需要两次 All-to-All：
1. **Scatter**：token 分发到目标设备。
2. **Gather**：汇聚专家计算结果。
- 通信复杂度 O(N²)，是 MoE 大规模扩展的主要瓶颈。

## Relevance

本文系统梳理了 LLM 模型结构的核心组件，与以下 wiki 页面直接相关：
- [[DeepSeek]] — MLA、DSA、MoE 的提出者
- [[GLM]] — DSA+MLA 的应用
- [[Transformer]] — 所有结构的基础

## Connections

- [[DeepSeek]] — DeepSeek-V2 提出 MLA，V3.2 提出 DSA 和 Device-Limited Routing
- [[GLM]] — 采用 DSA+MLA 和 MoE 结构
- [[LayerNorm]] — RMSNorm 的前身
- [[RoPE]] — 主流位置编码方案
- [[FlashAttention]] — IO 感知注意力加速算法
- [[GQA]] — Group Query Attention，KV Cache 压缩方案
- [[Mixture-of-Experts]] — MoE 架构的稀疏激活机制
- [[SwiGLU]] — SwiGLU 门控前馈结构

## Contradictions

- 无直接矛盾。本文定位为综述性介绍，与各论文的具体设计一致。

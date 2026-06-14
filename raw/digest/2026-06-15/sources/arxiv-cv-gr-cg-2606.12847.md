---
title: "Language-Guided Abstraction for Visual Reasoning"
arxiv_id: "2606.12847"
url: https://arxiv.org/abs/2606.12847
categories: [cs.CV]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: Language-Guided Abstraction for Visual Reasoning
**作者**: Xu-Jing Ye, Yuan-Gen Wang, Ruping Wang
**分类**: cs.CV
**arXiv**: https://arxiv.org/abs/2606.12847
**提交日期**: 2026-06-11

**摘要**:
The Abstraction and Reasoning Corpus (ARC) is viewed as a critical avenue to Artificial General Intelligence (AGI), as it enables models to learn abstract transformation rules from few-shot examples and then generalize to new tasks. However, prevalent ARC methodology is either pure language or vision-only (i.e., VARC). The former depends heavily on LLMs, consuming billions of parameters. The latter often struggles to capture high-level semantics, leading to overfitting on pixel-level patterns. To bridge this gap, we propose L-VARC, a novel framework that enhances visual reasoning via a language-guided Learning Using Privileged Information (LUPI) branch. Specifically, we design a Semantic Compression Module by feeding a unified, task-agnostic prompt into DeepSeek-V3. In this way, the raw LARC (a crowd-sourced language description dataset) can be substantially refined and structured, fitting with the context length constraint of standard text encoders (e.g., CLIP). Moreover, we design a Cross-Attention Projector to align visual features with semantic embeddings, aiming to guide the training of the ARC model. Notably, the LUPI branch is taken in the training process and will be discarded during inference, thereby yielding a lightweight model with a mere 18 million parameters. Extensive experiments demonstrate that our L-VARC effectively leverages linguistic priors to boost visual reasoning and outperforms state-of-the-art. Ablation studies further confirm the contribution of the two new designs towards the L-VARC framework. The code is available at https://github.com/GZHU-DVL/L-VARC.

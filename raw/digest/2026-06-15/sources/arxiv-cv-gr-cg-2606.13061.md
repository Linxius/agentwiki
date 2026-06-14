---
title: "LaME: Learning to Think in Latent Space for Multimodal Embedding via Information Bottleneck"
arxiv_id: "2606.13061"
url: https://arxiv.org/abs/2606.13061
categories: [cs.CV]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: LaME: Learning to Think in Latent Space for Multimodal Embedding via Information Bottleneck
**作者**: Peixi Wu, Biao Yang, Feipeng Ma, Bosong Chai, Bo Lin, Wei Yuan, Fan Yang, Tingting Gao, Hebei Li, Xiaoyan Sun
**分类**: cs.CV
**arXiv**: https://arxiv.org/abs/2606.13061
**提交日期**: 2026-06-11

**摘要**:
Reasoning-driven universal multimodal embedding has advanced rapidly by introducing Chain-of-Thought (CoT) reasoning into the embedding pipeline. Despite the strong performance across both general and complex tasks, this paradigm suffers from two core limitations: (i) autoregressive CoT reasoning incurs high computational cost, making it impractical for low-latency retrieval; and (ii) embedding performance is heavily coupled with CoT annotation quality, making large-scale training unreliable. These raise fundamental questions: Is textual CoT the optimal form of reasoning for embedding, and can effective embedding reasoning be accomplished in latent space? To this end, we propose LaME (Latent Reasoning Multimodal Embedding), which formulates embedding-oriented latent reasoning as a weakly supervised information bottleneck. LaME employs K learnable reason tokens as a fixed-capacity bottleneck, completing all reasoning within a single forward pass. The two weak supervision signals structurally decouple contrastive from autoregressive objectives and eliminate dependence on CoT annotations, while a two-stage training pipeline ensures stable convergence. Experiments on MMEB-v2 and MRMR show that LaME achieves competitive performance, surpassing some explicit CoT-based models, while delivering 60x faster inference than explicit CoT methods and 2x faster than latent baselines with throughput comparable to discriminative embedding models. Code will be released.

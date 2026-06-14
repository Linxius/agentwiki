---
title: "Multi-Label Test-Time Adaptation with Bayesian Conditional Priors"
arxiv_id: "2606.12925"
url: https://arxiv.org/abs/2606.12925
categories: [cs.CV,cs.LG]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: Multi-Label Test-Time Adaptation with Bayesian Conditional Priors
**作者**: Qiru Li, Ao Zhou, Zhiwei Jiang, Zifeng Cheng, Cong Wang, Yafeng Yin, Qing Gu
**分类**: cs.CV, cs.LG
**arXiv**: https://arxiv.org/abs/2606.12925
**提交日期**: 2026-06-11

**摘要**:
Multi-label recognition with frozen Vision-Language Models (VLMs) is brittle under distribution shift: standard zero-shot inference scores labels independently, ignoring co-occurrence structure and producing incoherent label sets where dominant concepts suppress weaker but compatible labels. We introduce Bayesian Conditional Priors (BCP) Estimation, a gradient-free test-time adaptation method that injects label dependency without tuning the backbone. BCP views zero-shot logits as a proxy for marginal posteriors under a fixed image-text likelihood and attributes shift-induced errors mainly to a mismatched label prior. For each test image, it selects a high-confidence anchor label and applies an anchor-conditioned Bayesian refinement. This update is closed-form in logit space and admits a pointwise mutual information (PMI) interpretation, explicitly promoting compatible labels and suppressing incompatible ones. BCP operates without target annotations by estimating anchor-conditioned priors online from the unlabeled test stream via lightweight second-order co-occurrence statistics, adding negligible overhead beyond a single forward pass. Across standard multi-label benchmarks and multiple CLIP backbones, BCP consistently outperforms strong TTA baselines, e.g., improving RN50 average mAP from 57.31 to 69.22 and ViT-B/16 from 62.61 to 71.79.

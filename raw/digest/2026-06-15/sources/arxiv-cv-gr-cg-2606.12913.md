---
title: "Selecting Samples on Graphs: A Unified Dataset Pruning Framework for Lossless Training Acceleration"
arxiv_id: "2606.12913"
url: https://arxiv.org/abs/2606.12913
categories: [cs.LG,cs.CV]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: Selecting Samples on Graphs: A Unified Dataset Pruning Framework for Lossless Training Acceleration
**作者**: Dongyue Wu, Zilin Guo, Xiaoyu Li, Jiajia Liu, Jingdong Chen, Nong Sang, Changxin Gao
**分类**: cs.LG, cs.CV
**arXiv**: https://arxiv.org/abs/2606.12913
**提交日期**: 2026-06-11

**摘要**:
The rapid growth of modern training datasets has significantly increased computational cost, motivating dataset pruning~(DP) methods which retain only a subset of informative samples to reduce training cost.  Existing pruning criteria typically rely on either intrinsic signals that assess samples independently or extrinsic signals that promote diversity via pairwise relations.  While effective in their own specific regimes, each captures only one aspect of sample utility and lacks robustness across different pruning ratios or data distribution.  In this work, we present a unified graph-based DP framework.  By modeling the dataset as a weighted graph, where node weights encode intrinsic value and edge weights encode extrinsic value, DP can be cast as a Maximum Weight Clique Problem (MWCP).  Although MWCP is NP-hard, its structure admits a principled greedy solution based on sample-wise marginal gains.  Under a few mild conditions, we further prove that this unified objective enjoys a formal approximation guarantee, which applies to a broad family of importance metrics and provides practical design guidelines.  Extensive experiments show that our method outperforms existing DP methods while substantially reducing training cost, reducing training time by over 40\% without sacrificing accuracy on ImageNet-1k with ResNet-50.

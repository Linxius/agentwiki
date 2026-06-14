---
title: "PP-OCRv6: From 1.5M to 34.5M Parameters, Surpassing Billion-Scale VLMs on OCR Tasks"
arxiv_id: "2606.13108"
url: https://arxiv.org/abs/2606.13108
categories: [cs.CV]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: PP-OCRv6: From 1.5M to 34.5M Parameters, Surpassing Billion-Scale VLMs on OCR Tasks
**作者**: Yubo Zhang, Xueqing Wang, Manhui Lin, Yue Zhang, Penglongyi Deng, Ting Sun, Tingquan Gao, Zelun Zhang, Jiaxuan Liu, Changda Zhou, Hongen Liu, Suyin Liang, Cheng Cui, Yi Liu, Dianhai Yu, Yanjun Ma
**分类**: cs.CV
**arXiv**: https://arxiv.org/abs/2606.13108
**提交日期**: 2026-06-11

**摘要**:
Vision-Language Models (VLMs) have achieved impressive results on general vision-language tasks, yet they suffer from hallucination, imprecise localization, and prohibitive computational cost when applied to dedicated OCR scenarios. This paper presents PP-OCRv6, a lightweight OCR system that combines architectural innovation with data-centric optimization. PP-OCRv6 redesigns the backbone, detection neck, and recognition neck around a unified MetaFormer-style building block with structural reparameterization, decoupling spatial token mixing from channel mixing and supporting both tasks through task-specific stride configurations. Three model tiers (medium, small, tiny) share the same block primitives, covering deployment scenarios from server to edge. On our in-house benchmarks, PP-OCRv6_medium achieves 83.2% recognition accuracy and 86.2% detection Hmean, outperforming PP-OCRv5_server by +5.1% and +4.6% respectively while surpassing Qwen3-VL-235B, GPT-5.5, and Gemini-3.1-Pro with orders of magnitude fewer parameters. The tiny tier achieves 3.9$\times$ faster inference than PP-OCRv5_mobile on Intel Xeon CPU while maintaining comparable accuracy.

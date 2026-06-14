---
title: "Magnifying What Matters: Attention-Guided Adaptive Rendering for Visual Text Comprehension"
arxiv_id: "2606.12898"
url: https://arxiv.org/abs/2606.12898
categories: [cs.CV,cs.CL]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: Magnifying What Matters: Attention-Guided Adaptive Rendering for Visual Text Comprehension
**作者**: Shenglai Zeng, Qirui Wang, Kai Guo, Xinnan Dai, Xianxuan Long, Hui Liu
**分类**: cs.CV, cs.CL
**arXiv**: https://arxiv.org/abs/2606.12898
**提交日期**: 2026-06-11

**摘要**:
Visual Text Comprehension (VTC) renders text into images for a vision-language model (VLM) to read, sidestepping LLM context-window limits and powering applications from long-page OCR to multi-page memory QA. Yet existing VTC pipelines treat rendering and layout as a fixed, content-agnostic preprocessing step and offer little mechanistic understanding of how VLMs internally process visualized text. Through a focused empirical study on VTC QA tasks, we reveal that VLMs exhibit a localization-without-utilization regime: evidence-localizing attention emerges sharply in the middle-to-late layers and is largely decoupled from answer correctness, yet simply enlarging the localized spans on the rendered page recovers a large fraction of the failures. Building on these observations, we propose AGAR (Attention-Guided Adaptive Rendering), a training-free, model-agnostic method that leverages a VLM's own middle-to-late layer attention to identify the top-K important visual patches, maps them back to word spans, and re-renders the page with those spans enlarged before re-inferring the answer. Extensive experiments across nine VTC benchmarks (short-form, long-context, and multi-page memory QA) and four VLM backbones show that AGAR (i)consistently improves off-the-shelf VLMs as a plug-and-play enhancement, (ii)composes with VLM post-training to yield further gains, and (iii)remains robust under both visual- and text-side input degradation.

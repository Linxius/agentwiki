---
title: "Unified MRI Brain Image Translation via Hierarchical Tumor Structure Comparison"
arxiv_id: "2606.13096"
url: https://arxiv.org/abs/2606.13096
categories: [cs.CV]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: Unified MRI Brain Image Translation via Hierarchical Tumor Structure Comparison
**作者**: Yupeng Cai, Jia Wei, Jianlong Zhou
**分类**: cs.CV
**arXiv**: https://arxiv.org/abs/2606.13096
**提交日期**: 2026-06-11

**摘要**:
Multi-modal MRI brain image translation via available modalities holds significant practical importance in modern medicine, providing robust support for early diagnosis, treatment planning, and outcome assessment of diseases. For this purpose, it is important to ensure the fidelity of the tumor regions after translation. However, existing brain image translation methods ignore the structure information of different tumor regions, which could assist translation models in enhancing the quality and clinical applicability of the translated images.  In this work, we propose a novel translation model called HTSCGAN, which is a unified multi-modal brain image translation generative adversarial model integrating the structural information within tumor regions with the aim of improving the quality of brain image translation. Specifically, the generator employs three Patch Contrast Module (PCM) with different patch sizes to capture the hierarchical structural information of the tumor regions. In addition, a pretrained Patch Classifier (PC) and a pretrained Structure-Aware Encoder (SAE) are employed to derive the generated image containing the same tumor region structure as the ground truth image via patch classification loss and tumor perceptual loss, respectively. The experiments on BraTS2020 and BraTS2021 demonstrate strong performance of our model in both translation tasks and down stream segmentation tasks, highlighting its effectiveness in enhancing the quality and clinical relevance of the translated brain images. Our code is available at https://anonymous.4open.science/r/HTSCGAN.

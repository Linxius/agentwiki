---
title: "Efficient, Robust, and Anti-Collusion Fingerprinting of Image Diffusion Models"
arxiv_id: "2606.12977"
url: https://arxiv.org/abs/2606.12977
categories: [cs.CV,cs.AI,cs.CR,cs.LG]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: Efficient, Robust, and Anti-Collusion Fingerprinting of Image Diffusion Models
**作者**: Jianwei Fei, Yunshu Dai, Zhihua Xia, Xiaochun Cao, Jiantao Zhou, Alessandro Piva, Benedetta Tondi
**分类**: cs.CV, cs.AI, cs.CR, cs.LG
**arXiv**: https://arxiv.org/abs/2606.12977
**提交日期**: 2026-06-11

**摘要**:
Model fingerprinting, embedding user-specific identifiers (fingerprints) into generated outputs, has recently emerged as a popular solution to protect the intellectual property rights (IPR) of generative text-to-image (T2I) models and prevent unauthorized redistribution. In this work, we reveal a previously unexplored systematic vulnerability in existing generative model fingerprinting methods: they lack robustness against collusion attacks, where multiple attackers combine their models to remove or obscure the fingerprints. To address this issue, we take the first step towards a robust fingerprinting method for T2I models with anti-collusion capabilities. The proposed method encodes strings of bits, namely fingerprints, into the coefficients of a personalized normalization module (PNM) incorporated into T2I models, so that fingerprints can be reliably recovered from any generated image. To defend against collusion attacks and prevent unauthorized model redistribution, we introduce an anti-collusion mechanism based on lossless function-invariant parameter transformations. This mechanism significantly degrades the image generation quality of colluded models, making them effectively unusable. Moreover, our method allows developers to efficiently create multiple copies of fingerprinted T2I models by reparameterizing the PNM without the need for retraining. We also introduce a worst-case optimization strategy to improve robustness against model-level attacks. Our experiments demonstrate that the proposed method achieves high fidelity and robustness across multiple T2I image generation and editing tasks, with fingerprint extraction accuracy exceeding 99.5%. Compared with existing methods, our method demonstrates, for the first time, a notable proactive robustness to collusion attacks by significantly increasing the FID of colluded models.

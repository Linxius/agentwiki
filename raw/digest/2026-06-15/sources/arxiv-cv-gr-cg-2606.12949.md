---
title: "ViPER: Vision-based Packing-Aware Encoder for Robust Malware Detection"
arxiv_id: "2606.12949"
url: https://arxiv.org/abs/2606.12949
categories: [cs.CR,cs.CV]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: ViPER: Vision-based Packing-Aware Encoder for Robust Malware Detection
**作者**: Fatima Qaiser, Bisma Tahir, Muhammad Abid Mughal, Nauman Shamim
**分类**: cs.CR, cs.CV
**arXiv**: https://arxiv.org/abs/2606.12949
**提交日期**: 2026-06-11

**摘要**:
Visualization-based malware detection maps raw binary bytes to grayscale images and applies learned visual classifiers, providing an evasion-resistant and disassembly-free alternative to conventional analysis pipelines. However, executable packing remains a critical failure mode: packed binaries produce high-entropy images that obscure the structural patterns these models rely on. Because packing is also prevalent in benign software (e.g., for compression or copy protection), packing state alone is not a reliable indicator of maliciousness, and existing approaches do not address this challenge within a unified supervised framework. We present ViPER, a Vision-based Packing-Aware Encoder for Robust malware detection. ViPER builds on a LoRA-adapted ViT-B/14 backbone with a dual-head architecture that jointly learns malware classification and packing detection. A packing-aware gating mechanism conditions malware predictions on the inferred packing state, enabling distinct decision boundaries for packed and unpacked inputs. To address packing label skew during training, we employ frequency-weighted losses with stratified sampling over joint class-packing strata. Evaluated on 200,000 Windows PE byteplot images, ViPER achieves a balanced accuracy of 0.8521, ROC-AUC of 0.9260, and AUPR of 0.9279, outperforming representative state-of-the-art baselines across all primary metrics, while attaining a packing detection AUC of 0.9949.

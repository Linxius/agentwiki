---
title: "Acquisition state behaves as a structured, measurable variable governing lung-nodule AI: kernel-driven measurement instability and noise-driven detection fragility, invisible to DICOM metadata"
arxiv_id: "2606.12824"
url: https://arxiv.org/abs/2606.12824
categories: [cs.AI,cs.CV]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: Acquisition state behaves as a structured, measurable variable governing lung-nodule AI: kernel-driven measurement instability and noise-driven detection fragility, invisible to DICOM metadata
**作者**: Daniel Soliman
**分类**: cs.AI, cs.CV
**arXiv**: https://arxiv.org/abs/2606.12824
**提交日期**: 2026-06-11

**摘要**:
AI governance for medical imaging is formalizing: the 2026 ACR-SIIM Practice Parameter recommends local acceptance testing and ongoing drift monitoring, and the ACR Assess-AI registry monitors AI outputs using DICOM metadata for context. We argue that a necessary, currently unmonitored layer sits beneath output metrics: whether incoming studies remain within the acquisition envelope a model was validated on. Using a LUNA16-trained MONAI RetinaNet lung-nodule detector, we test whether acquisition state behaves as a structured, measurable variable. On real paired CT differing only in reconstruction kernel (NLST B30f vs B80f), kernel alone shifted AI-measured diameter and flipped a Fleischner size category in 5.2% (8 of 155) of nodules at fixed patient and acquisition, while detection confidence was unchanged (Wilcoxon p=0.22). Under controlled LIDC-IDRI perturbations the effects dissociated by axis: the noise axis degraded detection confidence (p=5.9e-32, concentrated in nodules under 6 mm) but not measurement, while the frequency/kernel axis corrupted measurement (p=8.6e-13) but not detection. A 4-feature pixel fingerprint recovered reconstruction identity (patient-level AUC about 0.95 on real CT, 0.995 on a QIBA phantom) where the ConvolutionKernel DICOM tag was uninformative (identical labels across reconstructions). The kernel axis transported across four manufacturers (leave-one-vendor-out AUC 0.94-0.98, matching the within-vendor ceiling). Acquisition state thus maps to distinct AI failure modes, frequency content to measurement reliability and noise to detection sensitivity, and is not recoverable from metadata. Acquisition-aware, input-side validation is the missing layer for the acceptance-testing and drift-monitoring requirements now entering imaging-AI accreditation.

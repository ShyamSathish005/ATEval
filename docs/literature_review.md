# Literature review and paper registry

**Registry status:** initial research map, not a completed systematic review.  
**Review date:** 2026-11-01.  
**Scope:** academic and technical text detection, benchmark validity, robustness, fairness, watermarking, and abstention/calibration.

## Review method and evidence limits

The initial corpus below is the 20-paper set specified in the project brief. For this first pass I checked official publisher/proceedings pages or primary institutional pages for the core methods and benchmark records cited in the detailed entries below, and used the URLs and bibliographic particulars supplied in the project brief for the remaining entries. This is not yet a full-text systematic review: several papers still require complete-paper reading, extraction of exact experimental settings, confirmation of repositories/data versions, and independent licence inspection. Claims in the brief are not silently upgraded into verified implementation facts. The implementation status for all methods remains not implemented.

Official-source records checked directly in this pass include the DetectGPT and Binoculars PMLR pages, Fast-DetectGPT ICLR record, RAID and M4 ACL Anthology records, M4GT-Bench ACL record, NIST AI 700-1 institutional page, KGW PMLR record, SynthID-Text Nature record and public reference repository, Liang et al. Patterns record, and additional ICLR work on Glimpse and detector optimization. Source pages establish bibliographic metadata and high-level claims; code/data licensing needs repository-level review before reuse.

## Synthesis

The literature supports treating detector scores as fallible measurements whose meaning depends on generator, domain, passage length, model/tokenizer, perturbation or watermark configuration, and operating threshold. The required methods represent materially different evidence: likelihood-derived heuristics; perturbation or conditional-curvature tests; two-model contrast; supervised classifiers; and keyed watermark tests. A single common output API is useful, but those scores must remain semantically distinct and be evaluated on matched, leakage-controlled data.

Benchmark work explicitly motivates testing unseen generators, domains, attacks and languages. Low false-positive operation points and uncertainty intervals matter more than headline accuracy when human-authored documents are in scope. A watermark detector can support a claim about a known compatible watermark configuration; it cannot establish generic AI authorship. The writing-quality and LaTeX-correction subsystem must remain independent of detector outputs.

## Initial required corpus

For each entry, “licence” means the licence of software/data assets, not the paper's publication licence. No external repository or data has been imported. Licences are therefore marked **not yet verified** unless stated otherwise.

### P01 — DetectGPT

- **Authors/year/venue:** Eric Mitchell, Yoonho Lee, Alexander Khazatsky, Christopher D. Manning, Chelsea Finn; 2023; ICML, PMLR 202.
- **Title:** *DetectGPT: Zero-Shot Machine-Generated Text Detection using Probability Curvature*.
- **Permanent source/PDF:** [PMLR paper](https://proceedings.mlr.press/v202/mitchell23a.html); [PDF](https://proceedings.mlr.press/v202/mitchell23a/mitchell23a.pdf). DOI not listed on the PMLR page; arXiv DOI 10.48550/arXiv.2301.11305.
- **Official code:** [eric-mitchell/detect-gpt](https://github.com/eric-mitchell/detect-gpt). Code licence: not yet verified.
- **Method/data/models:** target-model log probabilities compared with generic-model perturbations; requires a scoring LM/tokenizer and a perturbation model (paper discusses T5-style infilling). Original paper evaluates on generated passages including GPT-NeoX fake-news samples.
- **Finding/limitation:** paper reports a curvature signal and an AUROC improvement over the baseline in its evaluated setting. Computational cost and dependence on scoring/perturbation models are central constraints; results do not establish universal performance or academic-domain validity.
- **ATEval:** planned, not implemented; exact equation, sign, normalization and reference outputs must be checked before coding.

### P02 — Fast-DetectGPT

- **Authors/year/venue:** Guangsheng Bao, Yanbin Zhao, Zhiyang Teng, Linyi Yang, Yue Zhang; 2024; ICLR.
- **Title:** *Fast-DetectGPT: Efficient Zero-Shot Detection of Machine-Generated Text via Conditional Probability Curvature*.
- **Permanent source/PDF:** [ICLR paper page](https://proceedings.iclr.cc/paper_files/paper/2024/hash/6b8c6f846c3575e1d1ad496abea28826-Abstract-Conference.html); DOI not listed on the conference record.
- **Official code:** [baoguangsheng/fast-detect-gpt](https://github.com/baoguangsheng/fast-detect-gpt). Licence: not yet verified.
- **Method/data/models:** conditional probability curvature, replacing DetectGPT's perturbation stage with a conditional sampling calculation; exact sampling and expectation/variance terms must be taken from the paper/code. Paper evaluates white-box and surrogate/black-box settings.
- **Finding/limitation:** authors report faster inference and strong AUROC in their settings. Those results are configuration- and benchmark-specific; hardware/runtime claims need local replication.
- **ATEval:** planned, not implemented; both compatible-source and surrogate setups required.

### P03 — Binoculars

- **Authors/year/venue:** Abhimanyu Hans, Avi Schwarzschild, Valeriia Cherepanova, Hamid Kazemi, Aniruddha Saha, Micah Goldblum, Jonas Geiping, Tom Goldstein; 2024; ICML, PMLR 235.
- **Title:** *Spotting LLMs With Binoculars: Zero-Shot Detection of Machine-Generated Text*.
- **Permanent source/PDF:** [PMLR paper](https://proceedings.mlr.press/v235/hans24a.html); PDF linked from that record.
- **Official code:** [ahans30/Binoculars](https://github.com/ahans30/Binoculars). Licence: not yet verified.
- **Method/data/models:** contrast between related performer and observer models using the paper's cross-perplexity/perplexity score; both model/tokenizer compatibility and the exact equation/threshold matter.
- **Finding/limitation:** authors report strong detection and low-FPR results across their evaluated sources. This does not transfer automatically to academic writing, other model pairs, or present-day generators.
- **ATEval:** planned, not implemented; published threshold reproduction must be distinct from locally calibrated thresholds.

### P04 — Transparent likelihood and statistical baselines

- **Authors/year/venue:** methodological baselines, not one paper. The project brief specifies mean token NLL, perplexity, mean rank/log-rank, predictive entropy, sequence likelihood and length-normalized likelihood.
- **Sources:** exact definitions and provenance will be linked to the method papers during implementation; this entry is not a paper citation.
- **Data/models:** causal LM logits and a pinned tokenizer/model revision; no fixed dataset.
- **Limitations:** tokenization, context window, domain vocabulary, truncation and length affect scores; low perplexity is not authorship proof and can create unfair error patterns.
- **ATEval:** planned, not implemented.

### P05 — Comparative evaluation framework

- **Authors/year/venue:** project-level evaluation objective, not a single publication.
- **Source:** use shared RAID/NIST conditions and each method's original paper; see P06/P09.
- **Method:** matched manifests, train/validation/test separation, AUROC/AUPRC, TPR at fixed low FPR, calibration, confidence intervals, subgroup/domain/generator metrics and measured runtime/resources.
- **Limitation:** comparisons are invalid when datasets, thresholds, preprocessing or hardware conditions differ without disclosure.
- **ATEval:** planned, not implemented.

### P06 — RAID

- **Authors/year/venue:** Liam Dugan, Alyssa Hwang, Filip Trhlík, Andrew Zhu, Josh Magnus Ludan, Hainiu Xu, Daphne Ippolito, Chris Callison-Burch; 2024; ACL 2024.
- **Title:** *RAID: A Shared Benchmark for Robust Evaluation of Machine-Generated Text Detectors*.
- **Permanent source:** [ACL Anthology](https://aclanthology.org/2024.acl-long.674/), DOI 10.18653/v1/2024.acl-long.674.
- **Project/data:** [liamdugan/raid](https://github.com/liamdugan/raid). Data and code licences: not yet verified.
- **Method/data:** benchmark described as more than six million generations across 11 models, 8 domains, 11 attacks and 4 decoding strategies; streaming/subset access and version identity are required.
- **Finding/limitation:** paper reports vulnerability of detectors to attacks, decoding variation and unseen models. Dataset composition limits the conclusions to its included sources and conditions.
- **ATEval:** adapter planned, not implemented.

### P07 — M4

- **Authors/year/venue:** Yuxia Wang et al.; 2024; EACL, ACL Anthology 2024.eacl-long.83.
- **Title:** *M4: Multi-generator, Multi-domain, and Multi-lingual Black-Box Machine-Generated Text Detection*.
- **Permanent source:** [ACL Anthology](https://aclanthology.org/2024.eacl-long.83/), DOI 10.18653/v1/2024.eacl-long.83.
- **Project/data:** [mbzuai-nlp/M4](https://github.com/mbzuai-nlp/M4). Licence/version still to verify.
- **Method/data:** benchmark spans languages, generators and domains; metadata must be retained to measure cross-group generalization.
- **Finding/limitation:** paper reports generalization difficulty on unseen domains or LLMs. Results are tied to its sampled languages, domains, models and collection period.
- **ATEval:** adapter planned, not implemented.

### P08 — M4GT-Bench

- **Authors/year/venue:** Yuxia Wang et al.; 2024; ACL 2024.
- **Title:** *M4GT-Bench: Evaluation Benchmark for Black-Box Machine-Generated Text Detection*.
- **Permanent source:** [ACL Anthology](https://aclanthology.org/2024.acl-long.218/); DOI and full bibliographic record to be confirmed from the Anthology metadata before registry freeze.
- **Project/data:** [mbzuai-nlp/M4GT-Bench](https://github.com/mbzuai-nlp/M4GT-Bench). Licence/version still to verify.
- **Method/data:** supports binary, multi-generator, mixed human-machine and segment-level tasks as specified in the project brief. Span and boundary metrics must remain separate from document-level metrics.
- **Limitations:** task labels and segment annotation quality bound the conclusions; exact data schema requires repository audit.
- **ATEval:** adapter planned, not implemented.

### P09 — NIST GenAI Pilot

- **Authors/year/publisher:** Hariharan Iyer, Seungmin Seo, Lukas Diduch, Kay Peterson, George Awad, Yooyoung Lee; 2025; NIST AI 700-1, published 25 June 2025.
- **Title:** *2024 NIST GenAI (Pilot Study): Text-to-Text Evaluation Overview and Results*.
- **Permanent source:** [NIST publication record](https://www.nist.gov/publications/2024-nist-genai-pilot-study-text-text-evaluation-overview-and-results), DOI 10.6028/NIST.AI.700-1.
- **Method/data:** text-to-text generation and discrimination pilot; NIST reports AUC and Brier scores on article groups and human/machine summaries.
- **Limitations:** a NIST-compatible local evaluation is not certification or endorsement. Data/submission conditions must be matched to reproduce a result.
- **ATEval:** compatible metrics planned; not implemented.

### P10 — KGW watermark

- **Authors/year/venue:** John Kirchenbauer, Jonas Geiping, Yuxin Wen, Jonathan Katz, Ian Miers, Tom Goldstein; 2023; ICML, PMLR 202.
- **Title:** *A Watermark for Large Language Models*.
- **Permanent source/PDF:** [PMLR paper](https://proceedings.mlr.press/v202/kirchenbauer23a.html).
- **Official code:** [jwkirchenbauer/lm-watermarking](https://github.com/jwkirchenbauer/lm-watermarking). Licence not yet verified.
- **Method/data:** keyed context-dependent green-token selection and a statistical test (including a z-statistic under the configured null); needs known scheme parameters and token/context implementation.
- **Finding/limitation:** paper proposes a watermark for compatible generation with interpretable statistical testing. It does not detect arbitrary generated text; edits and insufficient token counts affect evidence.
- **ATEval:** planned, not implemented; separate watermark evidence track.

### P11 — SynthID-Text

- **Authors/year/venue:** S. Dathathri et al.; 2024; *Nature* 634, 818–823.
- **Title:** *Scalable watermarking for identifying large language model outputs*.
- **Permanent source:** [Nature article](https://www.nature.com/articles/s41586-024-08025-4), DOI 10.1038/s41586-024-08025-4.
- **Official reference code/docs:** [Google DeepMind repository](https://github.com/google-deepmind/synthid-text). Repository describes a reference implementation; code/data/model terms require separate inspection.
- **Method/data:** tournament-sampling text watermark and compatible detection, with published frequentist/Bayesian procedures and documented configurations.
- **Finding/limitation:** paper reports large-scale deployment evaluations and quality/detectability findings. Only supported configurations and known compatible texts should be considered; detector output is watermark evidence, not generic authorship attribution.
- **ATEval:** planned, not implemented.

### P12 — Non-native English false-positive risk

- **Authors/year/venue:** Weixin Liang et al.; 2023; *Patterns*.
- **Title:** *GPT detectors are biased against non-native English writers*.
- **Permanent source:** [DOI/publisher record](https://doi.org/10.1016/j.patter.2023.100779).
- **Code/data:** public supplementary/code availability and licence require follow-up review; no data imported.
- **Finding/limitation:** paper reports substantial false-positive disparities in its evaluated detectors and TOEFL/student-essay setting. The exact sample is limited and should be treated as an important warning, not a universal quantified rate for current methods.
- **ATEval:** fairness protocol planned, not implemented; never infer writer background from prose.

### P13 — Detector reliability evaluation

- **Authors/year/venue:** Debora Weber-Wulff et al.; 2023; *International Journal for Educational Integrity*.
- **Title:** *Testing of detection tools for AI-generated text*.
- **Permanent source:** [DOI](https://doi.org/10.1007/s40979-023-00146-z).
- **Method/data:** evaluation of publicly available and commercial detection systems as described in the paper; exact versions and protocol need full-text extraction.
- **Finding/limitation:** the study concluded tested tools were not sufficiently reliable for academic misconduct decisions in its tested conditions. This should not be generalized beyond those tools/data without replication.
- **ATEval:** review and error-analysis protocol; not an algorithm.

### P14 — Stumbling Blocks

- **Authors/year/venue:** Yichen Wang et al.; 2024; ACL 2024.
- **Title:** *Stumbling Blocks: Stress Testing the Robustness of Machine-Generated Text Detectors Under Attacks*.
- **Permanent source:** [ACL Anthology](https://aclanthology.org/2024.acl-long.160/).
- **Method/data:** controlled robustness evaluation; exact attacks, data, and conclusions require full-paper extraction.
- **Licence:** code/data license not yet verified.
- **ATEval:** stress-test design planned, not implemented; use only as authorized scientific evaluation, not as rewrite guidance.

### P15 — Detection limits under transformations

- **Authors/year/venue:** Vinu Sankar Sadasivan et al.; 2025; *Transactions on Machine Learning Research*.
- **Title:** *Can AI-Generated Text be Reliably Detected?*.
- **Permanent source:** [OpenReview paper](https://openreview.net/forum?id=00gsAZdF0t).
- **Method/data:** analyzes transformation-based limits and distributional distinguishability; full text and version should be read before translating claims into protocol.
- **Limitations:** theoretical/empirical scope depends on assumptions and studied transformations.
- **ATEval:** stress-test rationale planned, not an implemented method.

### P16 — Practical detector examination

- **Authors/year/venue:** Brian Tufts, Xuandong Zhao, Lei Li; 2025; Findings of NAACL 2025.
- **Title:** *A Practical Examination of AI-Generated Text Detectors for Large Language Models*.
- **Permanent source:** [ACL Anthology](https://aclanthology.org/2025.findings-naacl.271/).
- **Method/data:** practical detector evaluation; the brief highlights TPR at fixed FPR. Full experimental details and data licence require review.
- **ATEval:** metric protocol planned; not implemented.

### P17 — TempTest

- **Authors/year/venue:** Tom Kempton, Stuart Burrell, Connor J. Cheverall; 2025; AISTATS, PMLR 258.
- **Title:** *TempTest: Local Normalization Distortion and the Detection of Machine-generated Text*.
- **Permanent source:** [PMLR paper](https://proceedings.mlr.press/v258/kempton25a.html).
- **Method/data:** local-normalization-distortion method. Exact model requirements, equations and reference code must be extracted from the primary source.
- **Limitations:** an experimental detector with paper-specific assumptions; do not approximate it with a different score.
- **ATEval:** optional planned method, not implemented.

### P18 — Cross-domain detection

- **Authors/year/venue:** You Zhou, Jie Wang; 2024; ACM Symposium on Document Engineering.
- **Title:** *Detecting AI-Generated Texts in Cross-Domains*.
- **Permanent source:** [ACM DOI](https://doi.org/10.1145/3685650.3685673).
- **Method/data:** RoBERTa-Ranker and small-data domain adaptation per project brief; exact data and training settings need full-text review.
- **Limitations:** domain adaptation on limited target data is not evidence of universal transfer.
- **ATEval:** classifier baseline planned, not implemented.

### P19 — Survey

- **Authors/year/venue:** Junchao Wu et al.; 2025; *Computational Linguistics* 51(1).
- **Title:** *A Survey on LLM-Generated Text Detection: Necessity, Methods, and Future Directions*.
- **Permanent source:** [ACL Anthology](https://aclanthology.org/2025.cl-1.8/), DOI 10.1162/coli_a_00549.
- **Contribution/limitation:** taxonomy and research survey; primary-source cross-check remains necessary for implementation details.
- **ATEval:** review queued; not an algorithm.

### P20 — Comprehensive review

- **Authors/year/venue:** Tanzila Kehkashan et al.; 2025; *Computer Science Review* 58.
- **Title:** *AI-generated text detection: A comprehensive review of methods, datasets, and applications*.
- **Permanent source:** [DOI](https://doi.org/10.1016/j.cosrev.2025.100793).
- **Contribution/limitation:** review taxonomy to compare with P19; individual primary studies must be consulted before implementation.
- **ATEval:** review queued; not an algorithm.

## Additional research identified for follow-up

1. **Glimpse: Enabling White-Box Methods to Use Proprietary Models for Zero-Shot LLM-Generated Text Detection** (ICLR 2025). [Official ICLR page](https://proceedings.iclr.cc/paper_files/paper/2025/hash/806e8e4ea77000a1486eeddeb1b90a6e-Abstract-Conference.html). Relevant to black-box/surrogate extensions of entropy, rank and Fast-DetectGPT; exact methods, access assumptions and code licence require full-paper/repository review.
2. **Language Model Detectors Are Easily Optimized Against** (ICLR 2024). [Official ICLR page](https://proceedings.iclr.cc/paper_files/paper/2024/hash/1f9f07df0992ce21698d800eaa891bd8-Abstract-Conference.html). Relevant to robustness and the limits of static detector validation; use to motivate controlled stress tests, not to build evasion tooling.

Further search is required across ACL Anthology, OpenReview, PMLR, IEEE Xplore, ACM Digital Library, SpringerLink, arXiv, and institutional proceedings. In particular, the review should search for post-2025 work through the final release cutoff, academic-specific corpora, mixed-authorship provenance, calibrated abstention, and newer watermark methods. This document deliberately does not claim that review is complete.

## Research references and implementation policy

The cited papers are research references, not bundled dependencies. Before code reuse, separately record repository URL, commit/release, source licence, model-weight licence, dataset licence, and any access restrictions in the SBOM/notices. Exact reproduction claims require matching or explicitly documenting deviations in model revision, tokenizer, data, preprocessing, threshold, hardware and code.

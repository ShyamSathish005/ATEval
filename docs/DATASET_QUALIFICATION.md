# AI-Text Detection Dataset Qualification Report (ATEval M5.1)

## Executive Summary

Milestone M5.1 establishes an empirical foundation for AI-text evaluation in academic writing. Prior to this milestone, ATEval operated an uncalibrated, deterministic stylometric signal baseline without qualified, licensed, document-grouped benchmark corpora.

This report documents the exhaustive qualification of eight candidate AI-text detection corpora against strict academic integrity, licensing, provenance, and task-definition criteria.

### Qualification Verdicts

| Candidate | DOI / Identifier | Primary Licence | Primary Domain | Mixed Authorship | Span Labels | Qualification Status |
|---|---|---|---|:---:|:---:|---|
| **TXD-22** | `10.17632/prcjcggtjf.1` | **CC BY 4.0** | Academic & Professional Q&A (30 domains) | **Yes** (4 classes) | No | **Approved for experimental benchmarking** |
| **RAID** | `2024.acl-long.674` | **MIT** | Multi-domain (arXiv abstracts, news, web) | No | No | **Approved for experimental benchmarking** |
| **M4** | `2024.eacl-long.83` | **CC BY 4.0** | Multi-domain (arXiv, Wiki, Reddit) | No | No | **Approved for experimental benchmarking** |
| **CHEAT** | `arXiv:2304.12008` | CC BY-NC-SA 4.0 | Academic Abstracts (arXiv) | **Yes** (3 classes) | No | **Useful only for secondary robustness testing** |
| **HC3** | `arXiv:2301.07597` | CC BY-SA 4.0 | General & Expert Q&A | No | No | **Useful only for secondary robustness testing** |
| **TuringBench** | `10.18653/v1/2021.emnlp-main.451` | CC BY-NC 4.0 | News articles (legacy models) | No | No | **Useful only for secondary robustness testing** |
| **MDAIGT** | `arXiv:2511.11340` | **Unstated / Unresolved** | News & Academic Articles | No | No | **Pending further evidence** |
| **HATCorpus** | `ky1916/HATCorpus` | *N/A (empty repo)* | *N/A* | No | No | **Rejected** |

---

## Detailed Candidate Audits

### 1. TXD-22: A Large-Scale Benchmark Dataset for Multi-Class AI-Generated and Mixed-Source Text Identification

* **Repository:** Mendeley Data  
* **DOI:** `10.17632/prcjcggtjf.1`  
* **Publication:** Iqbal, M. S., & Kashem, M. A. (2026). *SiBot: A hybrid framework for fine-grained semantic attribution of AI-generated text and its production deployment*. **PLOS ONE**, 21(9), e0357405. DOI: `10.1371/journal.pone.0357405`.  
* **Download Availability:** Fully available via Mendeley Data direct HTTP public API (`TXD-22 A Large-Scale Benchmark Dataset.csv`, 121,656,267 bytes, SHA-256 `232c260f8caf7ea61a331f39fa730956862afbe0c5fc554720daa07d215a2f7d`).  
* **Licence:** **Creative Commons Attribution 4.0 International (CC BY 4.0)**, explicitly registered in schema.org JSON-LD and Mendeley REST API.  
* **Scale & Class Distribution:** 66,000 samples balanced across 22 classes (exactly 3,000 samples per class):  
  * **1 Pure Human Class:** Written in English by ~350 participants from diverse academic and professional backgrounds without AI assistance.  
  * **17 AI Systems:** ChatGPT, Gemini, Claude, LLaMA, Mistral AI, Grok, Copilot, Perplexity, DeepSeek, DeepAI, Qwen, Gemma, Poe, Nova, Pi, Z.ai, BLACKBOXAI.  
  * **4 Mixed-Authorship Classes:**  
    1. `AI-generated + Human-written`  
    2. `AI-generated + AI-refined`  
    3. `Human-written + AI-refined`  
    4. `AI-generated + AI-refined + Human-written`  
* **Human Participant Consent & Ethics:** Informed consent obtained from all ~350 human contributors; voluntary participation; all responses anonymized with zero PII retained.  
* **Academic Domain Coverage:** Elicited across 30 academic and professional disciplines using a hierarchical question set.  
* **Text Length:** Normalized response lengths up to ~300 words.  
* **Passage-Level Labels:** **None.** Labels are document-level (full response text).  
* **Leakage Risks:** The `Question` column contains the prompt. If rows are split at random without grouping by `Question`, AI and human answers to the exact same prompt cross train and test boundaries. Group-based splitting by prompt is mandatory.  
* **Redistribution Restrictions:** CC BY 4.0 permits research and benchmarking with proper attribution. Raw corpus (121 MB) is kept out of Git and managed via download manifests.  
* **Qualification Verdict:** **Approved for experimental benchmarking** (Task A: Human vs AI; Task B: Mixed Authorship).

---

### 2. MDAIGT: Multi-Domain AI-Generated Text Detection

* **Repository:** Hugging Face (`CogniSAL/MDAIGT`)  
* **Publication:** Lamsiyah, S., et al. (2025). *M-DAIGT: A Shared Task on Multi-Domain Detection of AI-Generated Text*. **RANLP 2025**, ACL Anthology: `2025.ranlp-mdaigt.1`, arXiv: `2511.11340`.  
* **Download Availability:** Partial. Training CSV files (`train_mdaigt_task1.csv` 19.5 MB, `train_mdaigt_task2.csv` 15.9 MB) exist via Git LFS on Hugging Face. The evaluation/test split is withheld for the shared task.  
* **Licence:** **Unstated / Unresolved.** The Hugging Face dataset card omits a license badge. Under international copyright, absence of an explicit open-source licence restricts automated ingestion and derivative distribution.  
* **Scale & Domains:** 20,000 samples (Task 1: 10,000 News articles; Task 2: 10,000 Academic abstracts). Balanced binary (`human` vs `machine`).  
* **AI Models:** GPT-4, Claude.  
* **Mixed Authorship:** None (pure binary).  
* **Passage-Level Labels:** None.  
* **Qualification Verdict:** **Pending further evidence.** Ingestion is prohibited until authors clarify dataset licensing.

---

### 3. RAID: Robust AI Detection Benchmark

* **Repository:** GitHub (`liamdugan/raid`) / Hugging Face (`liamdugan/raid`)  
* **Publication:** Dugan, L., et al. (2024). *RAID: A Shared Benchmark for Robust Evaluation of Machine-Generated Text Detectors*. **ACL 2024 (Long Papers)**, `2024.acl-long.674`.  
* **Download Availability:** Complete via Hugging Face (`raid-train`, `raid-test`, `raid-extra`).  
* **Licence:** **MIT License** (permissive open-source).  
* **Scale & Domains:** Over 10 million generation records across 11 domains, prominently featuring **ArXiv Abstracts** alongside news, recipes, and Wikipedia.  
* **AI Models:** 8 foundation models (ChatGPT, GPT-4, LLaMA-2-70b, Mistral-7B, Cohere Command, etc.) with 11 decoding strategies and adversarial attacks.  
* **Mixed Authorship:** None (discrete whole-document generations).  
* **Passage-Level Labels:** None (binary document-level; 512-token windows).  
* **Qualification Verdict:** **Approved for experimental benchmarking** (academic domain holdout and adversarial robustness).

---

### 4. M4: Multi-Generator, Multi-Domain, Multi-Lingual Detection

* **Repository:** GitHub (`mbzuai-nlp/M4`)  
* **Publication:** Wang, Y., et al. (2024). *M4: Multi-generator, Multi-domain, and Multi-lingual Black-Box Machine-Generated Text Detection*. **EACL 2024 (Resource Paper Award)**, `2024.eacl-long.83`.  
* **Download Availability:** Complete via GitHub / Hugging Face.  
* **Licence:** **Creative Commons Attribution 4.0 International (CC BY 4.0)**.  
* **Scale & Domains:** Multi-lingual corpus featuring a dedicated **arXiv academic paper** subset alongside Wikipedia, WikiHow, and Reddit.  
* **AI Models:** ChatGPT, GPT-4, LLaMA, Dolly, BLOOMZ.  
* **Mixed Authorship:** Base M4 is binary/source attribution; boundary detection added in SemEval-2024 Task 8.  
* **Passage-Level Labels:** Document-level in base M4.  
* **Qualification Verdict:** **Approved for experimental benchmarking** (academic generalisation).

---

### 5. HATCorpus: Human–AI Text Corpus

* **Repository:** Hugging Face (`ky1916/HATCorpus`)  
* **Stated Metadata:** Claimed 32,248 samples of Wikipedia/Gutenberg human text vs AI text under `cc-by-sa-4.0`.  
* **Underlying File Inspection:** **Defective / Empty.** The Git repository tree contains solely `.gitattributes` and `README.md`. No Parquet, CSV, or JSONL data files were committed or pushed by the author.  
* **Qualification Verdict:** **Rejected.** Candidate repository contains zero data.

---

### 6. CHEAT: ChatGPT-Written Abstracts Dataset

* **Repository:** GitHub (`zaopeng-yu/CHEAT`)  
* **Publication:** Yu, Z., et al. (2023). *CHEAT: A Large-scale Dataset for Detecting ChatGPT-writtEn AbsTracts*. **arXiv:2304.12008**.  
* **Licence:** Non-commercial research terms (CC BY-NC-SA 4.0).  
* **Academic Coverage:** 35,304 academic abstracts from arXiv.  
* **Mixed Authorship:** Contains pure generation, human-AI mixed abstracts, and AI-polished abstracts.  
* **Qualification Verdict:** **Useful only for secondary robustness testing** due to non-commercial licensing constraints.

---

### 7. HC3: Human ChatGPT Comparison Corpus

* **Repository:** Hugging Face (`Hello-SimpleAI/HC3`)  
* **Publication:** Guo, B., et al. (2023). *How Close is ChatGPT to Human Experts? Comparison Corpus, Evaluation, and Detection*. **arXiv:2301.07597**.  
* **Licence:** CC BY-SA 4.0.  
* **Domain Focus:** Question answering in medicine, finance, law, psychology, and computer science.  
* **Qualification Verdict:** **Useful only for secondary robustness testing** (conversational QA rather than academic prose).

---

### 8. TuringBench: Turing Test in Neural Text Generation

* **Repository:** GitHub / Hugging Face  
* **Publication:** Uchendu, A., et al. (2021). *TURINGBENCH: A Benchmark Environment for Turing Test in the Age of Neural Text Generation*. **EMNLP 2021**, `10.18653/v1/2021.emnlp-main.451`.  
* **Licence:** CC BY-NC 4.0.  
* **Model Provenance:** 19 legacy generator architectures (GPT-2, GROVER, CTRL, RoBERTa, XLNet). Lacks modern instruction-tuned LLMs.  
* **Qualification Verdict:** **Useful only for secondary robustness testing** (outdated generator architectures).

---

## Qualification Summary and Next Steps

1. **Primary Evaluation Corpus:** **TXD-22** meets all qualification criteria: CC BY 4.0 licence, peer-reviewed PLOS ONE provenance, verified human ethics, 66,000 balanced samples across 22 classes, and academic domain coverage.
2. **Secondary Academic Robustness Corpora:** **RAID** (arXiv subset) and **M4** (arXiv subset) are approved for cross-corpus generalization benchmarks.
3. **Task Isolation:** No candidate corpus provides passage-level ground truth spans. Consequently, **Task D (Passage Localisation) must reject document-level datasets** and only evaluate explicitly verified span fixtures.


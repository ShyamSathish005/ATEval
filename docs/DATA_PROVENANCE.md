# ATEval Data Provenance and Licensing Ledger

## Purpose and Policy

ATEval adheres to strict academic licensing, data provenance, and reproducibility standards:
1. **Zero External Data in Git:** Large external corpora, raw manuscripts, and model weights are strictly barred from version control via `.gitignore` and enforced by `scripts/check_release_archive.py`.
2. **Deterministic Provenance:** Every external asset is registered with its canonical DOI, primary licence terms, SHA-256 cryptographic hash, exact download URL, and download timestamp.
3. **Auditability:** Preprocessing transformations must be deterministically reproducible from raw source files to evaluation splits.

---

## External Dataset Registry

### 1. TXD-22: A Large-Scale Benchmark Dataset

* **Dataset Identifier:** `TXD-22`  
* **Source Repository:** Mendeley Data  
* **DOI:** `10.17632/prcjcggtjf.1`  
* **Canonical Citation:**  
  > Iqbal, Md Sadiq; Kashem, Mohammod Abul (2026), "TXD-22: A Large-Scale Benchmark Dataset for Multi-Class AI-Generated and Mixed-Source Text Identification", Mendeley Data, V1, doi: 10.17632/prcjcggtjf.1  
* **Associated Paper:**  
  > Iqbal, M. S., & Kashem, M. A. (2026). SiBot: A hybrid framework for fine-grained semantic attribution of AI-generated text and its production deployment. *PLOS ONE*, 21(9), e0357405. https://doi.org/10.1371/journal.pone.0357405  
* **Licence:** Creative Commons Attribution 4.0 International (**CC BY 4.0**)  
* **Download URL:** `https://data.mendeley.com/public-files/datasets/prcjcggtjf/files/1e842f9d-4ff8-4986-bc7c-cde460f806ee/file_downloaded`  
* **Expected File Name:** `TXD-22 A Large-Scale Benchmark Dataset.csv`  
* **Expected File Size:** 121,656,267 bytes (121.6 MB)  
* **Cryptographic Hash (SHA-256):**  
  `232c260f8caf7ea61a331f39fa730956862afbe0c5fc554720daa07d215a2f7d`  
* **Total Records:** 66,000 samples (22 classes, 3,000 per class)  
* **Human Participant Consent:** ~350 participants; voluntary; informed consent obtained; fully anonymized with zero PII retained.  
* **Local Storage Path:** `data/raw/txd_22/txd22_raw.csv` (git-ignored)  
* **Manifests:** `data/manifests/txd22_dataset_manifest.json`, `data/manifests/txd22_train_manifest.json`, `data/manifests/txd22_val_manifest.json`, `data/manifests/txd22_test_manifest.json`.

---

### 2. RAID Benchmark (Secondary Academic Cohort)

* **Dataset Identifier:** `RAID`  
* **Source Repository:** GitHub (`liamdugan/raid`) / Hugging Face (`liamdugan/raid`)  
* **Canonical Citation:**  
  > Dugan, L., Hwang, A., Trhlík, F., Zhu, A., Ludan, J. M., Xu, H., Ippolito, D., & Callison-Burch, C. (2024). RAID: A Shared Benchmark for Robust Evaluation of Machine-Generated Text Detectors. In *Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)*, pages 12463–12492. ACL.  
* **Licence:** MIT License  
* **Academic Subset:** `abstracts` domain (arXiv abstracts)  
* **Local Adapter:** `ateval.detection.adapters.RAIDAdapter`

---

### 3. M4 Benchmark (Secondary Academic Cohort)

* **Dataset Identifier:** `M4`  
* **Source Repository:** GitHub (`mbzuai-nlp/M4`) / Hugging Face (`mbzuai-nlp/M4`)  
* **Canonical Citation:**  
  > Wang, Y., Mansurov, J., Ivanov, P., Su, J., Shelmanov, A., Tsvigun, A., Whitehouse, C., Afzal, O. M., Mahmoud, T., Sasaki, T., Arnold, T., Aji, A. F., Habash, N., Gurevych, I., & Nakov, P. (2024). M4: Multi-generator, Multi-domain, and Multi-lingual Black-Box Machine-Generated Text Detection. In *Proceedings of the 18th Conference of the European Chapter of the Association for Computational Linguistics (Volume 1: Long Papers)*, pages 1369–1407. EACL.  
* **Licence:** Creative Commons Attribution 4.0 International (**CC BY 4.0**)  
* **Academic Subset:** `arxiv` domain  
* **Local Adapter:** `ateval.detection.adapters.M4Adapter`

---

## Preprocessing and Transformation Ledger

Every transformation applied to raw external corpora is deterministic and auditable:

1. **Text Normalization:**
   - UTF-8 decoding with surrogate-character sanitization.
   - Preserves intra-word hyphens and apostrophes.
   - Retains original sentence boundaries and LaTeX math notations where present.
2. **Label Preservation:**
   - Raw source labels (e.g., `ChatGPT`, `AI-generated + Human-written`, `Human`) are preserved verbatim in `original_label`.
   - Standardized mapping into `human`, `ai`, and `mixed` strictly respects source taxonomy.
3. **Partition Tracking:**
   - Record IDs are assigned deterministically as `{source_dataset}_{row_index:06d}`.
   - Document and prompt hash keys ensure zero leakage across split manifests.


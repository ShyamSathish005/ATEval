# Dataset licenses and distribution status

The project workspace currently contains IteraTeR-HUMAN raw exports, derived
splits, annotation packets, reviewer results, model heads, and benchmark
predictions. They are excluded from source archives and Docker builds. They
remain in the existing workspace; this release preparation does not delete
them.

| Asset | Upstream statement / provenance | Release handling |
|---|---|---|
| TXD-22 (`10.17632/prcjcggtjf.1`) | Mendeley Data V1; CC BY 4.0; Iqbal & Kashem (PLOS ONE 2026, `10.1371/journal.pone.0357405`). Contains 66,000 QA samples across 22 balanced classes (1 human, 17 AI, 4 mixed). Human contributors (~350 participants) provided informed consent; anonymized. | Downloaded via `scripts/download_txd22.py`; raw CSV excluded from Git by `.gitignore`. Used for Task A (binary) and Task B (mixed authorship) benchmarking. |
| RAID (`2024.acl-long.674`) | Dugan et al. (ACL 2024); MIT License; contains millions of generations across 11 domains (including arXiv abstracts). | Approved for academic domain and adversarial robustness benchmarks. Excluded from repository git tracking. |
| M4 (`2024.eacl-long.83`) | Wang et al. (EACL 2024); CC BY 4.0; multi-generator and multi-domain corpus including an arXiv domain subset. | Approved for academic domain generalisation benchmarks. Excluded from repository git tracking. |
| MDAIGT (`CogniSAL/MDAIGT`) | Lamsiyah et al. (RANLP 2025 / arXiv:2511.11340). | Pending further evidence; Hugging Face dataset card omits explicit open-source license badge. Ingestion withheld. |
| HATCorpus (`ky1916/HATCorpus`) | Repository on Hugging Face is empty (0 data files). | Rejected; unviable. |
| IteraTeR-HUMAN sentence and document dataset cards ([sentence](https://huggingface.co/datasets/wanyu/IteraTeR_human_sent), [document](https://huggingface.co/datasets/wanyu/IteraTeR_human_doc)) | Hugging Face cards currently declare Apache-2.0. The dataset consists of revisions of text collected from third-party sources. | Raw/processed copies and trained artifacts are excluded pending a provenance and derivative-work review of the included text and local manifests. Reproducers must fetch from the upstream source and check its current card and source terms. |
| IteraTeR-FULL / IteraTeR Plus / v2 | Separate corpora and provenance; not verified for this release. | Not included. No license inference from IteraTeR-HUMAN. |
| Re3-Sci, CASIMIR, EditEval, XtraGPT/ReviseQA and other research resources | See `docs/extended_revision_research.md`; each resource and its source material may have separate conditions. | Not included or downloaded by the install path. Review the exact source and derived-data licenses before acquisition or use. |
| `data/annotations/` and `experiments/milestone4_4/` reviewer work | Contains blind keys, human annotations, and excerpts linked to research records. | Excluded from source archives and Docker contexts until consent, de-identification, and redistribution permission are documented. |

Upstream cards are discovery metadata and do not establish the rights of every
underlying source passage, nor do they automatically authorize redistribution
of fitted model artifacts. Do not use these local corpora for commercial
training or distribute them based only on this summary. See
`docs/release_exclusion_manifest.yaml` for file-level exclusion rules.

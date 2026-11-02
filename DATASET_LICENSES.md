# Dataset licenses and distribution status

The project workspace currently contains IteraTeR-HUMAN raw exports, derived
splits, annotation packets, reviewer results, model heads, and benchmark
predictions. They are excluded from source archives and Docker builds. They
remain in the existing workspace; this release preparation does not delete
them.

| Asset | Upstream statement / provenance | Release handling |
|---|---|---|
| IteraTeR-HUMAN sentence and document dataset cards ([sentence](https://huggingface.co/datasets/wanyu/IteraTeR_human_sent), [document](https://huggingface.co/datasets/wanyu/IteraTeR_human_doc)) | Hugging Face cards currently declare Apache-2.0. The dataset consists of revisions of text collected from third-party sources. | Raw/processed copies and trained artifacts are excluded pending a provenance and derivative-work review of the included text and local manifests. Reproducers must fetch from the upstream source and check its current card and source terms. |
| IteraTeR-FULL / IteraTeR Plus / v2 | Separate corpora and provenance; not verified for this release. | Not included. No license inference from IteraTeR-HUMAN. |
| Re3-Sci, CASIMIR, EditEval, XtraGPT/ReviseQA and other research resources | See `docs/extended_revision_research.md`; each resource and its source material may have separate conditions. | Not included or downloaded by the install path. Review the exact source and derived-data licenses before acquisition or use. |
| `data/annotations/` and `experiments/milestone4_4/` reviewer work | Contains blind keys, human annotations, and excerpts linked to research records. | Excluded from source archives and Docker contexts until consent, de-identification, and redistribution permission are documented. |

Upstream cards are discovery metadata and do not establish the rights of every
underlying source passage, nor do they automatically authorize redistribution
of fitted model artifacts. Do not use these local corpora for commercial
training or distribute them based only on this summary. See
`docs/release_exclusion_manifest.yaml` for file-level exclusion rules.

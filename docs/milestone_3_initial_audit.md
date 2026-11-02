# Milestone 3: Milestone 2 implementation audit

**Audit date:** 2026-11-01
**Scope:** the repository state before this milestone's dataset and model additions.

## Findings

| Area | Existing implementation | Gap addressed in Milestone 3 |
|---|---|---|
| Dataset loaders | Offline IteraTeR and arXivEdits adapters, raw label retention, a reviewed taxonomy crosswalk, and an arXivEdits per-paper/version license gate. | Official IteraTeR `.json` exports are JSONL; the loader assumed JSON arrays. Added JSONL fallback and paired document-context join. arXivEdits is still not ingested because per-version text rights are heterogeneous and no complete record-level license manifest was available. |
| Corpus inspection | `revisions inspect` reports rows, skipped records and label counts. | No acquired licensed corpus, source hashes, duplicate report, or real corpus quality profile existed. Added immutable manifests and reports for IteraTeR-HUMAN. |
| Intention model | A small Multinomial Naive Bayes model was trainable from local data and reportable on a declared split. | It was not trained on the actual corpus; no majority/LR/SVM comparison, validation tuning, context ablation, calibration report, or domain slicing existed. Added document-held-out classical baselines. |
| Training/evaluation | Existing evaluator had a document leakage check for a fitted NB model. | The grouped benchmark now fails on any train/dev/test document overlap, tunes C only on validation, excludes unchanged pairs from the intent task, and reports test scores once. A frozen DistilBERT comparison was added during this milestone; no expert review is claimed. |
| Context | Loader could extract limited context from document records, but the classifier did not consume it. | Added sentence, local-neighbor and full-document feature variants and paired document export matching. The model API uses local neighboring context. |
| Generation | Conservative phrase proposals existed and required author acceptance. | No generation baseline had been evaluated against human revisions. Added identity and existing-rule comparison; rule candidates are auto-applied only inside that held-out benchmark, never by the interactive UI. |
| Preservation | Exact protected-span checks reported structural preservation and explicitly abstained on semantic equivalence. | Kept that honest boundary. Generation benchmark adds numeric and citation sequence checks. No claim-level NLI/QA method is implemented; uncertain edits still require review. |
| CLI | Offline inspection and NB train/evaluate commands existed. | Added `benchmark-intent` and `benchmark-generation` commands over licensed local exports with no-overwrite output guards. |
| API | Local API handled writing analysis, ingestion and privacy-conscious review audits. | Added `/writing/revision-intent` for a trained, checksum-verified local model. The endpoint marks its output advisory and reports that the model cannot decide whether any change is necessary. |
| UI | Poppins-based quality view presented conservative suggestions with rationale, context, technical risk and accept/reject controls. | Added an intent-preview action for the first sentence and prominent limitations. Manuscript context is sent only to the local API and is not stored by prediction. |
| Audit records | Saved audits omitted full source text and kept hashes, snippets and decisions. | Preserved this behavior; intent predictions are not persisted. |

## Data and label assumptions

The IteraTeR-HUMAN sentence task is single-label in the published export. Its public tags (`clarity`, `fluency`, `meaning-changed`, `coherence`, `style`, `others`) are cross-walked to the product taxonomy without inventing finer distinctions. The first canonical annotation is used where a source supplies multiple tags. Unchanged source/target pairs have no explicit “change necessary” label, so they are excluded from intention classification; the interface consequently reports necessity as “not determined.”

The official upstream sentence train/dev/test metadata contains documents in more than one split. The benchmark therefore uses deterministic source-document grouping across all six sentence files and keeps the upstream split as provenance. This is a corrective evaluation split, not a replacement for the authors' published split.

## Remaining limitations

- The corpus contains 3,254 published human sentence pairs in total, from news, Wikipedia and arXiv abstracts; it is not representative of all academic fields or manuscript sections.
- There are no author identifiers in these exports, so author-held-out evaluation and author-style modeling are unavailable.
- The annotation set is imbalanced, especially `other` and style-related labels.
- Text overlap scores cannot establish writing quality or meaning preservation.
- No qualified academic reviewer study was conducted in this milestone.
- A frozen DistilBERT contextual-embedding classifier was run after a pinned model license and CPU setup were verified. No encoder fine-tuning or fine-tuned sequence-to-sequence generator was completed. See the final report for measured results and limits.

The implementation and evidence are described in [`milestone_3_report.md`](milestone_3_report.md), [`dataset_ingestion_report.md`](dataset_ingestion_report.md), and [`dataset_quality_report.md`](dataset_quality_report.md).

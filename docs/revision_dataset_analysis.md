# Revision dataset analysis

**Milestone:** 2 · **Prepared:** 2026-11-01 · **Status:** adapters implemented; corpus-scale data not acquired

## Scope and use

This note reviews the two closest revision-intent resources for building a research baseline. They supervise analysis of observed human revisions; they are not automatic rewrite targets, labels of text quality, or evidence that later text is always better. Corpus labels are mapped into ATEval's taxonomy while the raw labels are retained. Unknown labels remain unmapped.

## arXivEdits

The paper reports 751 papers sampled from 1,000 arXiv groups (1,790 versions), 1,039 adjacent-version revision pairs, and manual sentence alignment plus span/intention annotation on 1,000 sentence pairs. Its alignment pipeline uses paragraph alignment and bidirectional neural CRF sentence alignment, followed by intersection/merging; its intent classifier is CRF-based. The paper reports 93.8 sentence-alignment F1 and 78.9 fine-grained intent F1 on its reported evaluation. Its taxonomy includes language improvement (accuracy/specificity, style, simplification, other), grammar/typo correction, content update, and formatting. It covers papers in physics and mathematics, so discipline and revision-type coverage are limited. [Zhao et al., EMNLP 2022](https://aclanthology.org/2022.emnlp-main.641/); [official repository and data/code layout](https://github.com/chaojiang06/arXivEdits).

### Data fields and ingestion

The public edit export includes sentence 1/2, edit-combination annotations, arXiv ID, and source/target version levels. Edit annotations include operation type, token spans, and intent. The adapter accepts local JSON/JSONL/CSV exports and maps token indices to exact character slices only for the exported whitespace-token form; when indices are absent or malformed it falls back to a diff, whose spans do not represent gold intent annotations. Sentence alignment is a separate transparent CPU dynamic-programming baseline supporting 1:1, 1:2, 2:1, insert, and delete. It is not a reproduction of the paper's neural CRF.

### Rights and provenance

The official repository has no one blanket license for the paper text. Its README records differing arXiv license terms by paper/version, including permissive and noncommercial/share-alike cases. A Hugging Face re-export's dataset card does not establish permission for underlying manuscript text. Thus the adapter requires a user-provided manifest for both source and target versions plus an explicit allowlist of exact license identifiers. A missing manifest entry or unpermitted term skips that pair. This is a software gate, not legal advice or a determination that a particular use is permitted. Do not redistribute source text or train on it without independently reviewing each applicable record's terms and research permissions. [Official arXivEdits data and license notes](https://github.com/chaojiang06/arXivEdits); [Hugging Face export fields](https://huggingface.co/datasets/miwytt/arXivEdits_edits).

## IteraTeR

IteraTeR contains 31,631 document revisions and 196,987 edit actions across Wikipedia, arXiv abstracts, and Wikinews. The manually annotated HUMAN resource comprises 559 revisions and 4,018 actions annotated by three annotators, with raw human annotations and a canonical aggregation. The paper reports the HUMAN sentence-level splits as 3,254 train, 400 development, and 364 test actions. The FULL split propagates model predictions and must remain separate from human labels. Published intent categories are fluency, clarity, coherence, style, meaning-changed, and other. The paper's classifier F1 varies strongly by class (reported clarity 0.69, fluency 0.80, coherence 0.32, style 0.13, meaning-changed 0.53), so raw labels should not be collapsed into an assumed reliable quality signal. Deeper revision stages are not a ranking of quality. [Du et al., ACL 2022](https://aclanthology.org/2022.acl-long.326/); [official repository and dataset instructions](https://github.com/vipulraheja/iterater); [HUMAN sentence export/card](https://huggingface.co/datasets/wanyu/IteraTeR_human_sent).

### Data fields and ingestion

The local adapter supports sentence-level fields such as `before_sent`, `after_sent`, `labels`, `doc_id`, `revision_depth`, and annotation `raw_intents`; it also reads document-level `before_revision` and `edit_actions` rows. `HUMAN` labels are the default. `FULL` is allowed only as a separately named variant and emits an explicit model-propagation warning. The official repository's Apache-2.0 code license is not automatically a license for all source text: examples originate in multiple upstream domains. The adapter is offline and does not fetch the corpus. Review the exact export provenance and source-specific terms before marking records verified. IteraTeR Plus and v2 are not included; the official instructions require separate access.

## Adapters and audit fields

`RevisionRecord` preserves dataset, source document ID, revision stage, split, source and revised text, edit spans, raw/canonical labels, context, annotation confidence, license identifier, and a verification flag. JSONL, JSON, and CSV are accepted. Training fails by default if any record has unverified licensing. Evaluation checks source-document IDs against the model's training IDs and fails on overlap. Keep paper/author groups in one split; sentence-level random splits create serious leakage.

The built-in test fixtures are synthetic and validate parsing/gating behavior only. No published corpus has been downloaded, no real records have been licensed for training, and no corpus benchmark score is claimed. A user may run `ateval revisions inspect iterater path/to/export.json --split train` to inspect a local export; arXivEdits additionally requires a per-version `--manifest` and repeated `--permitted-license` flags. Training requires `--license-verified` for IteraTeR records after the user reviews the source terms.

## Selection conclusion

Use IteraTeR-HUMAN first for a small intent-classification baseline if provenance for the local source export is approved. Use arXivEdits only for per-version eligible examples, keeping the dataset's source/target pair and document group intact. Report results by corpus, domain, split, intent, and annotator confidence. Do not pool HUMAN and FULL labels or infer that a revision is beneficial from its stage, label, or direction.

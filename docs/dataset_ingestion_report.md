# IteraTeR-HUMAN dataset ingestion report

**Ingestion date:** 2026-11-01
**Dataset used:** IteraTeR-HUMAN sentence and document exports.
**Status:** source exports retained byte-for-byte; processed copies and manifests are versioned separately.

## Sources and terms

- [IteraTeR paper (ACL Anthology)](https://aclanthology.org/2022.acl-long.250/) describes iterative human revisions and intention annotations.
- [Official IteraTeR repository](https://github.com/vipulraheja/iterater) and its [dataset README](https://github.com/vipulraheja/iterater/blob/main/dataset/README.md) document the HUMAN, FULL, Plus and v2 resources. The README reserves Plus/v2 for users who separately acquire Newsela and contact the authors; neither is used here.
- [Sentence dataset card](https://huggingface.co/datasets/wanyu/IteraTeR_human_sent) and [document dataset card](https://huggingface.co/datasets/wanyu/IteraTeR_human_doc) identify the public HUMAN exports as Apache-2.0. That declaration is recorded as the source license in each split manifest. This is provenance documentation, not legal advice; users should review the original terms for their intended redistribution.

Only HUMAN was downloaded. The automatic `FULL` labels are not mixed with human labels. arXivEdits (the [paper](https://arxiv.org/abs/2210.15067) and [repository](https://github.com/chaojiang06/arXivEdits)) was investigated but not ingested: its associated arXiv texts carry mixed per-version terms, and the export available to this pipeline did not provide a complete verified license manifest for every source/target version. The existing adapter requires both exact version terms and an explicit allowlist before it accepts any arXivEdits pair.

## Files and content

The six source files are newline-delimited JSON despite their `.json` suffixes. Sentence records provide `doc_id`, `revision_depth`, `before_sent`, `after_sent`, `labels`, and where available raw human votes. Document records provide the before/after revisions, edit actions, character positions, and a domain tag. Author IDs and authorship permissions are not present in the downloaded exports. The arXiv subset maps to abstracts; the dataset does not provide reliable section labels for full papers.

| Raw source | Rows | Bytes | SHA-256 |
|---|---:|---:|---|
| `data/raw/iterater_human_sent/train.json` | 3,254 | 2,449,295 | `0b1d1dbe74e2a68495cd0770746899c354cf6787450fc6b14b7ee1f95914eb4c` |
| `data/raw/iterater_human_sent/dev.json` | 400 | 292,355 | `7e60c860608a853e55e3b702d104039ab15235e732e5bbe78bade0b81a739189` |
| `data/raw/iterater_human_sent/test.json` | 364 | 294,380 | `1a30452c33bd5379ff56159016d68ecd7e2669ede1e4ea77244c6e300952e9cb` |
| `data/raw/iterater_human_doc/train.json` | 481 | 2,088,096 | `3f60e9989879b7a51b994edbe4536a5bd30556670f47b6677815bf0ed45c0acc` |
| `data/raw/iterater_human_doc/dev.json` | 27 | 200,286 | `9b8e216ca1874260bcf63365877225b2ee1547b70f1945fc172be1fcd945fc70` |
| `data/raw/iterater_human_doc/test.json` | 51 | 192,095 | `b3f371261389662eebd8395f8b78020eef84a85218c03b2df6823d2c7f551b4b` |

The files were downloaded from the dataset's public file export at pinned revisions (`7a570cd` for sentence files and `ec416e7` for document files). Source files have not been rewritten. Prepared sentence and document records live under `data/processed/iterater_human_grouped_v1/`.

## Split correction, context and transformations

The published train/dev/test split has 13 train–dev and 16 train–test document overlaps. To avoid evaluating on sentences from training documents, the preparation script merges all published sentence splits, retains the original split as `source_upstream_split`, deduplicates only exact same-document/same-revision-depth sentence pairs with the same label, and assigns entire documents with a stable SHA-256 70/15/15 rule. The salt, input hashes, output hashes, row IDs and document-ID hash are recorded in immutable manifests. Original rows remain available in `data/raw/`.

Each sentence record was joined to the same document ID and revision depth in the document export. This produced document context for all retained records. Local context for modeling is bounded to up to two neighboring sentences before/after the target; document context is used only in the full-document ablation. This avoids sending full manuscripts by default.

The CLI loader maps known labels through the reviewed taxonomy, retains raw labels, and keeps empty `after_sent` values as possible human deletions. It does not synthesize missing labels. A training run requires the explicit `--license-verified` acknowledgment after source-term review.

## Reproduction

```sh
python scripts/prepare_iterater_splits.py
python -m ateval revisions inspect iterater data/processed/iterater_human_grouped_v1/sentence_train.jsonl --split train --license Apache-2.0 --license-verified
```

The preparation script refuses to overwrite any existing immutable prepared output or report. Inspect the split manifest JSON for exact file hashes and record IDs.

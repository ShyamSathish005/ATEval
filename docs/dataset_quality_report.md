# IteraTeR-HUMAN grouped dataset quality report

**Date:** 2026-11-01
**Source:** public IteraTeR-HUMAN exports, sentence/document data; details and terms in [`dataset_ingestion_report.md`](dataset_ingestion_report.md).
**Audit data:** [`data/manifests/revision_dataset_audit.json`](../data/manifests/revision_dataset_audit.json).

## Grouped partitions

| Partition | Sentence pairs | Source documents | Documents joined | Empty source | Empty target (deletion candidate) | Exact no-op |
|---|---:|---:|---:|---:|---:|---:|
| Train | 2,775 | 285 | 100% | 0 | 36 | 57 |
| Validation | 649 | 72 | 100% | 0 | 9 | 15 |
| Test | 588 | 70 | 100% | 0 | 3 | 4 |

After removal of same-document, same-depth, exact sentence-pair/label duplicates, 4,012 annotated pairs remain. The grouped result totals 285/72/70 unique source documents. No document is shared across partitions. The split is document-held-out, not author-held-out.

## Upstream leakage and duplicates

Published source metadata had 13 train–dev and 16 train–test overlapping document IDs; dev and test had no overlap. These overlaps are listed in `revision_dataset_audit.json`. Six exact sentence pair/label duplicates within the same source document and revision depth were removed. No exact pair/label duplicates remained across different source documents. Exact source-equals-target examples are retained in prepared files, but excluded from the intention classification task because the corpus does not label whether an edit was necessary.

A SimHash locality-sensitive candidate search followed by exact character 5-gram Jaccard verification at threshold 0.95 found 506 near-duplicate sentence pairs; all were within the same source document, and zero crossed document boundaries. These repeated variants therefore remain together in a single split. Near-duplicate detection is a heuristic and may miss paraphrases.

## Labels and domains

| Original IteraTeR tag | Train | Validation | Test |
|---|---:|---:|---:|
| clarity | 1,088 | 263 | 250 |
| fluency | 662 | 150 | 124 |
| meaning-changed | 612 | 150 | 134 |
| coherence | 267 | 71 | 55 |
| style | 95 | 11 | 22 |
| others | 51 | 4 | 3 |

The labels are imbalanced. The rare `style` and `others` categories have too few validation/test instances for stable conclusions. The tag `meaning-changed` reflects an annotation label; it is not proof that the edit was semantically harmful. The product taxonomy maps `fluency` to grammar, `coherence` to cohesion, `style` to author style, and `others` to other, while preserving raw tags.

Source document counts by domain are train: arXiv 119, news 125, Wikipedia 109, unknown 26; validation: 19/34/27/6; test: 24/30/34/6. The arXiv records are abstracts. Because some test domains have only 24–34 documents, domain-sliced scores are exploratory and are reported with their sample counts.

## Missingness and edge cases

- No blank source sentences and no missing labels were found.
- 48 target sentences are blank and retained as possible deletion edits.
- 76 pairs are normalized exact no-ops across the full retained corpus (train 57, validation 15, test 4); they do not train the intention classifier.
- Document context joins succeeded for 100% of retained sentence pairs.
- 506 near-duplicate pairs were detected, all within source documents; none cross the new grouped split boundary.
- Raw human-vote disagreements are retained as provenance where provided. There are no author identifiers, so author-held-out generalization cannot be estimated.

No item-level quality estimate is inferred from this structural audit. The corpus is small, domain-skewed and dominated by clarity/fluency/meaning-change annotations. It cannot support claims about all academic disciplines or an individual author's voice.

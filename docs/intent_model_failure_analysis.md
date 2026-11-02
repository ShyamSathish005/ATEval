# Milestone 3 intent model failure analysis

**Status:** audit complete before any model-size increase
**Evidence:** saved M3 manifests, configuration, sklearn artifacts, held-out comparison and DistilBERT run
**Outcome under investigation:** best held-out macro-F1 = **0.2050**, full-document TF-IDF + balanced logistic regression

## Finding

The 0.2050 result is principally a task and data limitation, not evidence that a larger classifier is needed. M3 predicts an edit-intention label from text *before* the edit, but the published IteraTeR intention classifier receives both the original and revised text for each action. The revision itself is direct evidence of the intended operation. M3 therefore evaluates a harder and different inference problem. In addition, the M3 model scores six mapped classes, including two extremely sparse classes; its document context omits an explicit target marker; and the class map merges semantically distinct annotation decisions.

The score is a valid result for the current grouped, six-class, source-only task. It is not a reproduction of IteraTeR's classifier score and should not be interpreted as one.

## Data, labels, and class imbalance

The source exports include IteraTeR-HUMAN sentence pairs and document revisions. All six files were hash-recorded in `data/manifests/revision_dataset_audit.json`; exact same-document/same-depth/same-label pair duplicates were removed (6 excess rows), while 48 deletion candidates and 76 exact no-ops were retained in the prepared audit. No-op pairs were excluded from intention classification because they have no edit-necessity annotation. Document context matched the paired source document for 100% of retained rows. Near-duplicate analysis found 506 pairs within the same source document and no cross-document duplicate pairs.

The raw-to-canonical mapping used in M3 was:

| IteraTeR raw label | M3 label | Train | Dev | Test |
|---|---|---:|---:|---:|
| `clarity` | `clarity_improvement` | 1,086 | 263 | 250 |
| `fluency` | `grammar_correction` | 616 | 135 | 121 |
| `coherence` | `cohesion_improvement` | 267 | 71 | 55 |
| `meaning-changed` | `meaning_changed` | 612 | 150 | 133 |
| `style` | `author_style` | 94 | 11 | 22 |
| `others` | `other` | 43 | 4 | 3 |

These are counts after no-op exclusion: 2,718 train, 634 validation, and 584 test edits. The test label proportions range from 42.8% clarity to 0.5% `other`; the class imbalance ratio is 83.3:1 (clarity:`other`). The six-class macro average weights the three `other` test examples as much as the 250 clarity examples. F1 for either rare class has high sampling uncertainty. `class_weight="balanced"` adjusts loss contributions but cannot add examples or resolve label ambiguity.

The crosswalk also changes the task's meaning: `fluency` is represented as grammar correction, `coherence` as cohesion, and all `others` as one catch-all. The source label is retained in each record, but those mapped names should not be treated as exact equivalence to the original taxonomy. In particular, mapped `other` should be an audit bucket rather than a product-quality class.

## Split and leakage

The upstream HUMAN partitions overlap by source document: 13 documents in train/dev and 16 in train/test. M3 merged and regrouped records deterministically by source document with SHA-256 70/15/15 assignment. The resulting non-overlapping partitions contain 285/72/70 documents, and the held-out metric refuses training/test document overlap. The source manifest records the upstream overlap IDs and the new split hashes.

This corrects document leakage for the reported score, but the new split is not the official IteraTeR split. The hash assignment was not optimized for label-stratification at document level. Example-level class proportions are broadly similar in train and test, but rare `other` support is only 3 in test and 4 in validation. The resulting 584-example test set is larger than IteraTeR's published 364 HUMAN sentence test pairs because M3 merged upstream splits, removed cross-split overlap through regrouping, and created a new held-out assignment.

## Feature and context audit

### Classical TF-IDF models

- Word features are sklearn's default lowercased tokenization, unigrams and bigrams; character features are 3–5 character n-grams. Each vocabulary is capped at 12,000 features. Sublinear term frequency is used; no explicit lemmatization, domain tokenizer, learned subword representation, sentence embedding, edit alignment feature, or syntactic feature is present.
- There is no TF-IDF token truncation. Longer contexts instead add many irrelevant features and dilute the target signal. Only word bigrams encode word order; wider syntax and discourse relations are not represented.
- The sentence input is section label plus the original sentence. The local input inserts `TARGET` between up to two preceding and following sentences. The document input is the whole available source document preceded by `DOCUMENT_CONTEXT`, but it does **not** mark the target sentence's position or highlight it. Therefore the representation cannot reliably distinguish local target evidence from topic vocabulary elsewhere in the document.
- The loader assigns `abstract` to all arXiv examples and uses `news`/`wiki` domain values as `section_type` for those domains. These are not observed manuscript section labels. The source data does not provide dependable section-level context for all examples.
- The source-only classifier does not include `revised_text`, edit spans, or a diff. Those are especially useful for learning the intent label, and the official IteraTeR classifier does include original and revised text.

### DistilBERT frozen-embedding baseline

The frozen DistilBERT comparison used uncased WordPiece tokenization, a 256-token maximum, truncation, final-layer masked-mean pooling, and a balanced logistic-regression head. Recounting the exact prepared inputs with the pinned tokenizer found:

| Input | Inputs over 256 tokens | Test over 256 | Target tokens partly truncated |
|---|---:|---:|---:|
| Sentence | 1/3,936 (0.03%) | 1/584 | 1/3,936 |
| Local context | 122/3,936 (3.10%) | 20/584 | 4/3,936 |

Median lengths were 42 tokens (sentence) and 143 (local); local-context p90 was 212. Truncation is not the main explanation for the low result, although it drops some trailing context and very occasionally cuts the target. Full document context was not run through DistilBERT. The embedding model was frozen rather than fine-tuned, and pooling averages all remaining tokens, including section markers and context.

## Results and error patterns

The six-class majority baseline reached 0.0999 macro-F1 and 0.4281 accuracy. Balanced TF-IDF logistic regression reached 0.1958 sentence, 0.1931 local-neighbor, and 0.2050 full-document macro-F1, with accuracies 0.3408, 0.3493, and 0.3373. The full-document model's macro-F1 advantage over the sentence model is 0.0092 while accuracy is lower; that is not evidence of a reliable context benefit. Weighted F1 for full document was 0.3365.

For the UI's local model, the held-out per-class results were:

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| author style | 0.000 | 0.000 | 0.000 | 22 |
| clarity | 0.477 | 0.492 | 0.484 | 250 |
| cohesion | 0.075 | 0.091 | 0.082 | 55 |
| grammar | 0.290 | 0.347 | 0.315 | 121 |
| meaning changed | 0.301 | 0.256 | 0.277 | 133 |
| other | 0.000 | 0.000 | 0.000 | 3 |

Sentence TF-IDF similarly had zero F1 on style and other, 0.458 clarity, 0.136 cohesion, 0.350 grammar, and 0.231 meaning-changed. Full-document TF-IDF class F1 was 0.000 style, 0.439 clarity, 0.186 cohesion, 0.330 grammar, 0.276 meaning-changed, and 0.000 other. These are the main sources of macro-F1 loss. The best model's held-out confusion matrix (rows are gold; columns are prediction) is:

| Gold \\ Predicted | Style | Clarity | Cohesion | Grammar | Meaning changed | Other |
|---|---:|---:|---:|---:|---:|---:|
| Style | 0 | 6 | 5 | 8 | 3 | 0 |
| Clarity | 0 | 104 | 37 | 57 | 52 | 0 |
| Cohesion | 0 | 21 | 13 | 6 | 15 | 0 |
| Grammar | 0 | 39 | 11 | 43 | 28 | 0 |
| Meaning changed | 0 | 54 | 18 | 24 | 37 | 0 |
| Other | 0 | 0 | 1 | 2 | 0 | 0 |

The detailed confusion counts for all three contexts and both classifier families remain in `models/revisions/iterater_human_grouped_v1/comparison.json`. The largest errors include clarity→grammar/meaning-changed, meaning-changed→clarity/grammar, grammar→clarity, and most cohesion edits misclassified as clarity/meaning-changed.

The calibrated SVM variants were near the majority baseline: the sentence SVM predicts the majority label for almost all examples and has 0.1111 macro-F1; local and document macro-F1 are 0.0999. Calibration does not improve class discrimination. Logistic-regression `n_iter_` for sentence/local/document models was 35/28/32 against `max_iter=600`; all six linear SVM estimators used in the saved calibrated models stopped at 551–940 iterations against `max_iter=1,200`. There is no indication that optimization hit the iteration cap. Increasing iteration count or model size is not supported by this audit.

The frozen DistilBERT contextual representations scored 0.1964 macro-F1 for sentence context and 0.1639 for local context. Sentence accuracy was 0.2877 and ECE 0.3988; local accuracy was 0.2534 and ECE 0.4011. This baseline was frozen, not fine-tuned, and it did not improve macro-F1 over TF-IDF. Its confidence estimates were poorly calibrated on this test sample.

## Comparison with original IteraTeR protocol

IteraTeR's paper describes a RoBERTa-large multiclass classifier that receives **the original and revised text** per edit action. The HUMAN sentence corpus is reported as 3,254/400/364 train/dev/test pairs. Its paper describes 15 training epochs, batch size 4, learning rate 1e-5, a single 16 GB Quadro RTX 4000, and reports per-intention F1 (clarity 0.69, fluency 0.80, coherence 0.32, style 0.13, meaning-changed 0.53). The official repository reproduces those class-wise numbers. M3 instead used 2,718/634/584 rows under a regenerated document-grouped split, six mapped labels, source text and optional context without the revised side, and aggregate six-class macro-F1. These protocols differ in inputs, split, training data size, and label inventory. The reported IteraTeR class F1 figures cannot be directly compared to M3's 0.2050 aggregate macro-F1.

The published generation benchmark is also different: IteraTeR BART and PEGASUS were trained on IteraTeR-FULL, not HUMAN, and the repository reports SARI/BLEU/ROUGE-L on that model/data setup. FULL includes model-propagated labels and is not a human-annotated training equivalent. The reported generation values do not transfer to M3's grouped HUMAN held-out set.

## Root-cause summary and next experiments

1. **Different prediction task:** M3 omits the revised sentence, although that is part of the official classifier's input. Keep a separate source-only intent-estimation task and add a paired before/after reproduction as a distinct benchmark.
2. **Too little support for all-class macro-F1:** report bootstrap confidence intervals clustered by document and per-class supports; obtain more rights-cleared examples for rare labels before claiming robust six-class behavior.
3. **Label crosswalk ambiguity:** report original IteraTeR's five labels for aligned comparisons. Keep the product taxonomy as a separately evaluated, reviewed crosswalk rather than equating broad mapped labels with original definitions.
4. **Weak target/context representation:** use explicit target spans and source/revision diff features for intent classification; for editing, pass only relevant paragraph/section context with target delimiters and protected spans.
5. **No strong context-effect evidence:** compare contexts with the same groups, seed, and scoring set, using cluster-bootstrap uncertainty and human ratings. The current +0.0092 full-document macro-F1 change is descriptive only.

The held-out split remains untouched for a reproduction. No larger classifier was trained as part of this audit. No AI-detector score was used.

## Sources

- [IteraTeR ACL 2022 paper](https://aclanthology.org/2022.acl-long.250.pdf), especially the intention classification setup and computational experiments.
- [Official IteraTeR repository and reported baseline tables](https://github.com/vipulraheja/iterater).
- [M3 comparison artifact](../models/revisions/iterater_human_grouped_v1/comparison.json), [dataset audit manifest](../data/manifests/revision_dataset_audit.json), [DistilBERT run](../models/revisions/iterater_distilbert_grouped_v1/comparison.json), and [experiment configuration](../experiments/iterater-distilbert-grouped-intent-v1.json).

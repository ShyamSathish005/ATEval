# ATEval Milestone 3 report

**Status:** implemented and evaluated as an initial local research baseline. This is not a validated academic editor.  
**Run date:** 2026-11-01  
**Dataset:** IteraTeR-HUMAN; Apache-2.0 as declared on its public dataset cards.  
**Reproduction config:** [`experiments/iterater-human-document-grouped-classical-intent-v1.json`](../experiments/iterater-human-document-grouped-classical-intent-v1.json).

## Implemented

- Preserved the six raw HUMAN exports and created stable, document-grouped partitions, immutable split manifests, hashes and a data-quality audit. Upstream train/dev/test document overlaps were detected and corrected for evaluation.
- Fixed `.json` JSONL loading, joined paired document context, retained raw labels and no-op/deletion examples in prepared data, and prevented document leakage in the benchmark.
- Trained and compared majority, word+character TF-IDF logistic regression and sigmoid-calibrated linear SVM models for sentence-only, local-neighbor and full-document input. Hyperparameter selection used validation macro-F1; test data remained held out. Trained artifacts have separate metadata files with environment, source/data hashes, feature settings, seed, selected C and checksums.
- Added held-out identity/no-edit and existing phrase-rule generation comparisons. Existing rules run as a benchmark-only system; the UI still requires author acceptance.
- Added a local API intent preview using the local-context logistic regression model and a UI control. Predictions are not stored, do not trigger edits, and explicitly say that whether a change is needed is unknown. Uncalibrated outputs are displayed as scores, not probabilities.
- Kept exact protected-span preservation explicitly separate from semantic equivalence. Audits remain reversible and omit the full manuscript.
- Updated the evaluation protocol and added a blind academic-review rubric, but did not recruit or rate expert reviewers.

## Intent classification results

Document-held-out test: 584 non-identical sentence pairs from 70 source documents (4 unchanged pairs were excluded because IteraTeR does not provide edit-necessity labels). The majority baseline's class was `clarity_improvement`. All test metrics below are on the held-out groups; no training score is reported as generalization.

| Input context | Model | Accuracy | Macro F1 | Weighted F1 | ECE (10-bin) |
|---|---|---:|---:|---:|---:|
| Majority | Majority class | 0.4281 | 0.0999 | 0.2566 | — |
| Sentence | Logistic regression | 0.3408 | 0.1958 | 0.3340 | 0.0613 |
| Sentence | Linear SVM, calibrated | 0.4349 | 0.1111 | 0.2711 | 0.0311 |
| Neighbor sentences | Logistic regression | 0.3493 | 0.1931 | 0.3434 | 0.0339 |
| Neighbor sentences | Linear SVM, calibrated | 0.4281 | 0.0999 | 0.2566 | 0.0239 |
| Full available document | Logistic regression | 0.3373 | 0.2050 | 0.3365 | 0.0638 |
| Full available document | Linear SVM, calibrated | 0.4281 | 0.0999 | 0.2566 | 0.0286 |
| DistilBERT frozen, sentence | Contextual embeddings + logistic head | 0.2877 | 0.1964 | 0.3017 | 0.3988 |
| DistilBERT frozen, local | Contextual embeddings + logistic head | 0.2534 | 0.1639 | 0.2654 | 0.4011 |

The best macro-F1 is 0.2050 (full-document logistic regression), a small absolute increase of 0.105 over majority while accuracy decreases. The frozen contextual transformer sentence baseline is effectively tied on macro-F1 (0.1964 vs 0.1958 for sentence TF-IDF), with lower accuracy, lower weighted F1 and much worse calibration diagnostics. Adding local context lowers its macro-F1 to 0.1639. It does not improve over the simpler baseline. The local-context TF-IDF logistic regression used by the UI has macro-F1 0.1931, weighted F1 0.3434. Local-context per-class precision/recall/support: author style 0.000/0.000/22; clarity 0.477/0.492/250; cohesion 0.075/0.091/55; grammar 0.290/0.347/121; meaning changed 0.301/0.256/133; other 0.000/0.000/3. The model fails to identify either rare author-style or `other` examples on this test set. Class balancing improves macro-F1 over majority but trades away accuracy; the calibrated SVM largely predicts the majority class.

Adding local neighboring sentences did not improve macro-F1 over sentence-only input (0.1931 vs 0.1958). Full-document context raised macro-F1 by about 0.009 over sentence-only but had lower accuracy, and domain slices are small. These results do not establish a useful context benefit. ECE and Brier scores are descriptive sample diagnostics; neither makes the model reliable or its label a correct edit recommendation.

The full classical per-class scores, confusion counts, calibration diagnostics and domain slices are in [`comparison.json`](../models/revisions/iterater_human_grouped_v1/comparison.json). Frozen DistilBERT results and scores are in [`comparison.json`](../models/revisions/iterater_distilbert_grouped_v1/comparison.json). See the classical [`intent-model-card.md`](../models/revisions/iterater_human_grouped_v1/intent-model-card.md) and [transformer baseline card](../models/revisions/iterater_distilbert_grouped_v1/model-card.md).

## Revision generation comparison

The same 588 test examples from 70 documents were scored against one human target each. The identity baseline has BLEU 0.7921, ROUGE-L 0.8665, edit-operation F1 0 and a 0% change rate. Phrase rules have BLEU 0.7918, ROUGE-L 0.8664, edit-operation precision 0.3333, recall 0.00065, F1 0.00129 and a 0.68% change rate. Both preserve the tested numeric, citation and protected-span sequences in all 588 examples. No-op unnecessary edits were 0/4 for both.

These overlap scores mostly reflect copying and do not measure writing quality. The rule baseline barely changes held-out text and did not improve the overlap diagnostics. Structural span preservation does not prove meaning preservation. The complete output is [`generation-comparison.json`](../reports/milestone3/generation-comparison.json); its model card is [`generation-model-card.md`](../reports/milestone3/generation-model-card.md).

## Context and model-resource decisions

Sentence, neighbor-context and full-document intent ablations were run as above. Full-document input did not materially improve the result; no generation ablation or expert preference experiment has run yet. Therefore the current editor has no learned text-generation model: it continues to make only narrow phrase proposals subject to author review.

The [DistilBERT base checkpoint](https://huggingface.co/distilbert/distilbert-base-uncased/tree/12040accade4e8a0f71eabdb258fecc2e7e948be) declares Apache-2.0 and provides a general English masked-language encoder, not an academic editor. We extracted frozen masked-mean contextual embeddings from its pinned checkpoint and trained a balanced logistic classification head on IteraTeR-HUMAN. It ran on CPU in 164 seconds after the weights were cached under `/private/tmp`; the checkpoint and manuscript text were not added to application persistent storage. PyTorch and Transformers were installed into a temporary dependency target; MPS and CUDA were unavailable. The transformer experiment has no quality advantage over TF-IDF and its ECE is high (~0.40), so it is not integrated into the UI. The investigated IteraTeR BART/PEGASUS fine-tuned checkpoints did not provide an explicit license declaration on their model cards, so their weights were not downloaded or used. No encoder fine-tuning or fine-tuned sequence-to-sequence system was completed. [Hugging Face's text-classification documentation](https://huggingface.co/docs/transformers/main/tasks/sequence_classification) describes the standard fine-tuning approach; this run uses frozen embeddings to keep the model within the available CPU budget.

## Preservation, CLI, API and UI

- Existing preservation tests confirm exact sequence handling for protected LaTeX/math/citation/reference/numeric spans and that semantic equivalence is reported as `not_assessed`.
- `revisions benchmark-intent` trains all classical baselines from verified local exports and refuses an existing output directory or document leakage. `revisions benchmark-generation` writes a held-out comparison report without overwriting. Existing inspect/train/evaluate commands remain available.
- `revisions predict-trained-intent "sentence" --context-before ... --context-after ...` returns a checksum-verified advisory label from the local model. It reports an uncalibrated top-class score, held-out macro-F1, `modification_necessary: null`, and never edits text.
- `scripts/benchmark_distilbert_intent.py` provides the frozen contextual-encoder comparison. Its pinned model is downloaded only when `--allow-model-download` is passed; the weights remain in a caller-selected Hugging Face cache. It is a CPU-capable research baseline, not a generation model.
- `/api/v1/writing/revision-intent` checks the model checksum, uses the first user-selected local sentence and bounded context, returns an advisory class and an uncalibrated top-class score, and stores nothing. The UI labels it advisory, shows the test macro-F1, says edit necessity is undetermined, and leaves changes under existing accept/reject controls.
- The API accepts the model only at its fixed workspace path. Joblib/pickle artifacts should be loaded only from this trusted workspace and matching Python/scikit-learn environment.
- Human review has not occurred. No claim-level contradiction/entailment model, factual QA validation, or semantic-equivalence guarantee was added.

## Reproduction and verification

```sh
python -m pip install -e '.[revision-ml]'
python -m ateval revisions benchmark-intent \
  data/processed/iterater_human_grouped_v1/sentence_train.jsonl \
  data/processed/iterater_human_grouped_v1/sentence_dev.jsonl \
  data/processed/iterater_human_grouped_v1/sentence_test.jsonl \
  --train-documents data/processed/iterater_human_grouped_v1/document_train.jsonl \
  --dev-documents data/processed/iterater_human_grouped_v1/document_dev.jsonl \
  --test-documents data/processed/iterater_human_grouped_v1/document_test.jsonl \
  --source-license Apache-2.0 --license-verified --seed 17 \
  --output-dir models/revisions/iterater_human_grouped_rerun_v1
python -m ateval revisions benchmark-generation \
  data/processed/iterater_human_grouped_v1/sentence_test.jsonl \
  --test-documents data/processed/iterater_human_grouped_v1/document_test.jsonl \
  --source-license Apache-2.0 --license-verified \
  --output reports/milestone3/generation-comparison-rerun.json
python -m ateval revisions predict-trained-intent \
  "The results are not clear." --section-type abstract
python -m pip install -e '.[revision-transformer]'
python scripts/benchmark_distilbert_intent.py \
  data/processed/iterater_human_grouped_v1/sentence_train.jsonl \
  data/processed/iterater_human_grouped_v1/sentence_dev.jsonl \
  data/processed/iterater_human_grouped_v1/sentence_test.jsonl \
  --train-documents data/processed/iterater_human_grouped_v1/document_train.jsonl \
  --dev-documents data/processed/iterater_human_grouped_v1/document_dev.jsonl \
  --test-documents data/processed/iterater_human_grouped_v1/document_test.jsonl \
  --allow-model-download --output-dir models/revisions/iterater-distilbert-rerun-v1
```

The immutable preparation and experiment commands intentionally refuse overwrites; choose a new output path for another run. The checked-in prepared partitions can be used directly; the preparation script creates a fresh immutable version and is intended for an empty output location. For this implementation run, `PYTHONPATH=/private/tmp/ateval-ml` points to scikit-learn 1.9.1 installed in a temporary target and does not modify the project Python environment. The DistilBERT experiment uses `revision-transformer` dependencies and a temporary Hugging Face cache. Verification completed: Python `unittest` 29/29 passed (including document-context loading, API prediction, privacy and semantic-preservation checks); Vite/TypeScript production build passed; Sites packaging checks 4/4 passed. API prediction and CLI prediction smoke checks both returned advisory-only results with no text persisted or edited. The frozen transformer baseline was run successfully on CPU.

## Limitations and next evidence gates

This is a small, imbalanced and domain-limited corpus; grouped splitting addresses document leakage but cannot establish author generalization. The strongest model has low macro-F1 and rare categories are not recognized. No transformer encoder fine-tuning, fine-tuned sequence-to-sequence system, human expert rating, inter-rater agreement, semantic-equivalence study, author-held-out analysis, or measurable quality gain has been demonstrated. The intent predictor is presented only as a research cue. Before a stronger writing-quality claim, gather a rights-cleared multi-discipline dataset with author permissions, preregister a blinded reviewer study, compare against copy/no-edit and rules on identical documents, report clustered uncertainty and subgroup failures, and implement independent claim/technical preservation checks.

No detector scores were used as a training, selection or evaluation objective. No novelty or authorship claim is made.

# M5.2 Detector Feature Analysis

## Scope and method

This analysis uses the frozen `stylometric-baseline` implementation. It does
not add detector algorithms or change the production signal. Feature
directions and thresholds for diagnostic ablations are selected on the
validation split only. The test split is used once for frozen comparisons.

The six implemented features are:

1. type-token ratio;
2. mean sentence length;
3. sentence-length variation;
4. function-word ratio;
5. punctuation density;
6. repeated-trigram rate.

MTLD, readability indices, and richer vocabulary-distribution statistics are
not implemented by the frozen baseline. They are recorded as unavailable
rather than reconstructed from undocumented approximations.

## Reproduction

```sh
python3 scripts/prepare_detection_splits.py --manifest-dir /tmp/ateval-m52-manifests
python3 scripts/analyze_m52_detector_failure.py \
  --manifest-dir /tmp/ateval-m52-manifests \
  --output-dir /tmp/ateval-m52-reports
```

The compact configuration is recorded in
[`data/manifests/m5_2_failure_analysis_manifest.json`](../data/manifests/m5_2_failure_analysis_manifest.json).
The generated JSON and SVG diagnostics are intentionally outside Git because
they contain derived records and are reproducible from the ignored manifests.

## Results

| Diagnostic | Test AUROC | 95% CI | Interpretation |
|---|---:|---:|---|
| Frozen combined signal | 0.5541 | 0.5302–0.5771 | Weak separation |
| Type-token ratio | 0.6628 | 0.6440–0.6831 | Some lexical separation; not AI-exclusive |
| Mean sentence length | 0.5568 | 0.5318–0.5836 | Little useful separation |
| Sentence-length variation | 0.7323 | 0.7141–0.7510 | Stronger association, likely genre/length-sensitive |
| Function-word ratio | 0.7635 | 0.7459–0.7814 | Strongest single feature, not authorship evidence |
| Punctuation density | 0.6691 | 0.6477–0.6900 | Moderate association; formatting-sensitive |
| Repeated-trigram rate | 0.5158 | 0.4929–0.5365 | Near chance |

These are exploratory feature associations. A feature can correlate with the
dataset label because of response style, editing, topic, length, or
preprocessing. None establishes that the feature is specific to AI writing.

The frozen threshold is `0.37`, selected by Youden's J on validation. On the
test set it produced:

- AUROC `0.5541` (95% CI `0.5302–0.5771`);
- precision `0.9626`, recall `0.3534`, F1 `0.5170`;
- FPR `0.2467`, FNR `0.6466`;
- confusion matrix: TP `2,859`, FP `111`, TN `339`, FN `5,232`.

The random-permutation diagnostic produced AUROC `0.4839`, close to chance.
The question-length-only diagnostic produced AUROC `0.4992`. A word-count-only
diagnostic reached AUROC `0.7108`, but its validation-selected threshold
collapsed to a degenerate all-negative decision on test. This contrast shows
that length is a major dataset signal but not a reliable decision rule.

Length matching reduced the test cohort to 892 records (446 per class):
AUROC `0.6296` (95% CI `0.5971–0.6664`), FPR `0.2444`, and FNR `0.5493`.
The signal therefore changes under a basic confounder control but remains
unsafe for authorship decisions.

## Threshold and curve artifacts

The generated output contains:

- `roc_curve.svg`;
- `precision_recall_curve.svg`;
- `feature_distributions.svg`;
- `confusion_matrix.json`;
- `m52_failure_analysis.json`, including the threshold comparison table,
  feature ablations, bootstrap intervals, and subgroup records.

The precision-recall result must be interpreted with the test prevalence
(8,091 AI and 450 human records); it is not evidence of broad detector
quality.

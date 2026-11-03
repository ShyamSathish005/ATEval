# M5.1 Stylometric Baseline Benchmark Results

## Status

This is an experimental benchmark, not an authorship or misconduct decision
system. The detector remains an uncalibrated research signal and its score is
not an authorship probability.

The run used the locally downloaded TXD-22 v1 file:

- SHA-256: `232c260f8caf7ea61a331f39fa730956862afbe0c5fc554720daa07d215a2f7d`
- 66,000 source rows; 57,000 pure human/AI Task A rows; 9,000 mixed rows
- 70/15/15 group split by prompt, with document and author identity unioning
- seed `42`; threshold selected on validation only by Youden's J
- no external data is committed to Git

Reproduce:

```sh
python3 scripts/prepare_detection_splits.py --manifest-dir /tmp/ateval-m5-manifests
python3 scripts/benchmark_stylometric_baseline.py \
  --manifest-dir /tmp/ateval-m5-manifests \
  --report-dir /tmp/ateval-m5-reports
```

## Task A: human versus AI

The held-out test set contained 8,541 records (8,091 AI and 450 human).

| Metric | Estimate | 95% bootstrap CI |
|---|---:|---:|
| AUROC | 0.5541 | 0.5309–0.5775 |
| AUPRC | 0.9612 | not reported |
| Precision | 0.9626 | not reported |
| Recall | 0.3534 | not reported |
| F1 | 0.5170 | 0.5060–0.5280 |
| False-positive rate | 0.2467 | 0.2076–0.2838 |
| False-negative rate | 0.6466 | 0.6360–0.6566 |

The high AUPRC is affected by the test prevalence (94.7% AI) and must not be
read as strong discrimination. The AUROC is only slightly above chance, while
recall is low and the human negative-control false-positive rate is concerning.

## Length-matched test cohort

The length-matched cohort contained 892 records (446 per class):

- AUROC: `0.6296`
- AUPRC: `0.6642`
- F1: `0.5317`
- false-positive rate: `0.2444`
- false-negative rate: `0.5493`

This does not establish robust authorship separation. It shows that the
observed signal changes when the class length distribution is controlled.

## Mixed authorship and domain limitations

Mixed-authorship rows were analyzed separately as Task B signal distributions;
they were not converted to binary labels. TXD-22 has no span annotations, so
Task D localisation metrics were not calculated.

TXD-22’s repeated prompts make a strict unseen-model holdout incompatible with
prompt-disjoint splitting: holding out a model would move the shared prompt
groups to test and leave degenerate human/AI train or validation support. The
default benchmark therefore does not claim unseen-generator generalisation.
Passing `--unseen-model` makes the splitter fail closed if any binary split is
degenerate.

## Interpretation

The baseline does not justify an AI-authorship claim. The most associated
features in this run were function-word ratio (`r_pb=-0.1900`), sentence-length
variation (`-0.1295`), punctuation density (`+0.1185`), and type-token ratio
(`+0.1086`). These are descriptive associations, not causal evidence.

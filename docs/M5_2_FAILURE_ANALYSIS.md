# ATEval M5.2 — Stylometric Detector Failure Analysis

## Research decision: B — supporting signal only

Retain the stylometric baseline only as a transparent supporting signal within
a future, separately validated ensemble or review workflow. Do not retain it
as a primary AI-writing detector, and do not expose its score as an authorship
probability.

This decision preserves the useful research value of inspectable features
while rejecting unsupported claims. It is not a decision to add an ensemble
in this milestone.

## Verification of M5.1

The original M5.1 command was rerun against freshly generated external
manifests from the unchanged TXD-22 file:

- source SHA-256:
  `232c260f8caf7ea61a331f39fa730956862afbe0c5fc554720daa07d215a2f7d`;
- label mapping: `human = 0`, pure generator labels `ai = 1`, mixed labels
  excluded from Task A;
- positive score direction: higher `signal_score` is treated as more AI-like;
- threshold: `0.37`, selected from validation only by Youden's J;
- test: 8,541 records, 8,091 AI and 450 human.

Independent reproduction returned AUROC `0.5541` and human FPR `0.2467`.
The confusion matrix was TP `2,859`, FP `111`, TN `339`, FN `5,232`.
The independent bootstrap FPR interval was `0.2093–0.2851` (95%).
M5.1 was not overwritten. Its documented result remains unchanged.

## Failure analysis

The combined signal is weak despite several individual feature associations.
The most useful exploratory features were function-word ratio (AUROC
`0.7635`) and sentence-length variation (AUROC `0.7323`), followed by
punctuation density and type-token ratio. Repeated-trigram rate was near
chance (`0.5158`), and mean sentence length was weak (`0.5568`).

The feature-level result is not a detector success. The word-count-only
diagnostic reached AUROC `0.7108`, demonstrating that dataset composition and
response length can create substantial separation. Its validation-selected
threshold produced an all-negative test decision, which is a warning against
using superficial correlations as a classifier. The question-length-only
baseline was near chance (`0.4992`), and the random permutation diagnostic was
near chance (`0.4839`).

After length matching, the frozen signal achieved AUROC `0.6296`, with FPR
`0.2444` and FNR `0.5493`. Human false positives remain unacceptable for an
academic evaluator. The test cohort is highly imbalanced, so AUPRC and
precision are prevalence-dependent and do not rescue the conclusion.

The dataset provides only one usable domain bucket. Generator subgroups are
AI-only, so their AUROC is undefined; generator signal summaries are
exploratory and cannot establish generalisation to unseen generators.

## Mixed authorship

The 9,000 mixed-authorship samples were not forced into the binary task.
Their signal means varied by source label, including:

| Source label | Mean signal |
|---|---:|
| AI-generated and AI-refined | 0.3771 |
| AI-generated and AI-refined and Human-written | 0.3278 |
| AI-generated and Human-written | 0.3203 |
| Human-written and AI-refined | 0.3544 |

These values are descriptive distributions, not binary accuracy or
localisation results. TXD-22 has no span-level ground truth.

## Limitations and next step

TXD-22 consists of short responses, not complete academic manuscripts. It
does not provide the structure, citations, equations, discipline metadata,
verified participant IDs, or realistic manuscript editing histories required
for the intended application. See
[`ACADEMIC_DOMAIN_GAP.md`](ACADEMIC_DOMAIN_GAP.md).

The next research milestone should qualify a manuscript-focused corpus before
adding detector methods. Any future ensemble must be evaluated with the same
prompt/document/author grouping, held-out generators and disciplines where
metadata supports them, and a human academic negative-control cohort.

## Reproducible outputs

Run:

```sh
python3 scripts/prepare_detection_splits.py --manifest-dir /tmp/ateval-m52-manifests
python3 scripts/analyze_m52_detector_failure.py \
  --manifest-dir /tmp/ateval-m52-manifests \
  --output-dir /tmp/ateval-m52-reports
```

The analysis configuration is recorded in
[`data/manifests/m5_2_failure_analysis_manifest.json`](../data/manifests/m5_2_failure_analysis_manifest.json).

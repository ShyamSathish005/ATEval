# Detector evaluation plan

The detector benchmark will report precision, recall, F1, AUROC/AUPRC where
appropriate, false-positive rate on human text, threshold calibration,
cross-model and domain generalisation, passage localisation, short-passage
performance, and mixed/edited-text performance.

Splits must be grouped by source document and author. Generation models should
be held out where feasible. Threshold selection and calibration must use a
validation split, never the final test split. Confidence intervals should use
document-clustered resampling.

## M5 baseline status

The `stylometric-baseline` is executable and deterministic, but no valid
labelled detector corpus is currently available in the repository. Therefore
there are no benchmark scores, no calibrated threshold, no AUROC, and no
authorship probability. The baseline output is a research signal with
method-specific uncertainty and explicit abstention through its limitations.

Reproduce the deterministic unit test with:

```sh
python -m pytest -q tests/test_detectors.py
```

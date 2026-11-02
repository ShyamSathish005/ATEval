# Revision baseline report

**Date:** 2026-11-01 · **ATEval milestone:** 2 · **Status:** software baseline verified; no corpus benchmark

## What was implemented

- Local JSON, JSONL, and CSV adapters for IteraTeR sentence/document exports and arXivEdits edit exports.
- Provenance-carrying revision records, preserved raw labels, canonical intent crosswalk, edit spans, annotation agreement share, split and stage fields.
- arXivEdits gate requiring per-paper/per-source-version license entries and an explicit permitted-license list; no network fetches.
- Transparent monotonic CPU sentence alignment and character-level edit spans.
- CPU multinomial Naive Bayes intent baseline with new-file-only model output and stored training document IDs.
- Accuracy, macro/per-class precision-recall-F1 and confusion output; evaluation rejects train/test document overlap.
- Descriptive revision-depth aggregation and end-to-end tests for adapters, gating, alignment, taxonomy, model serialization, and split leakage.
- Context-carrying edit proposals in the current author review path, with stage-one abstention and no automatic prose changes.

## Results

| Evidence | Result |
|---|---|
| Synthetic software tests | 7 new revision tests passed; all fixtures are hand-authored and not corpus samples |
| External data records loaded | 0 |
| Intent baseline trained on an academic corpus | No |
| Corpus intent metrics | Not available |
| Expert review / semantic preservation study | Not conducted |
| AI-detector objective | Not used |

The test fixture can train a one-example model to confirm serialization and predicted class paths. That is a functional check, not a meaningful metric. The adapter emits a warning and blocks training when rights are unverified. arXivEdits records remain withheld unless both adjacent source versions pass the license manifest and exact allowlist.

Verification on this workspace: `python3 -m unittest discover -s tests -v` passed all 27 tests. Frontend production build and 4 Sites packaging tests passed. These are software regression checks, not academic benchmark results.

## Interpretation and limitations

This is a reproducible baseline architecture, not evidence of improved academic writing. The Naive Bayes model is small, uses first-label single-label supervision, and will be weak for sparse classes and cross-domain context. No calibration claim is made for its probabilities. The alignment model uses simple token and character similarity rather than the published neural CRF. Corpus adapters are format-aware but cannot determine whether a license permits a particular research use. Human expert review is required to judge intent and meaning.

The published corpora themselves impose limits: arXivEdits is a smaller, subject-skewed collection with mixed source terms; IteraTeR's manually labeled HUMAN set is much smaller than its auto-labeled FULL material, and its published classifier performs poorly for coherence, style, and meaning-changed categories. The crosswalk has imperfect category equivalence. Revision stage is not treated as quality ordering.

## Next empirical gate

Before reporting corpus performance: obtain a rights-reviewed local IteraTeR-HUMAN export (or fully permitted arXivEdits subset), run `ateval revisions inspect`, verify source-grouped train/dev/test disjointness, have two reviewers validate a stratified annotation sample, train on train only, compare with majority on held-out test, and report per-class results with document-clustered uncertainty. Do not expose model-generated rewrites until blinded academic evaluation demonstrates a user-approved preservation non-inferiority bound.

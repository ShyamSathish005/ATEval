# Milestone 4.3 results

## Status

M4.3 completed its reproducible validation and preparation work. Human
evaluation is **pending** because qualified reviewers were not available in this
run. No new large generative model was introduced.

## Preserved experiments

- Pre-work commit: `50d9b3afc5dc8a60d9fae7285f292c540aea488d`
- M4.1 predictions: 588 rows; SHA-256
  `5c7da1abaed3723d79cf89925e4c14c4e56857c0f4fcf08348279e31fa6d1535`
- M4.2 reports: unchanged; exact hashes are in
  [`m43_experiment_manifest.json`](../reports/milestone4_3/m43_experiment_manifest.json)

## Gate validation

The independent typed-sentinel pilot covers missing, duplicated, reordered,
modified, unknown, nested-LaTeX, repeated-term, multi-citation, numeric-range,
negative-number, scientific-notation, percentage, unit, equation, and Unicode
mathematical-symbol cases. All expected adversarial rejections and valid
restorations passed in the generated report. The tests are also in
[`test_scar.py`](../tests/test_scar.py).

This validates structural restoration, not scientific meaning. The original
source is never mutated.

## Claim validation

The proposition pilot produced conservative abstentions for cue and clause
changes and quantitative rejection for changed quantities. It does not claim
that unchanged cues imply preserved propositions. The existing SCAR gate remains
fail-closed; no threshold was weakened based on the 30 examples.

## Calibration and comparison

The available 30-case sample is not sufficient for gate calibration because
its labels are revision intentions, not necessity judgments. Therefore no
precision, recall, false-acceptance, false-rejection, or no-edit estimate is
reported as a scientific result. The 100-row annotation manifest is prepared
with null reviewer fields. Once independently annotated, it can support
abstention-aware calibration and comparison of identity, phrase rules, full
XtraGPT, SCAR, and human references.

The 30-case inspection found harmless changes, plausible useful revisions
rejected by conservative protection, and genuine claim alterations. This
confirms that both false rejection and false acceptance analyses are necessary.
It does not establish that SCAR improves writing quality.

## Research contribution boundary

Author-controlled selective editing, typed exact-span protection, lexical cue
checks, and review-only application are combinations of established ideas.
ATEval's implementation is an engineering and evaluation hypothesis, not a
novel algorithm claim. A meaningful contribution would require a preregistered
ablation, independent necessity annotations, qualified human ratings, and
evidence that safety and usefulness improve together.

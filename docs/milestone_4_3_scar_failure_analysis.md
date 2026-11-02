# Milestone 4.3 SCAR failure analysis

## Scope and preservation

This analysis is a new experiment and does not overwrite M4.1 or M4.2. The
pre-work commit was `50d9b3afc5dc8a60d9fae7285f292c540aea488d`. The original
M4.1 prediction file remains unchanged (SHA-256
`5c7da1abaed3723d79cf89925e4c14c4e56857c0f4fcf08348279e31fa6d1535`).
M4.2 report hashes are recorded in
[`m43_experiment_manifest.json`](../reports/milestone4_3/m43_experiment_manifest.json).

All 30 document-distinct M4.2 development cases were inspected. The case-level
record is [`scar_failure_analysis_cases.json`](../reports/milestone4_3/scar_failure_analysis_cases.json).
These are research adjudications by inspection, not independent expert ratings.
`semantic_equivalence` remains `not_assessed`.

## Findings

| Category | Count | Interpretation |
|---|---:|---|
| Harmless lexical/grammatical change | 7 | The candidate appeared safe, but this is not proof of quality. |
| Valid improvement rejected conservatively | 8 | Structural protection or a cue mismatch prevented a potentially useful draft. |
| Genuine scientific-claim alteration | 12 | The candidate added, removed, strengthened, or weakened information. |
| Dangerous structural omission | 2 | Protected facts or claim-bearing text were dropped. |
| Total | 30 | Fixed development sample only. |

The current automatic decisions were 6 accepted for author review, 17
structural rejections, and 7 claim-cue rejections. The manual inspection shows
why acceptance is not a quality label and rejection is not always a bad-output
label.

## Representative cases

1. The revision changing “may improve” to “will improve” was correctly rejected
   as a modality change.
2. The revision changing `$5.15 per hour` to `$7.25 per hour` was correctly
   blocked by numeric protection; this is a genuine factual alteration.
3. The revision changing “not only protect” to “protect” removed a limitation
   and was correctly treated as a meaning risk.
4. The `between` to `from ... to` rewrite was plausibly equivalent, but the
   lexical quantification check rejected it. This is a false rejection candidate.
5. A candidate that added “downsampling” and a “deep transformer architecture”
   introduced unsupported technical claims despite fluent wording.
6. Several candidates were useful grammar or coherence edits but omitted
   protected numbers, acronyms, or number words. The fail-closed structural
   gate appropriately refused to create a patch, but a future system should
   preserve the candidate for reviewer comparison rather than silently discard
   the diagnostic.

## Calibration implication

The development set is too small and its IteraTeR labels are not editing
necessity labels. It cannot estimate gate precision or recall. The appropriate
next step is the 100-row reviewer-empty pilot manifest in
[`milestone4_3_pilot.jsonl`](../data/annotations/revision_necessity/milestone4_3_pilot.jsonl),
with independent reviewers and abstention allowed. No revised acceptance
threshold is justified from these 30 cases.

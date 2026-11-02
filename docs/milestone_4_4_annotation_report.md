# Milestone 4.4 annotation report

## Infrastructure status

The reviewer packet contains 130 items: 30 diagnostic comparison items and 100
new necessity-annotation items. The packet is immutable, versioned by SHA-256,
and isolated under `experiments/milestone4_4/`. The reviewer-empty annotation
file is `reviewer_annotations.jsonl`.

The 30 comparison items expose original, full-model, accepted-SCAR, and human
reference candidates only where the frozen source artifact contains them.
Rejected SCAR candidates remain represented by their absence rather than being
silently treated as an output. The 100 new items are necessity-only because no
new generation was permitted in M4.4.

## Empirical status

Qualified independent reviewers were not available during this run. Therefore:

- annotation count is zero;
- no preference, agreement, false-acceptance, or false-rejection result is
  reported;
- no simulated reviewer response has been created;
- semantic improvement and preservation remain unvalidated.

The API supports independent annotation import through
`POST /api/v1/review/annotations` and status/export through the review status
endpoint.

# No-edit annotation protocol

## Purpose

The M4.2 development labels describe observed revision intentions, not whether
an edit is necessary. M4.3 creates a 100-example pilot manifest with all
annotation fields empty. It must not be treated as labelled training data until
qualified reviewers complete it.

## Sampling and separation

Rows are sampled with seed 43 from the document-grouped development export.
The source record and document identifiers are retained for audit. No M4.1
test row is used for annotation-driven tuning. The manifest is
[`milestone4_3_pilot.jsonl`](../data/annotations/revision_necessity/milestone4_3_pilot.jsonl).

## Reviewer fields

For each passage, reviewers independently record:

- editing necessity: `no_edit`, `edit_needed`, `uncertain`;
- proposed intention: grammar, clarity, redundancy, technical concern,
  coherence, or other;
- reasoning in free text;
- confidence: low, medium, or high;
- reviewer identifier and disagreement status.

Reviewers must use the supplied context, section information, and technical
discipline. They must not infer necessity from whether an automatic model
changed the text. “Uncertain” is a valid outcome.

## Analysis plan

After two or more qualified reviewers complete the pilot, report raw agreement,
Cohen's kappa for two reviewers or Krippendorff's alpha for more, category
counts, confidence-stratified disagreement, and adjudication notes. Report
no-edit precision/recall only after an adjudicated reference is defined.
The pilot is exploratory and cannot establish statistical certainty.

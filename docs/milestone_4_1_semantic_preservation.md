# Milestone 4.1 semantic preservation

## What is checked

Each neural output is retained next to its source and human-edited reference in the local benchmark JSONL. ATEval checks:

- Exact ordered numeric-expression sequences, including values and common units.
- Exact ordered citation-like spans recognized by its citation patterns.
- Exact ordered protected structural spans recognized by the LaTeX/span validator.
- Whether the model returned no change, and whether it edited a reference no-op.
- Whether a supplied protected term or citation is still present for UI-originated proposals.

The benchmark manifest and exact model checksum are retained with the result so the same proposals can be reviewed without regenerating them. Neural proposals do not overwrite source files. The UI preview provides accept/reject decisions and the review audit records the selected passage, candidate, model identity, preservation findings and decision.

## What is not established

These checks do **not** prove semantic equivalence. They do not establish that a claim, qualifier, negation, modality, cause/effect relation, evidence attribution, limitation, result interpretation, or terminology meaning was preserved. The number/citation recognizers are pattern-based and may miss unusual notation or misrecognize prose. Protected-span identity cannot detect a fluent but technically wrong substitution outside a protected span. XtraGPT's own response rationale is not independent evidence.

The held-out references are a single revision path, not a uniquely correct target. Automatic similarity metrics cannot decide if a different revision is faithful or clearer. No human semantic evaluator has scored the complete test set yet. The output JSON therefore labels semantic equivalence `not_assessed` and requires author review even when every structural check passes.

## Observed risk example

Source: “The proposed method improves model performance by 12% on the held-out dataset.”

One XtraGPT smoke output: “The proposed method demonstrates a significant improvement of 12% in model performance when evaluated on the held-out dataset. This enhancement is specifically validated against a conventional baseline, indicating that our approach not only enhances accuracy but also provides actionable insights for future research.”

The numeric string `12%` survived. The output nevertheless added “significant,” recast generic “performance” as “accuracy,” and asserted actionable insights for future research without source evidence. The preservation check passed the protected-span sequence. This demonstrates why an exact number check is not semantic validation. A second output kept the numeric claim and scope more closely, but remains an unreviewed proposal.

## Safety behavior and next evaluation

ATEval marks every proposal as review-required and never auto-applies a neural change. If the output is malformed or a protected span is changed, the warning is shown rather than claiming equivalence. To extend this work, reviewers should annotate claim-level before/after relations, qualifiers and modality, causal links, citations/evidence, terminology, numbers/units, and limitations. Disagreements should be adjudicated and reported with document-clustered uncertainty. Critical semantic changes must be tracked separately from ordinary style preference.

No detector score is computed or used to tune these checks.

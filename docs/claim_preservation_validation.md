# Claim-preservation validation

## Objective

SCAR's original `compare_claim_cues` recognises lexical families for negation,
modality, quantification, causality, and claim strength. It is a useful
fail-closed warning, not a proposition or semantic-equivalence evaluator.
M4.3 therefore adds a secondary diagnostic in
[`claim_validation.py`](../ateval/revisions/claim_validation.py).

## Proposition-level pilot

The pilot covers may/will, could/does, suggests/demonstrates,
correlation/causation, significance, approximate/exact quantities,
at-least/at-most, polarity, necessary/sufficient conditions, generalisation,
and limitation removal. Results are in
[`claim_preservation_validation.json`](../reports/milestone4_3/claim_preservation_validation.json).

The diagnostic:

- rejects when quantitative expressions differ;
- abstains for cue or proposition-structure differences that require discourse
  or domain knowledge;
- reports no diagnostic difference only when configured cues, quantities, and
  clause count are unchanged.

This is deliberately conservative. “No diagnostic difference” is not a claim
that the proposition is preserved. Human review remains mandatory.

## Observed limitations

Lexical families cannot reliably distinguish harmless paraphrase from changed
scope, causal attribution, evidence strength, or qualification. For example,
“between” and “from ... to” can express the same range, while removing “only”
can weaken a restriction. Negation can be expressed syntactically without a
negation keyword. Domain terminology and anaphora also require context.

The revised diagnostic is not yet wired as a replacement for SCAR's existing
gate. The M4.3 evidence does not justify weakening the existing fail-closed
rules. A future change should be made only after proposition-level expert
annotations and safety tests.

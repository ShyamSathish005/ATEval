# Blind human evaluation protocol

## Status

The evaluation packet and protocol are prepared, but qualified human ratings
were not available during this implementation. No human judgments are
fabricated and no model is described as preferred.

## Design

Use the fixed 30 M4.2 development cases only for the initial pilot. Each item
contains the original passage and four candidates where available: identity,
full XtraGPT, SCAR-approved revision, and the human reference revision.
Candidate labels are pseudonyms and are independently randomised per item.
Presentation order must be counterbalanced so each candidate occupies each
position approximately equally.

Reviewers should rate grammar, academic clarity, naturalness, technical
accuracy, meaning preservation, editing necessity, and overall acceptability.
They may choose original preferred, candidate A preferred, candidate B
preferred, equally good, or neither acceptable; a forced winner is not allowed.
Each rating includes confidence and an optional disagreement comment.

## Meaning comprehension

For each scientific passage, add claim-specific questions about findings,
quantities, causal relationships, qualifications, limitations, conditions, and
conclusions. Questions must be answerable from the original passage and scored
against the reviewer response, not against lexical overlap. This follows the
reading-comprehension motivation of Agrawal and Carpuat (2024):
<https://aclanthology.org/2024.tacl-1.24/>.

Human answers are the final authority. An automated question-answering model,
if used as a secondary exploratory signal, must be labelled as such.

## Analysis

Report per-dimension distributions, paired preferences, confidence intervals
where sample size permits, position effects, reviewer agreement, disagreements,
and examples of technical or meaning failures. Keep all semantic conclusions
qualified; protected-span success does not establish meaning preservation.

# Revision edit-intention taxonomy

## Purpose

This is an operational label set for classifying observed edits and routing review suggestions. It does not encode a universal human-writing profile or imply that an edit is good. Preserve the dataset's original label alongside any mapped label. A changed scientific claim is a risk class, not a transformation objective.

## ATEval review taxonomy

| Canonical intent | Meaning for annotation | Example boundary |
|---|---|---|
| `grammar_correction` | Grammar, spelling, punctuation, or typo repair without intended claim change | A clear typo; if changing a technical token, flag terminology risk |
| `clarity_improvement` | Make an existing explanation easier to understand while retaining its proposition | Clarify an antecedent; do not infer omitted evidence |
| `concision` | Remove unnecessary wording without dropping scope, qualification, or emphasis | Shorten a phrase only when its relation is preserved |
| `redundancy_removal` | Remove repeated information | Keep repetition that serves a defined rhetorical purpose |
| `vocabulary_refinement` | Improve word choice or register while retaining technical meaning | Domain terms require author confirmation |
| `sentence_restructuring` | Reorder clauses or split/merge a sentence | Preserve negation, modality, causality, and attribution |
| `explanation_improvement` | Add or clarify explanatory connection | Any added factual content requires the author |
| `argument_clarification` | Make a claim/evidence/warrant relationship explicit | No new evidence or stronger claim is generated |
| `cohesion_improvement` | Improve references/transitions between adjacent units | A connective cannot invent a causal or contrast relation |
| `paragraph_restructuring` | Reorder, split, or merge paragraph material | High-risk; context and author review required |
| `technical_precision` | Refine a technical expression or disambiguate a term | Exact discipline-specific meaning must be verified |
| `citation_correction` | Repair citation placement/format or a verifiable reference issue | Never fabricate sources or bibliographic facts |
| `meaning_changed` | The revision changes or adds/removes substantive content | Flag for explicit author review; do not optimize toward it |
| `formatting` | Layout or markup-only change | Preserve equations, references, and LaTeX structure |
| `author_style` | An author-authorized preference or style adjustment | Within-writer preference only; never generic “humanization” |
| `other` | Valid edit outside current categories | Retain raw label and invite adjudication |
| `no_change` | Reviewer judges no edit necessary | An explicit valid outcome, not a model failure |

## Dataset crosswalk

The implemented crosswalk is in `ateval/revisions/taxonomy.py`. IteraTeR `FLUENCY` maps to grammar correction; `CLARITY` to clarity improvement; `COHERENCE` to cohesion improvement; `STYLE` to author style; `MEANING-CHANGED` to meaning changed; and `OTHER` to other. arXivEdits grammar/typo, simplification, style, more accurate/specific, content update, and format labels map respectively to grammar correction, concision, author style, technical precision, meaning changed, and formatting. Raw labels remain on the record. Where the source class has broader or ambiguous scope, this mapping is a pragmatic experimental crosswalk, not semantic equivalence.

Unrecognized labels return no canonical label. Additions to the crosswalk require documented examples and dual review. Multi-intent records preserve all mapped labels, but the current Naive Bayes baseline trains on the first canonical label only; benchmark results must state this limitation or use a multi-label model in a later experiment.

## Annotation and adjudication

Annotators receive source and revised text plus surrounding paragraph/section context, but no system identity. They record (a) one or more edit intentions, (b) whether a factual or claim-level change occurred, (c) confidence, and (d) whether the source text required any change. For safety review, separately mark claim scope, certainty/modality, negation, causal direction, evidence attribution, numbers and units, equations, terminology, citations, and limitations. “Meaning changed” is not synonymous with “incorrect”; the reviewer judges change, then separately judges correctness and author intent.

Use two independent academic reviewers and adjudicate disagreements with a third. Report raw labels, agreement by category, and abstentions; do not collapse weakly agreed labels into apparently certain ground truth. For multi-annotator IteraTeR rows, store the raw human votes where available and derive majority confidence as the largest vote share. This agreement share is not a calibrated probability.

# Semantic preservation methodology

## Principle

Text similarity, readability gain, and semantic equivalence are different constructs. An academic editor must preserve the author's proposition and evidence unless an author explicitly makes a content change. Even strong reading-comprehension evaluation has found substantial meaning loss in simplification output; one evaluated system left 14% of questions unanswerable under the reported setting. [Agrawal & Carpuat (2024)](https://aclanthology.org/2024.tacl-1.24/). No automatic validator can certify meaning equivalence for all disciplines and contexts.

## Protected content and invariants

Before a proposal is eligible, preserve and compare:

- mathematical expressions, delimiters, environments, and equation labels;
- citation commands, citation keys, reference commands, and bibliography entries;
- numerical values, signs, ranges, units, percentages, dates, and identifiers;
- technical terminology, named entities, abbreviations, and author-designated locked phrases;
- negation, quantifiers, modality, hedging, causal/contrast relations, attribution, and limitation statements;
- source ordering for citations/references and document markup that the extractor recognizes.

Exact protection is appropriate for numbers, citation keys, equations, and locked terms. Claim strength, causality, evidence support, and discourse scope require contextual human assessment; simple token checks do not validate them.

## Validation tiers

1. **Span integrity:** retain original, revised, and offsets; verify every expected locked span and citation/equation sequence. If offsets are stale, source text differs, or a protected interval is touched, abstain.
2. **Structured invariants:** compare numbers+units, equation blocks, citation/reference keys, named entities, terminology, negation/modality cues, and claim/limitation cues. These are alarms, not proofs.
3. **Semantic assistance:** optional local entailment or question-answering models may flag candidate contradictions/omissions. Record model/version and uncertainty. Never turn an entailment score into automatic approval; model failure and domain shift are expected.
4. **Author review:** show the before/after text and paragraph context; make accept/reject explicit. Any uncertainty involving findings, scope, evidence, limitations, causal claims, or technical terms must be escalated to the author.
5. **Audit:** write a complete reviewable change log keyed to the source hash, with source span, replacement, intent, risk, author decision, and application status. Do not store full manuscript content in telemetry.

## Current implementation

`ateval/writing/semantic.py` implements only exact protected-span sequence checking and explicitly returns `semantic_equivalence: not_assessed`. `ateval/writing/latex.py` protects recognized LaTeX/math/citation/reference and other spans. `ateval/writing/editing.py` rejects stale/overlapping source spans and checks exact source text before applying accepted edits. Current candidate suggestions avoid protected spans. The front end retains decisions and applies accepted text only to a local draft. This is conservative integrity plumbing, not an automatic semantic model.

## Uncertain transformations and abstention

Abstain and ask for author review when a candidate:

- touches or changes a number, unit, equation, citation, reference, named entity, or locked technical term;
- changes negation, quantifier, tense/aspect, modality, hedge, attribution, causal direction, comparison scope, or limitation;
- adds factual content, strengthens a result, removes uncertainty, changes evidence linkage, or alters paragraph argument order;
- depends on an ambiguous pronoun, section-specific convention, or discipline-specific terminology;
- fails exact offsets, changes protected-token order, or produces conflicting validator checks.

`meaning_changed` remains an annotation class and safety escalation, never a reward for the editor.

## Evaluation of preservation

Use blinded expert ratings on separate axes: proposition/claim preservation; strength and scope; numeric/unit integrity; equation integrity; citation/reference integrity; technical-term integrity; evidence attribution; causal/contrast relation; and limitations. For a subset, write document-grounded questions before editing and measure whether answers remain supported after editing. Measure false alarms and missed errors separately; adjudicate disagreements. Report critical-error rate and confidence intervals by intent, discipline, and edit-risk level. Readability gains cannot compensate for a critical meaning or citation failure.

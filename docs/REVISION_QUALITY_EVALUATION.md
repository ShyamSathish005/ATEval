# Revision quality evaluation

M6 evaluates the humanizer as a writing-improvement and preservation workflow,
not as an authorship or detector-evasion system.

## Automated evaluation dimensions

Synthetic manuscripts should include identity/no-op passages and passages with
equations, citations, numbers, technical identifiers, tables, figures, and
LaTeX environments. Every candidate is evaluated for:

- exact numerical, citation, terminology, and protected-span preservation;
- claim-cue and proposition-count diagnostics;
- source-map validity and round-trip structural preservation;
- whether the proposal was necessary or appropriately abstained;
- whether accepted patches are non-overlapping and exportable;
- reduction of unnecessary changes compared with the phrase-rule baseline.

These checks are safety gates and diagnostics. They do not establish semantic
equivalence or human preference. BLEU, ROUGE, lexical diversity, and sentence
variation are not quality objectives.

## Reproducible checks

```bash
python -m pytest -q tests/test_manuscript_analysis.py tests/test_scar.py
python -m pytest -q tests/test_writing.py tests/test_api.py
cd frontend && npm run build
```

Expert review infrastructure remains a future step; no human-review result is
reported until reviewers complete a preregistered evaluation.

## M4.1 failure checks

The M6 fixtures and manuscript tests target excessive rewriting, numeric and
citation loss, structural damage, and edits to already-good prose. SCAR
rejects protected-span changes and claim-cue changes, and supports explicit
`NO_CHANGE` abstention. Generated candidates remain pending author review.

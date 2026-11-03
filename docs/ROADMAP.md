# Roadmap

This roadmap describes research direction, not promised product capability.

## Current foundation

- Local manuscript ingestion, source mapping, analysis, and review-first UI.
- Reproducible revision-intention experiments and SCAR protection gates.
- Blinded human-evaluation packet and annotation infrastructure.
- CI across Python 3.11, 3.12, and 3.13 with frontend and Docker image checks.

## Next research gates

1. Complete qualified, independent human annotation and agreement analysis.
2. Measure false acceptance and false rejection without tuning on the held-out
   evaluation set.
3. Improve context-aware preservation checks only when supported by annotations
   and regression tests.
4. Reassess model adoption, smaller-model fine-tuning, or a new architecture
   from the evidence rather than a predetermined outcome.

## Explicitly not a goal

ATEval will not optimize against AI-detector scores, promise undetectable
writing, or turn experimental signals into authorship or misconduct decisions.

# Research & evaluation

ATEval is a research platform, not a claim that automated rewriting improves
scholarly writing. Its central question is how revision intent, technical
preservation, selective editing, abstention, and author review can be studied
reproducibly.

## Research threads

- **Human revision modelling:** IteraTeR-HUMAN ingestion, document-grouped
  splits, intent baselines, and held-out generation comparisons.
- **Meaning preservation:** typed protection for numbers, citations, LaTeX,
  terminology, and conservative claim-cue validation.
- **Selective revision:** SCAR proposes only under explicit author intent and
  rejects or escalates when evidence is insufficient.
- **Human evidence:** M4.4 supplies blinded packet generation and annotation
  infrastructure. Qualified reviewer outcomes are not yet completed.

## How to interpret results

BLEU, ROUGE, edit distance, change rate, classifier scores, and detector
signals are diagnostic measurements. They are not proof of human writing
quality, semantic equivalence, or authorship. Read the [methodology](research_methodology.md),
[benchmark report](revision_benchmark_report.md), [SCAR specification](scar_algorithm_specification.md),
and [failure analyses](milestone_4_3_results.md) together.

Every reproducible run should record the dataset manifest and hash, source
document grouping, checkpoint and licence, prompt/decoding configuration,
hardware, output hash, exclusions, and limitations.

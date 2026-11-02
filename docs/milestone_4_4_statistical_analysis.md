# Milestone 4.4 statistical analysis

The preregistered analysis is implemented in
[`analyze_milestone4_4.py`](../scripts/analyze_milestone4_4.py) and writes
[`statistical_analysis.json`](../reports/milestone4_4/statistical_analysis.json).

Planned analyses include:

- ordinal weighted Cohen's kappa for two-reviewer tasks;
- Krippendorff's alpha for incomplete multi-reviewer ratings, using a validated
  implementation when real multi-reviewer data are imported;
- candidate preference and assessment proportions;
- item- and source-document-clustered bootstrap confidence intervals;
- technical-error frequencies and disagreement analysis;
- no-edit accuracy, false acceptance, and false rejection after adjudication.

The current output is explicitly `pending_human_annotations`; it contains no
simulated observations and no confidence claims.

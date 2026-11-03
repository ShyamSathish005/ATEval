# Alpha limitations

ATEval is an experimental alpha. Human review is required.

- Real-model generation is not launch-ready until the local-model smoke test
  passes on a declared configuration.
- Automated preservation checks are conservative diagnostics, not semantic
  equivalence.
- Writing quality and coherence have not been established by completed expert
  evaluations.
- LaTeX spans crossing markup may be read-only; PDF cannot be written back.
- DOCX support is optional and limited to exact paragraph/run mappings.
- Browser-session undo history is not durable and does not survive refresh.
- The AI-writing evaluator is a weak research preview (AUROC 0.5541 and human
  FPR 0.2467 in the documented TXD-22 evaluation), not a validated detector.
- Windows, Linux, and Docker require separate environment validation.

Do not use ATEval to make authorship, misconduct, academic-integrity, or
detector-evasion decisions.

# Alpha limitations

ATEval is an experimental alpha. Human review is required.

- The verified real-model configuration is macOS + loopback Ollama +
  `ateval-xtragpt-1_5b-q8_0`; generation remains a proposal requiring author
  review.
- Automated preservation checks are conservative diagnostics, not semantic
  equivalence.
- Writing quality and coherence have not been established by completed expert
  evaluations.
- LaTeX spans crossing markup may be read-only; PDF cannot be written back.
- DOCX support is optional and limited to exact paragraph/run mappings.
- Browser-session undo history is not durable and does not survive refresh.
- The AI-writing evaluator is a weak research preview (AUROC 0.5541 and human
  FPR 0.2467 in the documented TXD-22 evaluation), not a validated detector.
- Windows, Linux, and Docker Compose are unverified and unsupported for this
  alpha.

Do not use ATEval to make authorship, misconduct, academic-integrity, or
detector-evasion decisions.

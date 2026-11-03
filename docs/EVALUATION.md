# Evaluation

ATEval uses layered evaluation rather than a single writing score.

| Layer | What it measures | Current status |
|---|---|---|
| Regression tests | Parser, API, protection, and gate behavior | Automated and run in CI |
| Structural preservation | Numbers, citations, LaTeX, protected terms, source maps | Automated safety checks |
| Revision experiments | Intent classification and local generation comparisons | Exploratory; reports are frozen |
| AI-writing evaluator | Stylometric feature signal and passage localisation | Executable baseline; uncalibrated, no detector benchmark |
| Human evaluation | Grammar, clarity, necessity, technical accuracy, and meaning | Infrastructure exists; qualified annotations pending |

The M4.1–M4.4 reports preserve negative findings and explicitly distinguish
rejected candidates from objectively poor writing. No automated metric is used
as an AI-detector optimization target. See the [human evaluation protocol](human_evaluation_protocol.md),
[M4.4 results](milestone_4_4_results.md), and [release limitations](known_limitations.md).

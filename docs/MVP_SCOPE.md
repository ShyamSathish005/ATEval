# ATEval MVP scope

ATEval is a local-first Academic Humanizer for computer-science and
engineering researchers working with TXT, LaTeX, and LaTeX project ZIP files.
It maps editable prose to source locations, proposes selective contextual
revisions, protects technical content, and requires author approval before
export.

## In scope

- Local TXT, TEX, and LaTeX ZIP import.
- Section and passage selection.
- Grammar, clarity, expression, structure, coherence, concision, and
  author-selected revision objectives.
- Optional local Ollama generation using a user-installed model.
- SCAR validation, abstention, side-by-side review, manual edits, undo, and
  source-preserving export.
- Synthetic demonstration and deterministic preservation tests.

DOCX is optional and PDF is read-only. The AI-writing evaluator remains a
separate research preview and does not block the humanizer.

## Out of scope

ATEval does not claim semantic equivalence, guaranteed writing quality,
authorship detection, detector evasion, cloud confidentiality, or automatic
large-model downloads. Every generated change requires human review.

## Launch status

The product is an experimental alpha. The local model launch gate is separate
from deterministic CI and is not passed until a real supported Ollama model
has completed the documented smoke test.

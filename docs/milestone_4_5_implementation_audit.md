# M4.5 implementation audit

## Existing components inspected

| Component | Current behavior | M4.5 implication |
|---|---|---|
| Detector registry (`ateval/registry.py`) | Perplexity, log-rank, entropy, stylometric, DetectGPT, Fast-DetectGPT, Binoculars, KGW, and SynthID are all `planned`; none is executable. Experiment run endpoint returns HTTP 409. | Do not produce detector scores or fabricated passage flags. The report must show methods as unavailable and analyzed passages as unanalysed. |
| Writing analysis (`ateval/writing/analysis.py`) | Computes descriptive lexical, sentence, paragraph, structure, claim-cue, and optional spaCy diagnostics; rule-based suggestions. It explicitly says these features do not identify authorship. | Reuse as academic-writing diagnostics, separate from AI-writing signals. |
| Document ingestion (`ateval/writing/documents.py`) | Read-only `.txt`/`.tex`, `.docx` text projection, and reliable text-layer `.pdf`; 25 MiB cap. DOCX/PDF do not carry writable source mappings. | Extend with project-aware LaTeX import; preserve DOCX structure for mapped edits; keep PDF read-only. |
| LaTeX (`ateval/writing/latex.py`, UI LaTeX page) | Protected span regex and a browser-local include/reference/figure inspection view; no root-file resolution or server-side project bundle analysis. | Add safe ZIP traversal, root detection, recursive includes, source-range mapping, and explicit unsupported-element reporting. |
| SCAR (`ateval/revisions/scar.py`) | Explicit intention gate, target offsets, local XtraGPT, typed sentinel validation, claim-cue checks, author-review-only decisions; semantic equivalence is not assessed. | Reuse per passage; do not feed detector scores into planning or generation. |
| XtraGPT adapter | Local Ollama loopback, no automatic model downloads, raw output telemetry and a generation cap. | Revisions stay local and can fail when the model is unavailable or times out. |
| Current writing UI (`frontend/src/App.tsx`) | Academic Quality page can upload `.txt/.tex/.docx/.pdf`, analyze text and accept phrase or one-sentence SCAR proposals into an in-browser draft. It exports `.txt` and an audit; it does not provide a full-manuscript source-mapped review workspace. | Add Manuscript Intelligence as a separate navigation destination and retain existing pages. |
| Reports | Existing report list stores local metadata and human-review audits. No document-level detector report exists. | Generate a document-scoped analysis report with method status, coverage, exclusions, uncertainty, and limitations; do not insert detector scores that do not exist. |
| Tests | API, writing, LaTeX protection, SCAR, and workspace tests exist. | Extend for imports, source mapping, detector-unavailable behavior, edit decisions, and exports. |

## Known unsupported behavior before M4.5

- No AIDetect detector is implemented and tested; none has a model or tokenizer revision available.
- `.tex` ingestion returned raw source and did not resolve `\\input` or `\\include`; ZIP projects were unsupported.
- Sentence-level source mapping, selectable signal highlights, full-section/document editing, and method-disagreement reporting were absent.
- DOCX/PDF text is a projection. PDF is not writable; DOCX write-back requires a source-preserving document path.
- UI accepted phrase suggestions into browser state but could not export a reviewed source-format DOCX or complete LaTeX project archive.

## Safe M4.5 scope

The new workflow may provide descriptive academic-writing measures and source-mapped passage review. These are not AI authorship signals. Since all registered detectors are planned, the correct AI-signal state is “not analysed / no supported method,” not a green “human-written” label. Proposed edits remain per-change reviewable. Unsupported macros, source regions, binary elements, scanned or sparse PDF text, ambiguous LaTeX roots, broken source locations, generation failures, and model unavailability must be reported rather than silently repaired.

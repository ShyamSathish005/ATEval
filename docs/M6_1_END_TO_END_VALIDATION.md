# M6.1 end-to-end validation

## Scope

This validation traces the supported local workflow from upload through
source-preserving export. It does not evaluate detector performance and does
not claim semantic equivalence.

| Step | Implementation | Evidence |
|---|---|---|
| Upload | `ManuscriptPage` → `POST /api/v1/manuscripts/analyze` | `tests/test_api.py` |
| Parse and structure | `import_manuscript` and `analyze_manuscript` | `tests/test_manuscript_analysis.py` |
| Selection/objective | Passage checkboxes and objective selector in `ManuscriptPage` | frontend production build |
| Generation | `POST /api/v1/writing/revise` → `SCARRevisionEngine` → `XtraGPTOllamaGenerator` | `tests/test_api.py`, `tests/test_m61_humanizer_validation.py` |
| Validation/abstention | SCAR gate, protected spans, claim-cue checks | `tests/test_scar.py`, `tests/test_api.py` |
| Review | Side-by-side proposals, accept/reject/manual validation | `ManuscriptPage` |
| Undo | Browser-session proposal snapshots | `ManuscriptPage` |
| Export | `POST /api/v1/manuscripts/export` → source-mapped exporter | `tests/test_manuscript_analysis.py`, `tests/test_m61_humanizer_validation.py` |

Generation is not mocked in the production path. If Ollama or the configured
model is unavailable, the API returns an explicit `503`; deterministic tests
patch the adapter only to exercise error handling and CI-safe behavior.

## Validation results

```text
python3 -m pytest -q
104 passed, 2 skipped

cd frontend && npm run build
passed
```

M6.1 added deterministic checks for multiple approved ranges, untouched
paragraphs, LaTeX source preservation, invalid technical changes, empty model
responses, prompt shape, telemetry, and review-required model output.

## Real-model smoke test

The local Ollama endpoint was checked at `http://127.0.0.1:11434` during this
run and was unavailable. Therefore no real-model result is reported.

With Ollama and the locally imported model installed, run:

```bash
ollama serve
ollama list
ATEVAL_OLLAMA_MODEL=ateval-xtragpt-1_5b-q8_0 \
python -m pytest -q tests/test_api.py -k "local_model or scar_api"
```

The model must be available locally; ATEval does not download weights or send
manuscripts to remote providers. The adapter uses loopback HTTP, a bounded
2,048-token context, deterministic seed 17, low temperature, and a bounded
192-token response in the API path. Hardware placement and latency depend on
Ollama's CPU/Metal configuration and should be recorded with the smoke result.

## M4.1 comparison boundary

The frozen M4.1 experiment artifacts do not contain a directly runnable,
repository-local benchmark command that produces the current M6 proposal
metrics. M6.1 therefore does not fabricate a numerical before/after result.
The current automated comparison harness is preservation-oriented and reports
structural safety, no-op behavior, abstention, and unnecessary-edit guards.
Human preference and academic quality require a separate completed expert
review and are not inferred from these checks.

## Privacy and history findings

- Manuscript analysis does not persist full source text.
- Browser revision history retains proposal objects and decisions only for the
  current page session; it is lost on refresh or browser closure.
- The optional downloadable change audit is explicitly user-triggered and
  includes selected proposal text, source locations, decisions, and validation.
- TXT/TEX/ZIP/DOCX exports preserve source assets outside accepted ranges;
  PDF is read-only.
- Ollama access is loopback-only. No external model provider is used by this
  workflow.
- The repository does not claim that browser memory is durable audit storage.

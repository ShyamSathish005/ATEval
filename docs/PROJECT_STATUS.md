# Project Status

## Current Release Status
**RELEASED — v0.1.0-alpha.1 / EXPERIMENTAL**

ATEval is an experimental alpha and is not a stable or production release.

## Current Package Version
0.1.0a1

## Verified Configuration (macOS)

The only configuration that has been tested end-to-end with the local model is:

- **OS**: macOS (Apple Silicon; Apple M1 evidence)
- **Runtime**: Ollama with model `ateval-xtragpt-1_5b-q8_0` (user-managed; provenance limitations are documented in docs/MODEL_PROVENANCE.md)
- **Mode**: Loopback-only FastAPI on `127.0.0.1:8000`
- **Installer**: Shell installer (`launch.sh`)
- **Tested hardware**: Apple M1 MacBook Air, 8 GB unified memory

## Supported Operating Systems
- **macOS** — Verified locally: installer, launcher, API, and real-model smoke test
- **Linux** — Unverified: shell installer exists; no clean installation or lifecycle evidence in this repository
- **Windows** — CI smoke-tested with packaged assets; no independent clean-machine or real-model evidence
- **Docker** — Unverified in production: `compose.yaml` demonstrates loopback-only port publishing (`127.0.0.1:${ATEVAL_PORT:-8000}:8000`), but no production deployment test has been run

## Verified Installation Paths
- macOS: shell installer; local end-to-end evidence
- Linux: packaged install smoke test in CI
- Windows: packaged install smoke test in CI

## Verified Local Models
- `ateval-xtragpt-1_5b-q8_0` (default experimental model) — Provenance: unresolved (see docs/MODEL_PROVENANCE.md); model path is caller-provided via `ATEVAL_XTRAGPT_GGUF` env var or CLI `--model-file`
- No other models are verified

## Supported Document Formats
- LaTeX (.tex) — Read/write via parser and source maps
- LaTeX ZIP archives (.zip) — Supported through ingestion pipeline
- DOCX — Experimental: read-only import via `python-docx`; write/edit capabilities untested
- PDF — Read-only, experimental: text extraction via `PyMuPDF`; editing capabilities unavailable

## Experimental Features
- AI Authorship Detector (disabled by default; not wired into any API endpoint)
- Revision generation (requires explicit author review; `author_review_required=True` by default)
- Document analysis (experimental: parsing and analysis implemented, revision not guaranteed)
- Protected content validation (structural validator implemented; author must approve)

## Disabled Features
- AI Authorship Detector — OFF by default; no API endpoint exposed
- Revision generation UI — hidden by default; accessible only via `/api/v1/writing/audits` with explicit payload
- Automatic model download — requires manual setup; not included in pip install
- Public API endpoints — loopback-only; `PUBLIC_DEMO_MODE` is off by default; rate-limited when enabled

## Unsupported / Unverified Capabilities
- Docker Compose production deployment — image CI passes, but Compose lifecycle is unverified
- Advanced DOCX editing — not implemented; only import is supported
- PDF editing capabilities — not implemented; only read-only text extraction via PyMuPDF

## Security Review Status
- Independent M6.4 security review completed; the ZIP traversal finding was fixed and regression-tested
- SSRF protection: Ollama URL validated as loopback (`_loopback_ollama_url` in api.py); `compose.yaml` publishes `127.0.0.1:8000` only
- Host-header and DNS-rebinding protection: Host header validated against `API_HOSTS` set (`127.0.0.1`, `localhost`, `terminal.local`)
- Local API request protection: `MaxRequestBodyMiddleware` rejects oversized bodies; rate limiting on public demo mode
- Docker host-port publishing — loopback-only by default; `compose.yaml` publishes `127.0.0.1:${ATEVAL_PORT:-8000}:8000`
- Public API exposed only in development mode; `PUBLIC_DEMO_MODE` env var controls opt-in with rate limiting

## Human Evaluation Status
- Human evaluation protocol established
- Pilot evaluation protocol ready
- No human evaluation results yet available (external dependency)
- Unit testing coverage for core functionality

## Licensing Status
- MIT License for project-authored material
- Third-party licenses documented in MODEL_LICENSES.md and DATASET_LICENSES.md
- No unlicensed dependencies (all dependencies have declared licenses; see pyproject.toml)
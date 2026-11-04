# M6.6 Performance, Concurrency & Correctness Report

**Branch:** `feat/m6.6-security-reliability-remediation`  
**Base Commit:** `293e3c8` (`main`)

---

## BUG-02 — Dependency and Lockfile Consistency

### Findings & Resolution
- Verified that `pyproject.toml` (`version = "0.1.0a1"`) and `uv.lock` are synchronized (`uv lock --check --offline` resolves all 148 locked packages cleanly).
- Updated `Dockerfile` so container builds copy `uv.lock`, export locked requirements with hashes (`uv export --locked --no-dev --extra ui-server --extra writing-docs --no-emit-project --format requirements.txt`), and install with `pip install --no-cache-dir --require-hashes` followed by `pip install --no-cache-dir --no-deps .`.
- Updated `Dockerfile` to copy the freshly built frontend (`frontend/dist/client`) into both `./ateval/static` (prior to wheel installation) and `./frontend/dist/client` so packaged and workspace static paths stay identical.

### Verification
- `tests/test_foundation.py::FoundationTests::test_bug02_dependency_lockfile_and_dockerfile_consistency`

---

## BUG-03 — Blocking Async Handlers and SQLite Concurrency

### Findings & Resolution
1. **Event-Loop Offloading (`ateval/api.py`):**
   - `import_dataset`, `writing_ingest`, `manuscript_analyze`, `manuscript_export`, `run_experiment`, and `experiment_events` are `async def` handlers that previously ran synchronous CPU-bound parsing, ZIP/DOCX/PDF extraction, stylometric analysis, and SQLite I/O directly on the asyncio event loop.
   - Offloaded synchronous CPU and disk/DB work (`_finalize_dataset_import`, `extract_document`, `_analyze_manuscript_sync`, `_export_manuscript_sync`, `_execute_research_experiment_sync`, `_get_experiment_event_snapshot`) to Starlette's threadpool via `await run_in_threadpool(...)` while keeping `UploadFile` streaming size enforcement in the async handler.
2. **SQLite WAL & Busy-Timeout Configuration (`ateval/api.py`):**
   - `init_db()` now enables `PRAGMA journal_mode = WAL` and `PRAGMA synchronous = NORMAL` once during database initialization rather than per request.
   - `get_db()` opens a dedicated per-operation connection with `timeout = 15.0` seconds, `PRAGMA busy_timeout = 15000`, and `PRAGMA foreign_keys = ON`, committing on success and rolling back cleanly on exception before closing.
   - Added `@app.exception_handler(sqlite3.OperationalError)` to translate unhandled SQLite lock/busy timeouts into a predictable HTTP `503 Service Unavailable` (`{"detail": "Database is temporarily busy; retry shortly"}`) instead of an unhandled 500 traceback.

### Verification
- `tests/test_api.py::LocalApiTests::test_bug03_async_threadpool_and_sqlite_wal_concurrency`

---

## BUG-04 — Repeated Sentence Offset Disambiguation

### Findings & Resolution
1. **Canonical Offset Unit:**
   - Defined **Unicode code-point offsets** (`offset_unit: "unicode_code_points"`, matching Python `str` slice indices) as the canonical offset representation across the API and frontend.
2. **Backend Validation (`ateval/api.py`):**
   - Extended `RevisionProposalRequest` with optional `paragraph_id: str | None`, `target_start: int | None`, and `target_end: int | None`.
   - Added `_resolve_revision_target_offsets(paragraph, sentence, target_start, target_end)`:
     - When `target_start` or `target_end` is supplied: requires both, validates `0 <= target_start < target_end <= len(paragraph)`, and verifies `paragraph[target_start:target_end] == sentence` (rejecting out-of-bounds or stale offsets with HTTP `422`).
     - When offsets are omitted: scans `paragraph` for all occurrences of `sentence` (including overlapping substrings). If `0` occurrences exist, returns HTTP `422`. If `> 1` occurrences exist, refuses to guess and returns HTTP `409 Conflict` requiring explicit `target_start` and `target_end` code-point offsets.
   - `POST /api/v1/writing/revise` returns `paragraph_id`, `target_start`, `target_end`, and `offset_unit: "unicode_code_points"`.
3. **Frontend Code-Point Offset Resolution (`frontend/src/App.tsx`):**
   - Added `resolveCodePointOffsets()` to convert UTF-16 string indices into Unicode code-point offsets (`Array.from(paragraphContext.slice(0, utf16Index)).length`) and disambiguate repeated sentences within the same paragraph context by passage order.

### Verification
- `tests/test_api.py::LocalApiTests::test_bug04_repeated_sentence_offset_disambiguation_and_unicode_code_points`

---

## BUG-05 — Docker Dynamic `PORT` Handling

### Findings & Resolution
- Added `validate_port(value: str | int) -> int` in `ateval/cli.py` to validate TCP ports in `1..65535` and deferred `os.environ.get("PORT", "8000")` validation to the `api` subcommand (with graceful fallback in `doctor`) so invalid `PORT` values produce a clean CLI error (`exit code 2`) on `ateval api` without crashing non-server CLI commands (`ateval version`).
- Updated `Dockerfile` and `compose.yaml` `HEALTHCHECK` commands to read and validate `os.environ.get('PORT', '8000')` dynamically instead of hardcoding port `8000`.
- Hardened `render.yaml` with `ATEVAL_ENABLE_RESEARCH_EXPERIMENTS: "0"` and `ATEVAL_TRUSTED_PROXY_HOPS: "1"` alongside `ATEVAL_PUBLIC_DEMO: "1"`.

### Verification
- `tests/test_foundation.py::FoundationTests::test_bug05_dynamic_port_validation_host_binding_and_container_healthcheck`

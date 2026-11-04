# M6.6 Security Remediation Report

**Branch:** `feat/m6.6-security-reliability-remediation`  
**Base Commit:** `293e3c8` (`main`)

> **Important Note on Verification Scope:** All remediations below are covered by automated unit and API regression tests in `tests/`. Automated regression tests verify expected application behaviour against known attack vectors, but they do not substitute for an independent external penetration test or third-party security certification.

---

## SEC-01 — Forwarded IP Trust and Rate-Limit Memory Exhaustion

### Vulnerability Summary
1. `local_origin_guard` in `ateval/api.py` previously parsed `X-Forwarded-For` unconditionally when `PUBLIC_DEMO_MODE` was enabled and selected the leftmost comma-separated value (`forwarded.split(",")[0].strip()`), allowing any client to spoof arbitrary source IPs and bypass per-IP rate limits.
2. `_public_rate_counts` grew without an upper bound when attackers sent requests with unique spoofed `X-Forwarded-For` values.

### Remediation Implemented
- **Explicit Trusted-Proxy Topology (`ateval/api.py`):**
  - Added `TRUSTED_PROXY_NETWORKS` (configured via `ATEVAL_TRUSTED_PROXIES`, defaulting to loopback + RFC 1918 private networks) and `TRUSTED_PROXY_HOPS` (configured via `ATEVAL_TRUSTED_PROXY_HOPS`, defaulting to `1` when `RENDER=true` or `ATEVAL_TRUSTED_PROXIES` is set, and `0` otherwise).
  - `_resolve_client_ip(request)` ignores `X-Forwarded-For` unless `effective_hops > 0` **and** `request.client.host` is inside `TRUSTED_PROXY_NETWORKS`.
  - Every hop in `X-Forwarded-For` is parsed and validated via `ipaddress.ip_address`. Malformed IPs, empty segments, or oversized headers (`> 2048` chars or `> 32` hops) raise `ValueError` and return HTTP `400 Bad Request`.
  - Selects the hop `parsed_ips[max(0, len(parsed_ips) - effective_hops)]` from the right rather than trusting the leftmost attacker-controlled value.
- **Bounded LRU Rate-Limit Table (`ateval/api.py`):**
  - Replaced the unbounded `dict` with an `OrderedDict` protected by `_public_rate_lock` and capped at `PUBLIC_RATE_LIMIT_MAX_BUCKETS` (default `4096`).
  - `_check_public_rate_limit()` evicts expired minute windows first and then evicts the oldest LRU entries when at capacity.
- **Multi-Worker Limitation Documented:**
  - Process-local in-memory rate limiting applies per worker process. Multi-worker or distributed deployments must enforce rate limiting at the reverse proxy, edge WAF, or shared key-value store (e.g., Redis).

### Regression Tests
- `tests/test_api.py::LocalApiTests::test_sec01_forwarded_ip_trust_and_rate_limit_bounds`

---

## SEC-02 — ZIP Bomb and Decompression Exhaustion

### Vulnerability Summary
1. `_zip_files` in `ateval/manuscript_analysis/documents.py` relied on `ZipInfo.file_size` header metadata (which can be spoofed in malformed/crafted archives) and called `archive.read(info)` in a single unbounded allocation.
2. `_docx_projection` in `ateval/manuscript_analysis/documents.py` and `extract_document` in `ateval/writing/documents.py` passed raw DOCX bytes directly to `python-docx` without pre-validating the underlying ZIP container against XML/decompression bombs.

### Remediation Implemented
- **Bounded Streaming Decompression (`ateval/manuscript_analysis/documents.py`):**
  - Implemented `_read_bounded_zip()` which streams each entry via `archive.open(info, "r")` in `64 KiB` chunks and counts actual decompressed bytes.
  - Enforces hard bounds on:
    - Maximum entry count (`MAX_PROJECT_FILES = 2000` for LaTeX ZIPs; `MAX_DOCX_FILES = 500` for DOCX packages).
    - Maximum individual expanded file size (`25 MiB` for LaTeX ZIPs; `16 MiB` for DOCX XML entries).
    - Maximum aggregate expanded bytes (`100 MiB` for LaTeX ZIPs; `50 MiB` for DOCX packages).
    - Maximum compression ratio (`MAX_COMPRESSION_RATIO = 200.0` once an entry expands past `64 KiB`).
  - Rejects path traversal (`..`), leading slashes, backslashes, null bytes, Windows drive prefixes (`C:`), symlinks (`0o120000`), and normalized duplicate entry names.
- **Pre-Validation for DOCX Ingestion (`ateval/manuscript_analysis/documents.py`, `ateval/writing/documents.py`):**
  - Added `validate_docx_archive(content)` and invoked it before `Document(io.BytesIO(content))` in both manuscript analysis and writing ingestion.
- **Validated Export Bundle Reuse (`ateval/manuscript_analysis/exports.py`):**
  - Updated `export_reviewed_manuscript` to write from the already-validated `bundle.files` map rather than re-reading raw archive streams.

### Regression Tests
- `tests/test_manuscript_analysis.py::ManuscriptAnalysisTests::test_sec02_zip_and_docx_decompression_safety`

---

## SEC-03 — Export Header Injection and HTML Execution Risk

### Vulnerability Summary
1. `manuscript_export` in `ateval/api.py` interpolated `output_name` directly into `Content-Disposition: attachment; filename="{output_name}"`.
2. Printable HTML reports lacked an embedded restrictive Content-Security-Policy and `printReport` in `frontend/src/App.tsx` wrote report HTML into a same-origin `about:blank` popup (`window.open("")`).

### Remediation Implemented
- **RFC 6266 / RFC 5987 Filename Sanitization (`ateval/manuscript_analysis/exports.py`):**
  - Added `sanitize_export_filename()` and `build_content_disposition()` which strip CR/LF, quotes, path separators, semicolons, and Unicode control characters, producing both an ASCII fallback `filename="..."` and UTF-8 percent-encoded `filename*=UTF-8''...`.
- **Hardened Export Response Headers & Standalone HTML Export (`ateval/api.py`, `ateval/manuscript_analysis/exports.py`):**
  - Added `export_html_report()` with `html.escape(..., quote=True)` on all manuscript strings and an embedded `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; form-action 'none'; base-uri 'none'">`.
  - `POST /api/v1/manuscripts/export` sets `Content-Disposition` via `build_content_disposition()`, `X-Content-Type-Options: nosniff`, `Cache-Control: no-store`, and `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; img-src data:; sandbox`.
- **Frontend Download-Only Report Delivery (`frontend/src/App.tsx`):**
  - Replaced `window.open("")` in `printReport` with an attachment download (`export-report.html`) containing the restrictive CSP meta tag so exported HTML never executes in the application's origin.

### Regression Tests
- `tests/test_api.py::LocalApiTests::test_sec03_export_header_injection_unicode_and_html_safety`

---

## SEC-04 — Unsafe `joblib` Deserialization

### Vulnerability Summary
1. `ateval/revisions/classic_models.py`, `ateval/api.py`, `ateval/revisions/cli.py`, and `scripts/benchmark_distilbert_intent.py` used `joblib.load()`, which relies on Python's `pickle` deserializer and allows arbitrary code execution if a model file is modified or replaced.

### Remediation Implemented
- **Declarative JSON Model Format (`ateval/revisions/classic_models.py`):**
  - Replaced `joblib.dump` / `joblib.load` with `DeclarativeLinearModel`, `save_declarative_model()`, and `load_declarative_model()`.
  - Models are stored as UTF-8 JSON (`.model.json`, schema `ateval-declarative-linear-model-v1`) containing only validated vocabulary mappings, finite IDF arrays, finite linear coefficients/intercepts, and class labels.
  - `load_declarative_model()` explicitly rejects `.joblib` files, enforces path containment under `ALLOWED_MODEL_ROOT`, validates the metadata manifest (`ateval-revision-classifier-metadata-v2`), verifies the SHA-256 digest of the model bytes, and supports build-pinned digests (`PINNED_MODEL_DIGESTS` / `expected_sha256`) so an attacker who can rewrite both model and metadata files is still blocked when a pinned digest is configured.
  - Documented that file-hash verification checks on-disk integrity and is not a sandbox against malicious code already executing inside the Python process.

### Regression Tests
- `tests/test_api.py::LocalApiTests::test_sec04_declarative_model_integrity_and_deserialization_safety`
- `tests/test_api.py::LocalApiTests::test_learned_revision_intent_is_advisory_and_not_persisted`

---

## SEC-05 — Local CSRF and Origin Protection

### Vulnerability Summary
1. `API_HOSTS` in `ateval/api.py` and `allowedHosts` in `frontend/vite.config.mjs` included the unverified hostname `terminal.local`.
2. State-changing `/api/` requests without an `Origin` header were not checked against `Sec-Fetch-Site`, `Referer`, browser form content-types (`application/x-www-form-urlencoded`, `text/plain`), or per-launch token authentication.

### Remediation Implemented
- **Host & Origin Hardening (`ateval/api.py`, `frontend/vite.config.mjs`):**
  - Removed `terminal.local` from `API_HOSTS` and `frontend/vite.config.mjs`.
  - Added `_normalize_host_header()` to strictly parse host and port (`1..65535`), handle bracketed IPv6 (`[::1]`), and reject missing or malformed `Host` headers on `/api/` routes.
  - Added explicit Tauri desktop origins (`tauri://localhost`, `http://tauri.localhost`, `https://tauri.localhost`) to `DEFAULT_CORS_ORIGINS`.
- **Cross-Site Mutation & Per-Launch Token Guards (`ateval/api.py`):**
  - State-changing `/api/` requests (`POST`, `PUT`, `PATCH`, `DELETE`) reject `Sec-Fetch-Site: cross-site`, reject untrusted `Referer` origins, and reject simple HTML form `Content-Type` values (`application/x-www-form-urlencoded`, `text/plain`) with HTTP `415`.
  - Added cryptographically random per-launch `LAUNCH_TOKEN` (`ATEVAL_LAUNCH_TOKEN` or `secrets.token_urlsafe(32)`), constant-time `X-ATEval-Token` verification (`hmac.compare_digest`), and opt-in strict enforcement (`ATEVAL_REQUIRE_LAUNCH_TOKEN=1`, `ATEVAL_REQUIRE_ORIGIN_FOR_MUTATIONS=1`).

### Regression Tests
- `tests/test_api.py::LocalApiTests::test_sec05_origin_host_csrf_and_launch_token_protections`

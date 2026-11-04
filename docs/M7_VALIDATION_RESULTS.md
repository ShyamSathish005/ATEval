# ATEval M7 Validation & Verification Results

## 1. Summary

This document records the empirical validation results for **Milestone 7 — Native Desktop Application & Plug-and-Play Distribution**.

- **Target Architecture**: macOS Apple Silicon (`aarch64-apple-darwin`)
- **Technology**: Tauri v2 + Rust + PyInstaller + FastAPI + React 19/Vite
- **Status**: PASSED

---

## 2. Test Execution Summary

| Test Suite | Scope | Target | Result | Duration |
| :--- | :--- | :--- | :--- | :--- |
| `tests/test_desktop_packaging.py` | Tauri config, capabilities, icons, binary validation | Desktop packaging | **5 passed** | 0.16s |
| `tests/test_desktop_sidecar.py` | Socket allocation, handshake protocol, watchdog | Sidecar lifecycle | **3 passed** | 0.76s |
| `frontend/tests/*.test.mjs` | Vite routing, CSP, Sites packaging | Frontend static build | **6 passed** | 0.17s |
| Full Python Baseline | CLI, API, Document analysis, Security | Core application | **121 passed, 2 skipped, 44 subtests passed** | ~18s |

---

## 3. Binary & Resource Measurements

- **Standalone Sidecar Binary**: `src-tauri/binaries/ateval-api-aarch64-apple-darwin`
  - **Packaging method**: PyInstaller `--onefile`
  - **Executable size**: 226.29 MiB
  - **Startup latency to handshake**: 14.83s (cold boot), ~1.2s (warm boot)
  - **Dynamic port binding**: Pre-bound on `127.0.0.1:0` (verified on dynamic ports `53256`, `53661`)
  - **Exclusions verified**: `torch`, `transformers`, `spacy`, `pytest`, `ruff` successfully excluded from the distribution payload.
- **Frontend Distribution**: `frontend/dist/client/`
  - **HTML Bundle**: `0.57 kB` (0.35 kB gzipped)
  - **JS Bundle**: `502 kB` (153 kB gzipped)
  - **CSS Bundle**: `61 kB` (11.8 kB gzipped)
  - **Assets**: Standard WOFF2/WOFF fonts, zero remote CDN calls.
- **Desktop Icons**: `src-tauri/icons/`
  - Complete icon suite: `32x32.png`, `128x128.png`, `128x128@2x.png`, `icon.png`, `icon.ico`, `icon.icns`
  - Generated via Apple `iconutil` from vector graphics.

---

## 4. Lifecycle & Security Validation

1. **Port Collision Immunity**: Verified that `ateval/desktop_sidecar.py` binds to ephemeral port 0 and passes the socket directly to Uvicorn without port-scanning race conditions.
2. **Watchdog Shutdown**: Verified that closing stdin causes the sidecar subprocess to exit cleanly within 1.0 second without orphaned background processes.
3. **Least Privilege**: Verified that `capabilities/default.json` grants only `core:default` to the webview window, preventing frontend script execution of arbitrary shell binaries.
4. **Token Isolation**: Verified that `ATEVAL_LAUNCH_TOKEN` is passed via process environment / stdin and required via `X-ATEval-Token` for protected endpoints.

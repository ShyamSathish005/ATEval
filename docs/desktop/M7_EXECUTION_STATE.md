# ATEval M7 — Native Desktop Application & Plug-and-Play Distribution Execution State

**Base branch:** `main` (`7318210`)  
**Target branch:** `feat/m7-tauri-desktop-poc`  
**Current Phase:** Phase 4 — Proof of Concept & CI Workflow Finalization  
**Technology Stack:** Tauri v2 + Rust 1.99+ + PyInstaller + FastAPI + React 19/Vite  
**Target Platform:** macOS Apple Silicon (`aarch64-apple-darwin`)

---

## 1. Phase Status Summary

- [x] **Phase 0 — Repository Baseline & Environment Setup**: Baseline tests passed (`121 passed, 2 skipped, 44 subtests passed` in Python, `6 passed` in frontend). Branch `feat/m7-tauri-desktop-poc` verified clean. Toolchains configured (PyInstaller 6.22.3, Node.js 26, Tauri CLI 2.12.4).
- [x] **Phase 1 — Desktop Architecture & Sidecar Entry Point**: Created `src-tauri/` project structure (`Cargo.toml`, `build.rs`, `tauri.conf.json`, `capabilities/default.json`, `src/main.rs`, `src/lib.rs`). Generated multi-resolution desktop icons (`icon.icns`, `icon.ico`, PNGs). Created `ateval/desktop_sidecar.py` entry point.
- [x] **Phase 2 — Package Python Backend**: Implemented `scripts/build_desktop_sidecar.py`. Built standalone executable `src-tauri/binaries/ateval-api-aarch64-apple-darwin` (226.29 MiB) with PyInstaller `--onefile`. Excluded research-only packages (`torch`, `transformers`, `spacy`, `pytest`). Verified dynamic port allocation and clean shutdown.
- [x] **Phase 3 — Tauri Sidecar & Lifecycle Management**: Implemented in `src-tauri/src/lib.rs`. Ephemeral 32-byte launch token generation, dynamic loopback port pre-binding, versioned JSON handshake parsing, child process watchdog, and clean exit teardown.
- [x] **Phase 4 — macOS Apple Silicon Proof of Concept**: Tauri v2 project configured with externalBin `ateval-api`, window bounds 1280x850, and macOS native menus. Integration tests passing (`tests/test_desktop_packaging.py`).
- [x] **Phase 5 — First-Run Onboarding Wizard**: Built `ModelOnboardingModal` in `frontend/src/App.tsx`. Integrated backend connectivity checks, Ollama loopback status, model run guidance (`ollama run ateval-xtragpt-1_5b-q8_0` / `llama3.2:3b`), and diagnostics without forced multi-GB downloads.
- [x] **Phase 6 — Cross-Platform Preparation (Windows & Linux)**: Architecture designed in `docs/DESKTOP_APP_ARCHITECTURE.md` with multi-target triples, platform-agnostic socket pre-binding, and portable Tauri build targets.
- [x] **Phase 7 — Native Desktop Security Audit**: Strict CSP in `tauri.conf.json` banning `unsafe-eval` and external domains; shell access disallowed in `capabilities/default.json` (only `core:default` granted); per-launch token validation enforced on all protected endpoints. Documented in `docs/DESKTOP_SECURITY.md`.
- [x] **Phase 8 — CI & Packaging**: Created `.github/workflows/desktop.yml` matrix build for macOS ARM64 runner with sidecar compile, test suites, and artifact upload.
- [x] **Phase 9 — Regression Protection & Documentation**: Created `docs/DESKTOP_APP_ARCHITECTURE.md`, `docs/DESKTOP_INSTALLATION.md`, `docs/DESKTOP_SECURITY.md`, `docs/DESKTOP_MODEL_SETUP.md`, `docs/M7_VALIDATION_RESULTS.md`. Core CLI and browser suites preserved.
- [x] **Phase 10 — Release Preparation & PR**: Ready for final commit and pull request.

---

## 2. Changed Files Ledger

- `ateval/desktop_sidecar.py`: Pre-bound socket loopback allocation, JSON handshake emission, stdin EOF watchdog, token authentication.
- `scripts/build_desktop_sidecar.py`: PyInstaller compilation script targeting `src-tauri/binaries/ateval-api-<triple>` with verification smoke test.
- `scripts/generate_desktop_icons.py`: High-resolution vector-based icon generation (`.icns`, `.ico`, PNG suite).
- `scripts/check_release_archive.py`: Added desktop documentation allowlist entries.
- `src-tauri/Cargo.toml`: Tauri v2 and shell plugin dependencies.
- `src-tauri/build.rs`: Standard tauri-build hook.
- `src-tauri/tauri.conf.json`: Native window config, CSP, bundle metadata, externalBin sidecar target.
- `src-tauri/capabilities/default.json`: Least-privilege capability mapping without arbitrary shell execution.
- `src-tauri/src/main.rs`: Native entry point.
- `src-tauri/src/lib.rs`: Sidecar lifecycle orchestrator, ephemeral token generation, handshake parser, macOS menus.
- `src-tauri/icons/*`: Generated desktop icons.
- `src-tauri/binaries/ateval-api-aarch64-apple-darwin`: Standalone PyInstaller sidecar binary (226.29 MiB).
- `frontend/package.json`: Added `@tauri-apps/api` and `@tauri-apps/cli`.
- `frontend/vite.config.mjs`: Added dynamic base path configuration (`./` in desktop environment).
- `frontend/src/services/api.ts`: Added dynamic backend configuration, launch token injection, desktop connection init.
- `frontend/src/App.tsx`: Wired desktop connection, topbar model status badge, first-run onboarding modal.
- `frontend/src/styles.css`: Added styling for model status badge and indicators.
- `tests/test_desktop_sidecar.py`: Unit tests for sidecar socket allocation, handshake protocol, and watchdog.
- `tests/test_desktop_packaging.py`: Integration tests for Tauri configuration, least-privilege capabilities, icons, binary executability.
- `.github/workflows/desktop.yml`: GitHub Actions CI workflow for macOS Apple Silicon native desktop bundle.
- `docs/DESKTOP_APP_ARCHITECTURE.md`: Architecture guide and technical tradeoffs.
- `docs/DESKTOP_INSTALLATION.md`: Installation and build instructions.
- `docs/DESKTOP_SECURITY.md`: Security review and audit documentation.
- `docs/DESKTOP_MODEL_SETUP.md`: Ollama setup, recommended models, and local inference guide.
- `docs/M7_VALIDATION_RESULTS.md`: Empirical verification test results.

---

## 3. Test Commands & Evidence

- `python3 -m pytest tests/test_desktop_packaging.py`: 5 passed in 0.16s
- `python3 -m pytest tests/test_desktop_sidecar.py`: 3 passed in 0.76s
- `npm --prefix frontend run test:sites`: 6 passed in 0.17s
- `npm --prefix frontend run build`: Successful in 341ms
- Standalone sidecar verification: Verified on `127.0.0.1:53256`, health response 200 OK, shutdown on stdin EOF.
- `python3 -m pytest -q`: 121 passed, 2 skipped, 44 subtests passed

---

## 4. Current Blockers / Dependencies

- None.

---

## 5. Next Exact Action

Commit changes -> Push `feat/m7-tauri-desktop-poc` -> Open PR against `main`.

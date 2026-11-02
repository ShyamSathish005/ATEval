# ATEval repository migration report

**Date:** 2026-11-02
**Destination:** `https://github.com/ShyamSathish005/ATEval.git`
**Branch:** `main` (the destination repository was empty, so initializing its default branch was non-destructive)
**Source:** local ATEval workspace (`Humanizer`; absolute workstation path omitted from this public report)

## Migration and integrity

The destination was cloned into a fresh staging directory outside the parent Desktop repository. Its `origin` matched the destination URL and the clone had no commits or project files. A new independent `main` history was created; no parent `.git`, remote, branch, or history was used.

Transferred 138 audited source files before this report (139 files including this report): 35 Python package files, 16 frontend source/configuration files, 50 research and implementation documents, 8 test files, and the project configuration, packaging, and GitHub Actions files. The complete source-to-destination path inventory and SHA-256 hashes matched for all 138 files before this report was added.

The migrated files include the current API, CLI, manuscript analysis and ingestion modules, LaTeX processing, revision and SCAR implementations, frontend, tests, install/configuration files, CI workflows, security/privacy policies, and model/dataset/third-party notices. The three old release-audit documents that describe the enclosing parent checkout were excluded. Design-review instructions and an unverified design image were also excluded.

The following were excluded: local SQLite state; raw and derived data under `data/`; model artifacts under `models/`; generated predictions and reports under `reports/`; experiment/private annotation material under `experiments/`; caches, build output, dependency trees, upload documents, and local environment files. These exclusions leave the reproducibility instructions and license inventories in the repository without redistributing the underlying research corpora or checkpoints.

A hard-coded `/private/tmp` model-file default was replaced with `~/.cache/ateval/models/XtraGPT-1.5B-q4.gguf` in the API, CLI, and benchmark runner. The README was updated to reflect the current ATEval project and to identify datasets and generated outputs that are not included.

## License status

The existing MIT `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md`, `MODEL_LICENSES.md`, and `DATASET_LICENSES.md` were retained. The `NOTICE` says ownership and release authority have not been verified. The MIT license was not changed, and this migration does not resolve that ownership question. Verify contributor ownership and third-party rights before making a formal release or representing the license status as cleared.

## Checks performed

Checks were run in the isolated destination checkout:

- `PYTHONPATH=. pytest -q`: **79 passed, 3 skipped, 17 subtests passed**. The skipped tests depend on optional components; two deprecation warnings were emitted by the installed Starlette/httpx stack.
- `cd frontend && npm run build`: **passed**.
- `cd frontend && npm run test:sites`: **6 passed**.
- `python3 -m ateval doctor`: **passed**; optional Torch, Transformers, DOCX/PDF extraction, spaCy, and Ollama model dependencies were unavailable and are not required for the core CLI.
- `python3 -m ateval --help`: **passed**.
- Source-to-destination SHA-256 verification: **138/138 files matched**.
- Python release-hygiene tests passed as part of the Python suite. A direct tarball audit was also attempted and reported generated caches from the test run plus historical research documents that the current `SAFE_DOCS` release allowlist rejects. The caches are ignored and are not committed; reconcile the archive policy with the retained research documentation before creating a formal source archive.
- A live UI upload was not repeated as part of this repository migration. The backend multipart/CORS upload integration tests ran within the Python suite; see `cors_upload_failure_analysis.md` and `upload_integration_test_report.md`.
- External dependency audits, Docker image build, GitHub Actions completion, and hosted deployment were not verified locally. Docker and `pip-audit` are not installed in this environment. No formal release or downloadable binary was created. The current release tarball checker allowlist needs review because it rejects the retained public research documentation; do not package a formal source archive until that policy is reconciled.

## Push and remaining verification

The 138-file project import is committed on the independent `main` branch as `794b3af`. This report is committed separately. The push will publish the branch; GitHub Actions must then be checked for completion. The repository migration does not certify production readiness, model quality, semantic equivalence, or ownership of third-party research assets.

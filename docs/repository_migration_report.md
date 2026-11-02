# ATEval repository migration report

**Date:** 2026-11-02
**Destination:** `https://github.com/ShyamSathish005/ATEval.git`
**Branch:** `main` (the destination repository was empty, so initializing its default branch was non-destructive)
**Source:** local ATEval workspace (`Humanizer`; absolute workstation path omitted from this public report)

## Migration and integrity

The destination was cloned into a fresh staging directory outside the parent Desktop repository. Its `origin` matched the destination URL and the clone had no commits or project files. A new independent `main` history was created; no parent `.git`, remote, branch, or history was used.

Transferred 139 audited source files before this report (140 files including this report): 35 Python package files, 16 frontend source/configuration files, 50 research and implementation documents, 8 test files, and the project configuration, packaging, and GitHub Actions files. The complete source-to-destination path inventory and SHA-256 hashes matched for all 139 source files before this report was added.

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
- Source-to-destination SHA-256 verification: **139/139 files matched**.
- `ruff check --select E4,E7,E9,F821 ateval tests scripts`: **passed** after CI identified four existing E731 lambda assignments.
- The first GitHub Actions run (`1b12cbf`) failed the Python jobs on those Ruff findings and failed Docker because the initial staged copy omitted the root `Dockerfile`. The frontend job passed. Both causes were corrected in `c8c33dd`. The follow-up run for `fb8fd3f` passed the Docker and frontend jobs but failed `pytest` in all three Python matrix jobs. Public annotations expose only exit code 2; detailed logs require GitHub sign-in, so the failing test names could not be verified. Locally, the Python suite passed with the optional DOCX/PDF packages installed (81 passed, 1 skipped) as well as without them (79 passed, 3 skipped). This cross-runner pytest failure remains unresolved.
- Follow-up M0.2 investigation reproduced the pytest exit-2 failure at collection on Python 3.11, 3.12 and 3.13. The import traceback identifies the missing `httpx2` dependency required by Starlette's `TestClient`, rather than a signal or test assertion. The CI dependency group now pins it, and `uv.lock` records the resolution. Local locked runs pass on 3.11.14, 3.12.12 and 3.13.12 (82 passed, 1 skipped, 17 subtests each); see `ci_failure_root_cause.md` and `python_compatibility_report.md`. GitHub run logs remain inaccessible to unauthenticated `gh`; only the public exit-code annotations were available.
- The M0.2 branch pins Ubuntu 24.04, updates GitHub Actions references, limits workflow permissions, and preserves pytest logs/JUnit artifacts. Its hosted matrix and Docker build are pending branch execution; local macOS results do not establish Ubuntu CI status.
- After allowing the audit commands network access, `pip-audit` reported no known vulnerabilities in the hash-locked Python dependencies and `npm audit --audit-level=high` reported zero frontend vulnerabilities. The frontend production build and all six frontend site tests pass locally. CLI help and doctor checks pass. See `m0_2_release_readiness.md` for the full status.
- Release archive hygiene now explicitly allows the retained research and migration documents and the M0.2 reports, while continuing to reject private datasets, generated outputs, and the unverified design image. The committed M0.2 source archive passed the checker.
- A live UI upload was not repeated as part of this repository migration. The backend multipart/CORS upload integration tests ran within the Python suite; see `cors_upload_failure_analysis.md` and `upload_integration_test_report.md`.
- External dependency audits, Docker image build, the follow-up GitHub Actions result, and hosted deployment are not verified locally. Docker and `pip-audit` are not installed in this environment. No formal release or downloadable binary was created. The current release tarball checker allowlist needs review because it rejects the retained public research documentation; do not package a formal source archive until that policy is reconciled.

## Push and remaining verification

The 139-file project import is on the independent `main` branch. The initial import is `794b3af`; `c8c33dd` adds the omitted Dockerfile and fixes lint findings. The main branch was pushed to the exact destination and was verified at `38db980` before this M0.2 work. The dedicated M0.2 branch and push status are recorded after publication of the branch. The repository migration does not certify production readiness, model quality, semantic equivalence, or ownership of third-party research assets. The current licence provenance review finds that the available squashed import history does not establish owner authority; a formal release remains blocked pending owner confirmation.

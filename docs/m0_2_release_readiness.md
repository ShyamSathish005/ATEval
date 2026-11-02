# M0.2 release readiness

**Assessment date:** 2026-11-02  
**Base commit:** `38db980`  
**Working branch:** `m0.2-ci-license-audit`

## Status

**Not cleared for a formal release.** The root cause has been reproduced and corrected locally. All three Python versions pass the locked local test run. The dedicated branch still needs a completed hosted GitHub Actions run, and project ownership/release authority requires confirmation from the project owner. No tag or release has been created.

## Work completed

- Added the missing, pinned `httpx2` test dependency and committed lockfile plan (`uv.lock`) to make CI dependency resolution reproducible.
- Pinned the CI runner to Ubuntu 24.04 and upgraded maintained GitHub Actions references to their current major releases reviewed on 2026-11-02. Checkout credentials are disabled, workflow permissions default to read-only, and publication has write permission only in the release publish job.
- Preserved full pytest output and JUnit XML for failed or successful runs, with 14-day artifact retention and a concise job summary.
- Added a strict Python dependency audit using a hash-locked exported requirements file. It excludes the local editable project package and audits third-party packages only.
- Added an explicit documentation archive allowlist for the retained research documents and the M0.2 reports. Added coverage that research/migration reports are allowed while the old excluded `release_audit.md` remains forbidden.
- Documented CI failure evidence, Python compatibility results, licence provenance limits, and release blockers.

## Verification performed locally

| Check | Result |
|---|---|
| Python 3.11.14 test suite | 82 passed, 1 skipped, 17 subtests; exit 0 |
| Python 3.12.12 test suite | 82 passed, 1 skipped, 17 subtests; exit 0 |
| Python 3.13.12 test suite | 82 passed, 1 skipped, 17 subtests; exit 0 |
| Ruff (`E4,E7,E9,F821`) | Passed on all three locked environments |
| Python dependency audit | Passed against the hash-locked third-party requirements export; no known vulnerabilities found |
| Frontend tests and production build | `npm run build` passed; all 6 `npm run test:sites` tests passed |
| Frontend dependency audit | `npm audit --audit-level=high` passed; 0 vulnerabilities |
| Docker image build | Not run locally; Docker CLI is unavailable. The previous hosted run built Docker successfully, but this branch's updated workflow still needs hosted verification |
| Archive hygiene | Committed source archive passed `scripts/check_release_archive.py` |
| CLI smoke tests | `python -m ateval --help` and `python -m ateval doctor` passed; optional model/spaCy/LaTeX services are absent as expected |
| GitHub Actions matrix | Pending branch push and hosted execution; local platform is macOS ARM, while CI is pinned to Ubuntu 24.04 |

The optional Milestone 3 model-artifact test remains skipped because its trained artifact is intentionally absent. The local Python and npm advisory lookups passed after granting the audit commands registry access. Diagnostic pytest logs and JUnit XML are saved outside the repository under `/private/tmp/ateval-m0.2-logs/`.

## Required before formal release

1. Push this branch and confirm the actual Python 3.11, 3.12 and 3.13 GitHub Actions jobs pass, along with frontend and Docker jobs.
2. Confirm the actual hosted workflow results. Frontend build/tests, both dependency audits, CLI smoke tests, and the committed source archive hygiene check pass locally.
3. Obtain owner confirmation of file authorship/permissions and authority to release the project-authored work under MIT; resolve any third-party licence/provenance questions that confirmation reveals.
4. Update the migration/readiness report with the hosted CI run and resolved or remaining rights findings.

If the hosted result or authority confirmation is unavailable, keep the project unreleased and describe the remaining blocker accurately. Do not mark the package production-ready based on local test results alone.

# M0.2 release readiness

**Assessment date:** 2026-11-02  
**Base commit:** `38db980`  
**Working branch:** `m0.2-ci-license-audit`

## Status

**Not cleared for a formal release.** The pytest root cause is corrected and verified by hosted CI. Python 3.11, 3.12, 3.13, frontend and Docker jobs passed in runs [41479922335](https://github.com/ShyamSathish005/ATEval/actions/runs/41479922335) and [41480358638](https://github.com/ShyamSathish005/ATEval/actions/runs/41480358638); the latter verified report commit `036e636d3667a841a580860a1787b4da19415ec5`. Project ownership/release authority still requires confirmation from the project owner. No tag or release has been created.

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
| Docker image build | Passed in hosted run 41479922335 on Ubuntu 24.04 |
| Archive hygiene | Committed source archive passed `scripts/check_release_archive.py` |
| CLI smoke tests | `python -m ateval --help` and `python -m ateval doctor` passed; optional model/spaCy/LaTeX services are absent as expected |
| GitHub Actions matrix | Passed in runs 41479922335 and 41480358638 on Ubuntu 24.04 for Python 3.11, 3.12, 3.13, frontend and Docker; release-gate was skipped for the feature-branch push |

The optional Milestone 3 model-artifact test remains skipped because its trained artifact is intentionally absent. The local Python and npm advisory lookups passed after granting the audit commands registry access. Diagnostic pytest logs and JUnit XML are saved outside the repository under `/private/tmp/ateval-m0.2-logs/`.

## Required before formal release

1. Confirm the authorship/permissions history and authority to release the project-authored work under MIT; resolve any third-party licence/provenance questions that confirmation reveals.
2. Re-run CI after any follow-up implementation change; the latest completed run verified report commit `036e636`.
3. Keep the release untagged until rights confirmation is documented.

If the hosted result or authority confirmation is unavailable, keep the project unreleased and describe the remaining blocker accurately. Do not mark the package production-ready based on local test results alone.

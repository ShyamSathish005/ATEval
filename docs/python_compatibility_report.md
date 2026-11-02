# Python compatibility report

**Date:** 2026-11-02

## Support target and method

The package declares Python `>=3.11`. The CI matrix targets Python 3.11, 3.12 and 3.13. Each version was installed and tested independently with uv-managed Python (`3.11.14`, `3.12.12`, `3.13.12`) using the committed lockfile and the same `ui-server`, `writing-docs`, `revision-ml`, and `ci` dependency groups configured for CI.

The test invocation was `PYTHONPATH=. pytest -vv -ra --tb=long -s --junitxml=...`; the repository Ruff command was `ruff check --select E4,E7,E9,F821 ateval tests scripts`.

## Results

| Python | Tests | Ruff | Notes |
|---|---:|---|---|
| 3.11.14 | 82 passed, 1 skipped, 17 subtests | Passed | Local macOS ARM; 8 warnings, primarily dependency deprecations |
| 3.12.12 | 82 passed, 1 skipped, 17 subtests | Passed | Local macOS ARM; 8 warnings, primarily dependency deprecations |
| 3.13.12 | 82 passed, 1 skipped, 17 subtests | Passed | Local macOS ARM; 8 warnings, primarily dependency deprecations |

The single skipped test requires trained Milestone 3 model artifacts, which are intentionally not committed. No compatibility failures were marked expected or hidden. The same test suite initially failed collection on all three versions because the test dependency `httpx2` was missing; see [CI failure root cause](ci_failure_root_cause.md).

## Reproducibility and limits

`uv.lock` records the resolved dependency versions and package hashes. CI uses `uv sync --locked`, so an unreviewed dependency change cannot silently alter the environment. The lock was generated for the supported Python range and resolves platform-specific wheels as needed.

The local verification ran on macOS ARM. Hosted runs [41479922335](https://github.com/ShyamSathish005/ATEval/actions/runs/41479922335) and [41480358638](https://github.com/ShyamSathish005/ATEval/actions/runs/41480358638) both passed the Python 3.11, 3.12 and 3.13 matrix on Ubuntu 24.04 (the latter run verified report commit `036e636d3667a841a580860a1787b4da19415ec5`). The environment also lacks the optional trained model artifact; model-backed integration coverage is therefore not represented by the skipped test.

Detailed run logs and JUnit reports were retained in `/private/tmp/ateval-m0.2-logs/` for this investigation and are not included in the public repository because they are generated artifacts.

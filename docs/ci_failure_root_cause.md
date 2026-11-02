# CI pytest failure root cause

**Investigation date:** 2026-11-02  
**Affected run:** [GitHub Actions run 41473748269](https://github.com/ShyamSathish005/ATEval/actions/runs/41473748269)  
**Investigated commit:** `38db980`

## Finding

All three Python matrix jobs stopped during pytest collection with exit code 2. A fresh reproduction using the workflow's Python dependency groups and the command `PYTHONPATH=. pytest -q` produced the same traceback on Python 3.11.14, 3.12.12 and 3.13.12:

```text
RuntimeError: The starlette.testclient module requires the httpx2 package to be installed.
ERROR tests/test_api.py - RuntimeError: ...
Interrupted: 1 error during collection
```

This is a collection-time import error raised while `tests/test_api.py` imports Starlette's `TestClient`. It is not a test assertion failure, a `KeyboardInterrupt`, a signal, a `pytest.exit()` call, or an external runner termination. Pytest's exit code 2 identifies interrupted execution; the captured traceback identifies why this execution stopped.

The workflow installed FastAPI and its unconstrained Starlette dependency, but the test suite's `TestClient` integration now requires the separately packaged `httpx2` transport. The runtime dependency resolution therefore differed from the tests' actual requirements. The same exception reproduced across all three interpreter versions, so this was not a Python-version incompatibility.

## Investigation performed

- Inspected all publicly available failed-job annotations for run `41473748269`. They show the failing command and exit code, but not the detailed traceback.
- Checked out the reported commit in an isolated staging clone and installed the original CI dependency groups in fresh Python 3.11, 3.12 and 3.13 environments.
- Ran the exact `PYTHONPATH=. pytest -q` command for each interpreter and retained the output and JUnit diagnostics under `/private/tmp/ateval-m0.2-logs/`.
- Inspected test and project files for `pytest.exit`, `KeyboardInterrupt`, signal registration, `sys.exit`, `conftest.py`, and pytest plugin configuration. No test-level interruption or signal handler explains this failure. CLI `SystemExit` uses are normal command-line entry points.
- No repository `conftest.py`, `pytest.ini`, `tox.ini`, or custom pytest plugin is present.

The GitHub CLI is installed but unauthenticated in this environment (`gh auth status` reports no logged-in host). GitHub therefore withholds full job logs; the public check annotations expose only the exit code. The local failure reproduction supplies the traceback, but this report does not claim to have inspected unavailable private run logs.

## Corrective change

Added a pinned `httpx2==2.16.0` test dependency in the `ci` extra and added a committed `uv.lock` so CI uses a reproducible, hash-verified dependency resolution. CI now installs that extra and retains verbose pytest logs and JUnit XML as workflow artifacts. The test command continues to use `PYTHONPATH=.`. `set -o pipefail` preserves pytest failures through the log-capture pipeline.

No model, research algorithm, test expectation, or failure condition was changed to obtain a passing result. No tests were marked `xfail`, skipped, or suppressed as part of this fix.

## Verification

With the lockfile and CI extras, Python 3.11, 3.12 and 3.13 each report **82 passed, 1 skipped, 17 subtests passed** locally. The one skipped test requires trained Milestone 3 model artifacts, which are not part of the repository. Ruff passes in each environment. Logs and JUnit XML are retained outside the repository at `/private/tmp/ateval-m0.2-logs/final-3.11.*`, `final-3.12.*`, and `final-3.13.*`.

Hosted run [41479922335](https://github.com/ShyamSathish005/ATEval/actions/runs/41479922335), for commit `518d56244b11897bbafba2a5bfb153f7717e5872`, completed successfully on Ubuntu 24.04. Python 3.11, 3.12 and 3.13, frontend, and Docker jobs all passed. The release-gate job was skipped because the push was to the dedicated feature branch, not `main` or a pull request. This closes the CI blocker for the verified commit; any follow-up commit will trigger another run.

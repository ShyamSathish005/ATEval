# Platform compatibility matrix

This matrix records observed evidence, not an unconditional support promise.

| Platform | Python / Node evidence | Native install | API / analysis | Frontend build | Docker |
|---|---|---|---|---|---|
| macOS (local assessment host) | Python 3.13; Node 26.4 / npm 12.0.1 | Pass | Pass: health, synthetic upload, analysis | Pass: `npm ci`, build, six site checks | Not tested: Docker unavailable |
| Ubuntu 24.04 (GitHub Actions) | Python 3.11, 3.12, 3.13; Node 22 | CI dependency sync and tests pass | Not a native API smoke test | Pass in CI | Image build pass; Compose runtime not tested |
| Windows | Not tested | Pending | Pending | Pending | Pending |

## Reproduction evidence

The macOS record used a clean checkout and:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[ui-server,writing-docs,ci]'
.venv/bin/python -m ateval doctor
PYTHONPATH=. .venv/bin/pytest -q
cd frontend && npm ci && npm run build && npm run test:sites
npm audit --audit-level=high
```

The hosted Linux record is [CI run 41573865780](https://github.com/ShyamSathish005/ATEval/actions/runs/41573865780).
Windows remains pending and must not be described as verified support.

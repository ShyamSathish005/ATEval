# Contributing

ATEval is an experimental research preview. Contributions should preserve
reproducibility, privacy, and clear limits on scientific claims.

## Before opening a change

- Read `CODE_OF_CONDUCT.md`, `SECURITY.md`, `PRIVACY.md`, and the feature status
  and limitation sections in `README.md`.
- Do not commit unpublished manuscripts, credentials, local databases,
  checkpoints, raw datasets, reviewer keys, or reviewer annotations.
- Use synthetic fixtures or sources whose reuse terms are documented.
- Keep local manuscript processing offline by default. Any external network
  access must be explicit, documented, and covered by tests.
- Do not optimize editing or detector features for AI-detector scores.

## Development checks

```sh
python -m pip install -e ".[ui-server,writing-docs,revision-ml]" pytest
PYTHONPATH=. pytest -q
cd frontend && npm ci && npm run build && npm run test:sites
```

For security-sensitive changes, add focused tests for malformed input,
traversal, size limits, and safe error responses. Never log manuscript text.
Changes to scientific methods need a protocol, data/license record, baselines,
and limitations before claims are added to the UI or documentation.

## Licensing

The project license and ownership are under review. By submitting a patch,
you confirm you have the right to contribute it, but do not assume that this
workspace has authority to relicense contributions under Apache-2.0. That
decision is blocked until repository ownership is verified.

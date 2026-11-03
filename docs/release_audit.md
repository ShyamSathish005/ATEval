# Repository release audit

Audit performed 2026-11-02. No project files were deleted.

## Repository and history

The ATEval directory is not itself a Git repository. `git rev-parse --show-toplevel`
resolves to the parent Desktop directory; the active `origin` points to
`ShyamSathish005/TrainDekho`, and the most recent commit is a TrainDekho
application commit. The parent worktree contains unrelated personal folders,
PDFs, and another app with pending deletions. They are outside this task's
writable project boundary and must not be staged, cleaned, tagged, or pushed.

No ATEval-specific release commit or tag can safely be created from this
history. The `v0.1.0-alpha` tag must be created only after the ATEval source is
placed in its verified standalone repository with an approved remote.

## Files and local artifacts found

- `.ateval/ateval.sqlite3`: local workspace database; excluded.
- `data/raw/` and `data/processed/`: IteraTeR-HUMAN source and derived text;
  excluded pending rights review.
- `data/annotations/`, `experiments/milestone4_4/blind_key.json`, and
  `reviewer_annotations.jsonl`: research packets and human labels; excluded
  pending consent and de-identification review.
- `models/`: fitted sklearn/joblib artifacts; excluded because they derive
  from excluded source text and joblib is a pickle-based format.
- `reports/`: includes predictions and evaluation records; excluded from
  release bundles by default because outputs may reproduce source passages.
- `frontend/node_modules/`, `frontend/dist/`, `.pytest_cache/`, Python caches,
  and `frontend/*.tsbuildinfo`: generated local build/test files; excluded.
- `frontend/.openai/hosting.json`: platform metadata; excluded.
- `frontend/public/design-option-3.png`: unused design exploration asset with
  unverified provenance; excluded from release artifacts until rights are
  documented.
- No `.env` file, API credential, large model checkpoint, manuscript fixture,
  or runtime log was found by the bounded project/config inspection. This is
  not a substitute for scanning full Git history in the eventual repository.

## Code and runtime inspection

- No `subprocess`, `os.system`, or `shell=True` usage exists in the ATEval
  application paths inspected. Manuscript analysis does not invoke TeX.
- ZIP ingestion rejects absolute/traversal paths, symlinks, duplicate paths,
  more than 2,000 files, and expanded contents over 100 MiB. Regression tests
  cover these guards.
- The native CLI binds to loopback by default. Public-demo mode is separate,
  rate-limits API requests, disables uploads and mutations, and accepts only
  an embedded synthetic sample.
- A configurable ASGI request-body cap now rejects oversized requests before
  multipart parsing can spool large data to temporary storage.
- Local npm audit could not reach `registry.npmjs.org` because network DNS is
  unavailable. `pip-audit` is not installed locally. CI now runs both audit
  tools; findings remain unverified until that job succeeds.
- Docker is not installed in the current environment. Dockerfile and Compose
  configuration are prepared but not locally built or run.

## Rights and release boundary

The root LICENSE currently says MIT, while the requested release proposes
Apache-2.0. Ownership and contributor authority are not established in the
project history. The existing license was preserved; no Apache-2.0 claim is
made. The release manifest and source-package whitelist keep data, models,
annotations, reports, local state, and platform metadata out of bundles.

The direct frontend package metadata includes Poppins under OFL-1.1 and
MIT-licensed React, Radix icons, Motion, Recharts, Tailwind, and Vite packages;
the exact transitive dependency inventory and Python dependency licenses must
be generated and reviewed from the release lockfiles/SBOM before publication.

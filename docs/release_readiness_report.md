# Alpha release readiness report

**Assessment branch:** `m0.4-release-readiness`
**Assessment commit:** `93246666b1e249304355f926b80d87622d92ca11`
**Base:** `main`
**Assessment date:** 2026-11-03

## Decision

**Not ready for tag or publication.** The latest verified main CI run
`41573865780` passed all jobs. The project owner has confirmed authority for
project-authored material under MIT, but Docker Compose runtime verification,
complete platform coverage, and independent security/privacy review remain
incomplete. No release artifact or tag has been created.

## Verified

### Historical evidence retained

- The merged main commit is `bbfa159`; previous branch and merge checks remain
  historical evidence and are not relabeled as M0.4 tests.
- Clean macOS installation and API smoke-test evidence was recorded before this
  branch; it remains applicable to the unchanged application code.

### Current verified evidence

- Main CI run `41573865780` passed Python 3.11, 3.12, 3.13, frontend, Docker
  image build, and release-gate jobs. The actual jobs and conclusions were
  verified with `gh run view`.
- A clean macOS checkout using Python 3.13 installed the declared UI,
  document, and CI extras; `ateval doctor`, 82 tests, and the CLI completed
  successfully.
- A clean frontend checkout passed `npm ci`, the production build, all six
  packaged-site checks, and `npm audit --audit-level=high`.
- A local API smoke test passed health, manuscript upload, and analysis
  requests against the clean installation.
- Frontend production build, packaged-site checks, and npm audit passed in
  main CI.
- The hosted Docker image build passed; this does not verify Compose runtime
  behavior.
- Archive allowlist and release hygiene tests passed.
- The repository is isolated in `ShyamSathish005/ATEval`; PR #1 merged into
  `main` at `bbfa159`. This M0.4 work is intentionally on a separate branch.
- Provenance documentation distinguishes project-authored material,
  AI-assisted development, third-party contributions, dependencies, models,
  and datasets. MIT is not asserted for external assets.
- The project owner explicitly confirmed ownership and licensing authority for
  project-authored material; the provenance report records the scope and date.

| Requirement | Result | Evidence |
|---|---|---|
| Python CI | Pass | Main run `41573865780`, Python 3.11/3.12/3.13 jobs |
| Frontend build | Pass | Main run `41573865780`, frontend job |
| Dependency audits | Pass | Python audit and npm audit in main run |
| Archive hygiene | Pass | Python job in main run |
| Docker image build | Pass | Main run `41573865780`, docker job |
| Docker Compose lifecycle | Pending | Docker unavailable; see [runtime report](docker_runtime_report.md) |
| Ownership/licence authority | Confirmed | Owner confirmation recorded in provenance report |
| macOS installation | Pass | Clean local Python 3.13 and frontend evidence |
| Ubuntu/Linux installation | Partial | Hosted CI dependency/test evidence; native install/API smoke test pending |
| Windows installation | Pending | No clean Windows environment available |
| Security/privacy review | Pending | Operational review recorded; independent audit not completed |

## Pending

- Docker Compose lifecycle verification, including health, synthetic LaTeX and
  LaTeX ZIP upload/analysis, loopback binding, cleanup, and shutdown.
- Docker and Docker Compose are unavailable in the assessment environment
  (`docker: command not found`), so no local runtime, loopback, cleanup, or
  graceful-shutdown result is claimed. See
  [docker runtime report](docker_runtime_report.md).
- Platform-specific verification. macOS local evidence and Ubuntu CI evidence
  exist; Windows and a clean Linux native install remain unverified. See
  [platform matrix](platform_compatibility.md).
- Independent security and privacy review before any public deployment. The
  local threat-model assessment and unresolved risks are in
  [security and privacy review](security_privacy_review.md).
- The security review identified a medium-severity SSRF risk in optional
  Ollama URL validation. A minimal fix and regression tests pass on this
  branch, but the fix is not in `main`; no security clearance is claimed.

## Release action

Do not create `v0.1.0-alpha` or invoke the release workflow until every
mandatory item in [release_checklist.md](release_checklist.md) is checked. Do
not claim scientific validation or support for an untested platform.

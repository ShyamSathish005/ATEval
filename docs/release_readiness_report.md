# Alpha release readiness report

**Branch:** `main`
**Verified merge commit:** `bbfa15936ecf3b092cf0ef2f99a33ad6c0ecc270`
**Assessment date:** 2026-11-03

## Decision

**Not ready for tag or publication.** Main is merged and its latest CI run
`41572673696` passed, but owner confirmation of licensing authority, clean
Docker Compose application verification, platform coverage, and independent
security/privacy review remain incomplete. No release artifact or tag has been
created.

## Verified

- Main CI run `41572673696` passed Python 3.11, 3.12, 3.13, frontend, Docker
  image build, and release-gate jobs.
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
  `main` at the verified commit above.
- Provenance documentation distinguishes project-authored material,
  AI-assisted development, third-party contributions, dependencies, models,
  and datasets. MIT is not asserted for external assets.

## Pending

- Written owner confirmation of authorship/permissions and authority to apply
  MIT to the project-authored portions.
- Clean installation and Compose lifecycle verification, including health,
  manuscript upload, analysis, and shutdown.
- Docker and Docker Compose are unavailable in the assessment environment
  (`docker: command not found`), so no local runtime, loopback, cleanup, or
  graceful-shutdown result is claimed. See
  [docker runtime report](docker_runtime_report.md).
- Platform-specific verification. The repository currently documents
  instructions for macOS, Windows, and Linux but has not tested clean
  environments for all three.
- Independent security and privacy review before any public deployment.

## Release action

Do not create `v0.1.0-alpha` or invoke the release workflow until every
mandatory item in [release_checklist.md](release_checklist.md) is checked. Do
not claim scientific validation or support for an untested platform.

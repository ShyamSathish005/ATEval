# Alpha release checklist

This checklist is for `v0.1.0-alpha`. A checked item must have reproducible
evidence in the release readiness report or linked CI run.

**Assessment branch:** `main`
**Assessment commit:** `b70b99d47b70e7a1faecb90d788a84a8e10acb18`

## Required gates

- [x] Isolated public Git repository, reviewed branch diff, and merge to main.
- [x] Main CI run `41595840933` passed Python 3.11, 3.12, and 3.13 checks.
- [x] Main CI run `41595840933` passed frontend build, packaged-site checks,
  and npm audit.
- [x] Main CI run `41595840933` passed the Docker image build (runtime remains
  unverified).
- [x] Main CI run `41595840933` passed Python dependency audit and archive
  hygiene checks.
- [x] Owner confirmation of authorship and authority to license project-authored
  material under MIT, recorded in `docs/final_license_provenance_review.md`.
- [ ] Clean Docker Compose startup, health check, upload, analysis, loopback
  binding, temporary-file cleanup, and graceful shutdown verification.
- [ ] macOS, Linux, and Windows clean-install verification. Current evidence
  supports macOS local verification and Ubuntu CI only; see
  [platform matrix](platform_compatibility.md).
- [x] Independent security and privacy review completed with one medium ZIP
  traversal issue fixed and regression-tested; no public confidential-
  manuscript deployment is offered.

The M0.4 branch contains a tested SSRF validation fix for optional Ollama
inference. It must be reviewed and merged before that fix can be part of a
release; this checklist does not authorize merging or publication.

## Publication rule

Do not create `v0.1.0-alpha` or publish a GitHub release while a mandatory
gate is unchecked. Third-party dependencies, model
checkpoints, datasets, fonts, and research artifacts retain their own terms
and are not covered by the project's MIT notice.

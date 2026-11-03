# Alpha release checklist

This checklist is for `v0.1.0-alpha`. A checked item must have reproducible
evidence in the release readiness report or linked CI run.

## Required gates

- [x] Isolated public Git repository, reviewed branch diff, and merge to main.
- [x] Main CI run `41572673696` passed Python 3.11, 3.12, and 3.13 checks.
- [x] Main CI passed frontend build, packaged-site checks, and npm audit.
- [x] Main CI passed the Docker image build (runtime remains unverified).
- [x] Main CI passed Python dependency audit and archive hygiene checks.
- [x] Owner confirmation of authorship and authority to license project-authored
  material under MIT, recorded in `docs/final_license_provenance_review.md`.
- [ ] Clean Docker Compose startup, health check, upload, analysis, loopback
  binding, temporary-file cleanup, and graceful shutdown verification.
- [ ] Installation verification on every platform claimed in release
  documentation.
- [ ] Independent security and privacy review for any public deployment.

## Publication rule

Do not create `v0.1.0-alpha` or publish a GitHub release while a mandatory
gate is unchecked. Third-party dependencies, model
checkpoints, datasets, fonts, and research artifacts retain their own terms
and are not covered by the project's MIT notice.

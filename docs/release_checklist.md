# Alpha release checklist

This checklist is for `v0.1.0-alpha`. A checked item must have reproducible
evidence in the release readiness report or linked CI run.

## Required gates

- [x] Isolated public Git repository and reviewed branch diff.
- [x] Python 3.11, 3.12, and 3.13 hosted CI checks.
- [x] Frontend build, packaged-site checks, and npm audit.
- [x] Docker image build.
- [x] Python dependency audit and archive hygiene check.
- [ ] Owner confirmation of authorship and authority to license project-authored
  material under MIT.
- [ ] Clean Docker Compose startup, health check, upload, analysis, and
  shutdown verification.
- [ ] Installation verification on every platform claimed in release
  documentation.
- [ ] Independent security and privacy review for any public deployment.

## Publication rule

Do not merge the release PR, create `v0.1.0-alpha`, or publish a GitHub
release while a mandatory gate is unchecked. Third-party dependencies, model
checkpoints, datasets, fonts, and research artifacts retain their own terms
and are not covered by the project's MIT notice.

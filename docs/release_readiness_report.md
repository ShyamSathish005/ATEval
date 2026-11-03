# Alpha release readiness report

**Branch:** `m0.2-ci-license-audit`  
**Expected commit:** `f35f6959035f04f2f52de6f0551fbcad93e4b5b4`  
**Assessment date:** 2026-11-03

## Decision

**Not ready for merge, tag, or publication.** Hosted CI verifies the code and
packaging gates listed below, but owner confirmation of licensing authority,
clean Docker Compose application verification, and independent security/privacy
review remain incomplete. No release artifact or tag has been created.

## Verified

- Python 3.11, 3.12, and 3.13 tests, lint, and dependency audit passed in
  hosted runs `41479922335` and `41480358638`.
- A clean macOS checkout using Python 3.13 installed the declared UI,
  document, and CI extras; `ateval doctor`, 82 tests, and the CLI completed
  successfully.
- A clean frontend checkout passed `npm ci`, the production build, all six
  packaged-site checks, and `npm audit --audit-level=high`.
- A local API smoke test passed health, manuscript upload, and analysis
  requests against the clean installation.
- Frontend production build, packaged-site checks, and npm audit passed.
- Docker image build passed in hosted CI.
- Archive allowlist and release hygiene tests passed.
- The branch is isolated in `ShyamSathish005/ATEval` and is based on the
  requested commit.
- Provenance documentation distinguishes project-authored material,
  AI-assisted development, third-party contributions, dependencies, models,
  and datasets. MIT is not asserted for external assets.

## Pending

- Written owner confirmation of authorship/permissions and authority to apply
  MIT to the project-authored portions.
- Clean installation and Compose lifecycle verification, including health,
  manuscript upload, analysis, and shutdown.
- Docker and Docker Compose were unavailable in the assessment environment, so
  no Docker lifecycle result is claimed.
- Platform-specific verification. The repository currently documents
  instructions for macOS, Windows, and Linux but has not tested clean
  environments for all three.
- Independent security and privacy review before any public deployment.

## Release action

Create the requested PR for review, but do not merge it or invoke the release
workflow until every mandatory item in [release_checklist.md](release_checklist.md)
is checked. Do not claim scientific validation or support for an untested
platform.

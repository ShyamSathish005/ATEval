# Public release hardening report

Audit and implementation status: 2026-11-02.

## Implemented in the workspace

- Added contributor, conduct, security, privacy, citation, installation,
  quick-start, OS setup, troubleshooting, architecture, limitation,
  methodology, model/dataset licensing, and release-checklist documentation.
- Added a release exclusion manifest, Python source-distribution whitelist,
  Git/Docker ignore rules, and a source-tar hygiene validator. Local datasets,
  reports, models, annotation packets, databases, user manuscript formats,
  node modules, build outputs, and unverified design assets are excluded
  without deleting the workspace originals.
- Set the requested application version string to `0.1.0-alpha` and added an
  unreleased changelog/notes draft. Existing MIT licensing was preserved
  because ownership authority for Apache-2.0 relicensing is not verified.
- Added an `ateval doctor` report for Python/runtime package versions, API
  dependencies and local server availability, frontend build, local Ollama
  and selected model, LaTeX compiler, storage capacity, and permissions.
- Added configurable API upload/request size limits. Oversized bodies are
  rejected before multipart parsing can spool large content.
- Added a multi-stage Dockerfile and hardened loopback-only Docker Compose
  setup: non-root UID, read-only root filesystem, no added capabilities,
  `no-new-privileges`, bounded `/tmp`, health check, graceful stop, and named
  data volume.
- Added a separate Render public-demo configuration. Public mode accepts only
  a fixed synthetic sample, rejects file uploads and state-changing API paths,
  applies a per-client in-memory rate limit, uses ephemeral storage, and
  updates the UI to disclose the public mode.
- Added CI jobs for Python tests/lint/dependency audit, frontend build/tests/
  audit, and Docker build. The manual release workflow verifies CI, builds
  packages and a Docker image archive, emits SBOMs/checksums, checks source
  archive exclusions, and requires explicit dispatch to publish.
- Added npm license-file copying to built frontend assets.

## Checks executed locally

- `PYTHONPATH=. pytest -q`: **80 passed, 2 skipped, 17 subtests passed**.
- `cd frontend && npm run build && npm run test:sites`: build succeeded;
  **6 frontend/site tests passed**.
- `python3 -m ateval doctor`: returned a structured report with installed and
  missing capabilities.
- Python compilation and YAML parse checks passed for Docker Compose, Render,
  CI/release workflows, and the exclusion manifest.
- A manual attempt to start a separate local public-mode server could not bind
  a port in the current sandbox (`operation not permitted`). Public-mode API
  behavior was tested using FastAPI's in-process test client.

## Release blockers

1. **Wrong Git context:** ATEval has no standalone `.git` directory. Git root
   and `origin` resolve to the parent Desktop repository for TrainDekho, which
   also contains unrelated personal files. No files outside ATEval were
   changed. Tagging or publishing from this context would be unsafe.
2. **Ownership and license:** the existing `LICENSE` is MIT. Ownership and
   contributor authority to relicense under Apache-2.0 have not been
   established. The requested Apache license must not be asserted yet.
3. **Dependency security scan:** local `npm audit` could not reach the npm
   advisory service because DNS/network access was unavailable. `pip-audit`
   is not installed locally. CI contains both checks, but no CI run has
   occurred in the authoritative ATEval repository.
4. **Build, Docker, and clean installs:** the source build could not create its
   isolated setuptools environment because PyPI DNS/network access is
   unavailable; a no-isolation retry failed because setuptools is not
   installed. Docker is not installed, so the image/Compose service was not
   built or run. Clean macOS, Windows, and Linux installations have not been
   verified.
5. **Public hosting:** Render configuration is prepared but not deployed.
   Platform-specific host forwarding, logging, retention, and resource limits
   need verification before launch. The in-process limiter is not a
   distributed DDoS defense.
6. **Independent review:** no external security/privacy review has been
   completed. The configured demo is synthetic-only; do not enable user
   manuscript uploads on a public host.
7. **Release artifacts:** no source archive, Docker image, SBOM, or checksum
   was produced locally, and `v0.1.0-alpha` was not tagged or published.
   The workflow prepares these only after the code is committed in the
   verified standalone ATEval repository and CI passes.
8. **CI action pinning / branch protection:** workflow actions use version
   tags and must be pinned to reviewed commit SHAs. Protected-main rules
   require configuration in the authoritative hosting account.

The release is therefore **prepared but not ready to publish**. See the
[repository audit](release_audit.md), [release checklist](release_checklist.md),
and [release notes draft](release_notes_v0.1.0-alpha.md).

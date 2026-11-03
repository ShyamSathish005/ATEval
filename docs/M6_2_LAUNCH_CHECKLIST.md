# M6.2 launch checklist

## Repository

- [x] M6.1 changes are committed, reviewed, and integrated into `main`.
- [x] M6.2 branch changes are reviewed and integrated without a direct unreviewed merge to `main`.
- [ ] M5.1/M5.2 manifests and reports are unchanged.
- [x] CI is green for Python, frontend, Docker image, and release gates.

## Local functionality

- [x] Academic Humanizer is the primary application entry point.
- [x] TXT, TEX, and LaTeX ZIP source mapping and approved export are tested.
- [x] Accept, reject, manual validation, and undo are implemented.
- [x] Protected-content and claim-cue checks fail closed.
- [x] Public demo uses a synthetic sample and disables uploads/editing.

## Model generation

- [x] Loopback-only Ollama adapter and explicit failure states exist.
- [x] Deterministic mock coverage exists for CI.
- [x] A real local model was executed with `scripts/smoke_test_local_model.py`.
- [x] Model name, version, quantization, hardware, and latency are recorded.
- [x] The configured model passes citation and equation-reference preservation scenarios; unsupported or unsafe output remains fail-closed.

## Preservation and privacy

- [x] LaTeX/ZIP preservation fixtures cover assets and protected content.
- [x] PDF remains read-only.
- [x] Browser undo history limitation is documented.
- [x] Local storage and optional audit export are documented.
- [ ] Independent security review is complete for any hosted deployment.

## Installation and distribution

- [x] macOS installer and loopback launcher are provided.
- [x] Manual Windows/Linux instructions are provided without claiming support.
- [x] macOS installer has been run in a clean local environment; a separate clean-machine test remains unavailable.
- [ ] Docker build and Compose lifecycle have been run.
- [ ] Landing/demo copy and screenshots are reviewed against the running app.

## Release

- [ ] All required gates above pass.
- [ ] Alpha limitations and human-review warning are included.
- [ ] No detector score or authorship claim appears in launch copy.
- [ ] Only after review: create a limited alpha distribution or GitHub release.

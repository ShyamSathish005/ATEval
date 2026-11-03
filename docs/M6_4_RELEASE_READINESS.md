# M6.4 release readiness

## Released alpha

`ATEval v0.1.0-alpha.1`

The initial supported configuration is macOS, local-first processing,
loopback-only API access, and the tested
`ateval-xtragpt-1_5b-q8_0` model through Ollama. Linux, Windows, and Docker
Compose are unverified and are not advertised as supported.

## Evidence

- Main integration: `b70b99d47b70e7a1faecb90d788a84a8e10acb18`.
- Main CI run `41595840933`: Python 3.11/3.12/3.13, frontend, Docker image,
  dependency audit, archive hygiene, and release-gate checks passed.
- Local Python suite: 111 passed, 1 skipped.
- Frontend production build and six packaged-site tests passed.
- macOS installer, loopback launcher, API health, and real Ollama smoke test
  were verified locally.
- Citation and equation-reference preservation passed after exact-source
  canonicalization; unsafe output remains fail-closed.
- Independent security review is recorded in
  [INDEPENDENT_SECURITY_REVIEW_M6_4.md](./INDEPENDENT_SECURITY_REVIEW_M6_4.md).

## Explicit limitations

- Docker is unavailable in the release environment, so Compose startup,
  upload, shutdown, volume cleanup, and port verification remain untested.
- A separate clean physical Mac was unavailable; local installation evidence
  is from the development Mac environment.
- No TeX compiler is installed; source-level LaTeX preservation was tested,
  but PDF compilation was not.
- No public confidential-manuscript upload service is offered.
- The AI Writing Evaluator remains an experimental, non-validated research
  module and is not an authorship detector.

## Release status

`v0.1.0-alpha.1` was published from the verified `main` commit after the
required scoped gates passed. No Docker or cross-platform support claim is
made; those environments remain explicitly unverified.

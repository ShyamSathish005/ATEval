# Security and privacy review

**Scope:** local ATEval application and Docker configuration  
**Assessment:** M0.4 documentation review, 2026-11-03  
**Status:** operational review recorded; independent security audit not
completed

## Controls observed

- Native API defaults to `127.0.0.1`; Compose publishes only
  `127.0.0.1:${ATEVAL_PORT}`.
- Upload limits are configurable and archive imports validate traversal,
  symlinks, duplicate paths, file count, and expanded size.
- Analysis does not compile LaTeX, execute document commands, or overwrite
  source manuscripts.
- Production routing is same-origin and does not use wildcard credentialed
  CORS.
- Docker uses a non-root user, read-only root filesystem, dropped
  capabilities, `no-new-privileges`, and an ephemeral `/tmp`.
- CI runs Python dependency auditing and npm audit; the latest main CI passed
  those checks.

## Privacy boundaries

Native analysis does not persist the original uploaded manuscript, but local
`.ateval/` state may contain metadata, imported datasets, reports, and accepted
edit snippets. The Docker named volume persists state after container removal.
Remote inference is optional and can disclose manuscript contents. Do not use
public hosting or remote inference for confidential manuscripts without an
independent review.

## Unresolved risks and required actions

1. **Resolved on this branch — medium SSRF risk in optional Ollama URL
   validation.** The branch now parses the URL and requires an exact approved
   loopback hostname, with regression tests for attacker-controlled suffixes,
   credentials, schemes, and paths. This fix is not in `main` until the branch
   is reviewed and merged.
2. Docker Compose runtime behavior, temporary-file cleanup, and synthetic
   upload/analysis have not been tested because Docker is unavailable.
3. No independent security reviewer has certified the application or a public
   deployment. `SECURITY.md` still requires a verified private reporting
   contact before public release.
4. The Docker image listens on `0.0.0.0`; running it with a non-loopback
   publish rule exposes unauthenticated upload and metadata endpoints.
5. Windows and native Linux installation evidence is incomplete.
6. Dependency audit results cover known advisories, not all licence or
   application-level vulnerabilities.

This review is not a penetration test, security certification, or public
deployment approval. See [SECURITY.md](../SECURITY.md) and
[PRIVACY.md](../PRIVACY.md).

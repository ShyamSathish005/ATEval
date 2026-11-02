# Security policy

ATEval is an alpha research preview, not security-certified software.

## Supported versions

Only the current source tree is supported. No release has been published.

## Reporting a vulnerability

Do not post exploit details, unpublished manuscripts, credentials, or personal
data in a public issue. Use the hosting platform's private vulnerability
reporting feature when available. A private contact address has not been
verified yet; establish one before public release.

## Current protections and boundaries

- The native API binds to `127.0.0.1` by default. Non-loopback binding is an
  explicit deployment choice.
- The local application uses exact local origins and same-origin production
  routing; it does not use wildcard credentialed CORS.
- Uploads have a configurable byte limit. LaTeX ZIP imports enforce file-count,
  expanded-size, path traversal, duplicate-path, and symlink checks.
- Analysis does not compile LaTeX, execute shell commands from documents, or
  write over source manuscripts. Review exports create a separate artifact.
- Do not expose the local API on a public network. A public demonstration must
  disable arbitrary uploads and stateful user data until an independent
  security/privacy review and public-mode implementation are complete.
- Public issue trackers are not a confidential reporting channel.

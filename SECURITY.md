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
- The local application uses exact local origins (`localhost`, `127.0.0.1`,
  `tauri://localhost`), strict `Host` header validation, cross-site mutation
  rejection (`Sec-Fetch-Site`, `Referer`, and simple HTML form content-types),
  and per-launch token authentication (`X-ATEval-Token`).
- Forwarded IP headers (`X-Forwarded-For`) are ignored unless the immediate peer
  is in `ATEVAL_TRUSTED_PROXIES` and `ATEVAL_TRUSTED_PROXY_HOPS > 0`. In-memory
  rate-limit buckets are bounded via LRU eviction (`ATEVAL_PUBLIC_RATE_LIMIT_MAX_BUCKETS`)
  and apply per worker process.
- Uploads have a configurable byte limit. Both LaTeX ZIP projects and DOCX
  packages enforce streaming decompression byte counting, compression-ratio
  caps, file-count caps, path traversal/backslash/drive rejection, duplicate
  path checks, and symlink rejection.
- Exported manuscripts and HTML reports use RFC 6266 / RFC 5987 attachment
  headers, `X-Content-Type-Options: nosniff`, and restrictive sandboxed
  `Content-Security-Policy` headers.
- Revision intent models use a declarative JSON schema
  (`ateval-declarative-linear-model-v1`) verified by SHA-256 manifest and
  optional build-pinned digest rather than `pickle`/`joblib` deserialization.
- Analysis does not compile LaTeX, execute shell commands from documents, or
  write over source manuscripts. Review exports create a separate artifact.
- Do not expose the local API on a public network. A public demonstration must
  keep `ATEVAL_PUBLIC_DEMO=1` to disable arbitrary uploads and stateful user
  data. Automated regression tests do not substitute for an external security
  certification.
- Public issue trackers are not a confidential reporting channel.

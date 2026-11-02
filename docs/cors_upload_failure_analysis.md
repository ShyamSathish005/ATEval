# Manuscript upload failure analysis

## Root cause

The upload error was a backend policy rejection that the browser surfaced as a CORS failure. The Vite UI was running at `http://127.0.0.1:5174` and its `/api` proxy forwarded requests to the local FastAPI process on `http://127.0.0.1:8001`. The FastAPI `local_origin_guard` accepted only origin ports `5173`, `4173`, and `8000`. It returned HTTP 403 with `Cross-origin requests are not allowed.` before the upload handler ran. That custom response did not contain CORS headers, so browser JavaScript could not read the response body.

The backend log showed `POST /api/v1/manuscripts/analyze` with status `403 Forbidden` for the failed attempts. Browser DevTools showed the app page at port `5174` and the manuscript analysis request path. This identified an origin allowlist mismatch rather than a malformed manuscript or missing multipart parser. The request already used `FormData`; the browser, not the application, sets the multipart boundary.

The macOS file chooser also disabled `.tex` files because its type mapping is `text/x-tex`, which was not included in the upload input's original `accept` types. The upload filter now includes the TeX MIME types and generic text MIME family. The backend still strictly checks supported file extensions, so this does not expand accepted server formats.

## Changes made

- `ateval/api.py`: explicit local CORS origins, methods, and request headers; CORS middleware wraps local-origin rejection responses; same-origin local API requests are accepted on configured loopback server ports; the API serves the built local SPA and its assets for same-origin production use; oversized manuscripts return 413; uploaded filenames are reduced to a basename.
- `frontend/vite.config.mjs`: Vite development and preview `/api` proxies target the configurable local API and strip the browser `Origin` header because browser-to-Vite requests are same-origin.
- `frontend/src/services/api.ts`: `uploadFile` sends a browser-created `FormData` body with no manual multipart Content-Type, displays progress, and applies a three-minute request timeout with readable errors.
- `frontend/src/App.tsx`: keeps the relative `/api/v1` route, adds a 25 MiB client-side size check and compatible TeX MIME filters.
- `frontend/tests/api-routing.test.mjs`, `frontend/package.json`: tests development and production-preview proxy routing and Origin stripping.
- `tests/test_api.py`: covers CORS/preflight, supported uploads, malformed and oversized requests, parser errors, and same-origin built-frontend/API serving.
- `README.md`: documents local production serving and clarifies that the Sites worker is static-only.

## Origins and security

Observed during verification:

- Development UI: `http://127.0.0.1:5174`
- Development FastAPI: `http://127.0.0.1:8001`
- Local packaged build verification: `http://127.0.0.1:8002` serving UI and API from one origin.

Configured explicit CORS origins are `http://localhost` and `http://127.0.0.1` at ports `5173`, `5174`, and `4173`, matching the Vite development and preview surfaces. `ATEVAL_CORS_ORIGINS` can replace this exact allowlist for a deliberately configured local frontend. No wildcard or `null` origin is accepted. Credentials are disabled. Allowed request headers are limited to `Content-Type`; no application authentication header is used. Allowed methods are `GET`, `POST`, `DELETE`, and `OPTIONS`, matching implemented routes. The default CLI bind remains `127.0.0.1`; the host guard rejects non-local host names. Manuscript bytes are not written to logs or stored by analysis.

The Vite proxy prevents cross-origin browser requests in normal development and preview. Direct browser access to the API receives CORS headers only for the exact configured local origins. The built local application is served by FastAPI from `frontend/dist/client` and uses relative API paths. The Sites worker remains a static host and does not proxy manuscript data to any external service.

## Validation status

The upload flow is confirmed through the application UI in development and through the built local production application. See [upload integration test report](upload_integration_test_report.md) for exact requests, parser results, original-file hashes, and suite results.

# Manuscript upload integration test report

## Result

The upload workflow was exercised in the running application, not only through API tests. A `.tex` manuscript completed analysis in the development UI, and a complete LaTeX project ZIP completed analysis in the built local production application. The imported originals were not modified.

## Browser-to-parser verification

| Application | Browser origin | API route | Input | Observed result |
|---|---|---|---|---|
| Development UI | `http://127.0.0.1:5174` | Relative `/api/v1/manuscripts/analyze`, Vite proxy to `http://127.0.0.1:8001` | `cors-smoke.tex` | UI displayed “Manuscript analyzed”; report contained 26 words and 2 source-mapped passages. FastAPI logged `POST /api/v1/manuscripts/analyze` with `200 OK`. |
| Built local production UI | `http://127.0.0.1:8002` | Same-origin `/api/v1/manuscripts/analyze` | `cors-smoke-project.zip` | UI displayed “Manuscript analyzed”, format ZIP, recursive LaTeX root/include projection, and passages mapped to `sections/introduction.tex`. FastAPI logged `200 OK`. |

The production browser also loaded the built application and its assets from port 8002 before posting the upload. The ZIP contained a root `.tex`, a nested included section, a BibTeX file, and a figure. Analysis resolved the included section and retained project paths. The subsequent UI “Re-analyze source” action again returned `200 OK`.

The browser file chooser initially omitted `.tex` because macOS reports it as `text/x-tex`. After adding the TeX MIME values to the existing picker filter, the actual `.tex` file was selectable and uploaded. The browser generated the multipart boundary; frontend code does not set the multipart `Content-Type` manually.

## Original-file integrity

SHA-256 values were measured before the repeat production analysis and again after the analysis workflow. They matched:

| Test input | SHA-256 |
|---|---|
| `cors-smoke.tex` | `afe66949a9e06eb92a751663477173647816ecfaf4c407c9291391b4d57813d7` |
| `cors-smoke-project.zip` | `7ba19e37040c7a75083c6ebe6327bfca4c2bd32c7eebefc34db91739f366c6bf` |

Analysis operates on the uploaded byte stream and does not write back to the selected source. ZIP extraction and source projection preserve the uploaded archive as the original.

## Automated checks

Executed on 2026-11-02:

- `PYTHONPATH=. pytest -q` — **71 passed, 2 skipped, 7 subtests passed** (8 dependency/deprecation warnings).
- `cd frontend && npm run test:sites` — **6 passed**. Includes development and production-preview proxy routing, `Origin` stripping, and static packaged-site routing checks.
- `cd frontend && npm run build` — completed successfully before the production browser run; the resulting `frontend/dist/client` was served by FastAPI on port 8002.

The API tests cover an allowed Vite-origin preflight, rejection of untrusted and `null` origins, `.tex` multipart parsing, `.docx` and PDF handling, unsupported extensions, malformed multipart, uploads above 25 MiB, parser exceptions, CORS headers on trusted-origin error responses, and built-frontend/API same-origin serving. An untrusted origin is rejected without an `Access-Control-Allow-Origin` header, as required. A trusted origin receives the CORS header on application errors, including 413 and 503 responses.

DOCX and PyMuPDF were not installed in this environment. Their automated cases therefore verified the explicit optional-dependency response (503); successful DOCX and PDF extraction was not verified here. PDF remains dependent on reliable text extraction and is not included in the successful browser upload claims.

## Runtime and security configuration

- Development frontend: `http://127.0.0.1:5174` in the observed run. Vite forwards relative `/api` calls to the local API (`ATEVAL_API_ORIGIN`, default `http://127.0.0.1:8000`) and strips the browser `Origin` header from that same-origin proxy request.
- FastAPI development API used for the observed run: `http://127.0.0.1:8001`.
- Built local application: `http://127.0.0.1:8002`; frontend assets and API share the origin.
- Default allowlist: exact loopback origins at ports 5173, 5174, and 4173 for both `localhost` and `127.0.0.1`. Same-origin production serving needs no CORS entry. `ATEVAL_CORS_ORIGINS` can replace the list with an explicit comma-separated list. The API does not allow wildcard or `null` origins and does not enable credentials.
- Allowed methods are `GET`, `POST`, `DELETE`, and `OPTIONS`; only `Content-Type` is allowed as a request header. The application has no upload Authorization header.
- The CLI binds to `127.0.0.1` by default. The local-origin guard restricts host headers to loopback/local hostnames. The upload limit is 25 MiB, and client-side size validation provides early feedback.
- File names are normalized to a basename before parsing; server-side format validation remains authoritative. Manuscript content is not written to request logs. Analysis does not overwrite or persist original manuscripts.
- The separately packaged Sites output is static and has no API proxy. Unpublished manuscripts should be analyzed with the local FastAPI application, not uploaded to a hosted static deployment.

## Temporary fixture cleanup

The `.tex`, `.txt`, and ZIP files used for the manual browser workflow were local test fixtures and have been removed from the workspace after the integrity check. No manuscript service outside the local machine was used.

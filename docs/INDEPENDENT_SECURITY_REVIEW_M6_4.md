# M6.4 independent security and privacy review

**Reviewer status:** Separate read-only reviewer; not the implementation agent.  
**Scope:** Loopback binding, uploads and ZIP handling, temporary files,
browser storage, manuscript logging, Ollama configuration, CORS, secrets,
Docker exposure, dependency configuration, and export integrity.

## Finding

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| 1 | MEDIUM | `ateval/manuscript_analysis/documents.py` | Windows-style ZIP member paths such as `..\\outside.tex` were accepted by POSIX-only validation and could escape a target directory when extracted on Windows. | Fixed and regression-tested |

The implementation now rejects backslashes, Windows absolute paths, drive
letters, and Windows parent-directory components before storing ZIP members.
The existing POSIX checks remain in place.

## Reviewed controls

The reviewer found no additional high or critical issue in the reviewed
scope. Loopback defaults, explicit CORS allowlisting, non-root Docker
execution, temporary-file cleanup, browser-session storage, manuscript
logging boundaries, and absence of hardcoded secrets were reviewed. The API
health probe now applies the same loopback URL validation as the generation
adapter.

This review is not an approval for a hosted confidential-manuscript service.
The alpha remains local-first and does not offer public confidential uploads.

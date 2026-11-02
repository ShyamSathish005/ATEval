# ATEval v0.1.0-alpha — release notes draft

**Status: unreleased.** This draft is not an announcement of a published
release. The release is blocked by the items in
[release checklist](release_checklist.md).

This alpha consolidates the local-first research workspace, source-mapped
manuscript inspection, descriptive writing diagnostics, and review-required
academic editing experiments. It includes no detector implementation and
makes no authorship or misconduct determination.

## Installation options prepared

- Native Python and frontend installation with no model-weight downloads.
- Docker Compose for a loopback-only local app with persistent local state.
- A separate Render configuration for a public synthetic-only demo. The demo
  rejects uploads and writes, limits API calls, and has no persistent disk.

## Security and privacy notes

The local upload limit defaults to 25 MiB and is configurable. The API binds
to loopback by default. LaTeX ZIP checks reject traversal paths, symbolic
links, duplicate paths, excessive file counts, and large expanded contents.
The public preview accepts only a built-in synthetic sample. The Docker image
does not contain research datasets, fitted models, reviewer annotations, or
user manuscripts.

## Known gaps

The Apache-2.0 license change awaits ownership verification. The current root
license is MIT and remains unchanged. The ATEval directory is not an isolated
Git repository, and the parent remote/history belongs to a different app.
Docker, clean OS installs, CI dependency audits, and independent privacy/
security review have not passed. The intended release tag has not been created.

## Scientific limitations

This is not production-ready or scientifically validated. The classifier is
weak, academic edits require author review, and structural checks do not prove
semantic equivalence. AI-writing detector algorithms are unavailable.

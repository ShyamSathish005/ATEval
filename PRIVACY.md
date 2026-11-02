# Privacy and manuscript handling

ATEval is designed for local-first research. Native local mode binds its API
to loopback and processes manuscript uploads in the local process. The
manuscript analysis route reads the uploaded bytes for parsing and does not
save the original manuscript. Routine application logs should contain request
metadata only, never manuscript bodies.

Local workspace state under `.ateval/` may contain imported research datasets,
metadata, analysis reports, and accepted edit snippets. Treat that directory
as private research data. It is not automatically deleted. Back it up or
remove it according to the institution's retention policy. The API's existing
database and audit features may store metadata and snippets; they are not a
zero-retention service.

The Docker Compose setup stores application state in the named `ateval-data`
volume and uses an ephemeral, no-execute `/tmp`. Removing the container does
not remove the named volume. Delete that volume explicitly when the user
chooses to remove local state.

Do not submit confidential, unpublished, personal, or restricted manuscripts
to a public demonstration. No public demonstration may accept arbitrary
manuscripts before an independent security and privacy review. Model runtimes
are optional; do not configure a remote inference URL with private documents.
ATEval telemetry is not implemented. Dependencies may perform package-manager
network access during installation.

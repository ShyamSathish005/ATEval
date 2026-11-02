# Troubleshooting

## Browser reports a CORS error

Use the frontend Vite proxy during development or serve the built frontend
from FastAPI at `http://127.0.0.1:8000`. Do not set multipart `Content-Type`
manually. See [upload failure analysis](cors_upload_failure_analysis.md).

## API is unavailable

Run `python -m ateval doctor`, then start `python -m ateval api`. Check that
port 8000 is available. The default service binds only to `127.0.0.1`.

## Upload rejected

Check the supported extension and configured `ATEVAL_UPLOAD_LIMIT_BYTES`.
LaTeX ZIP projects must have one identifiable root `.tex`, safe relative
paths, no symlinks or duplicate paths, at most 2,000 files, and at most 100
MiB expanded contents. PDF needs a reliable text layer; DOCX/PDF parsers are
optional native dependencies.

## Optional model is unavailable

Run `ateval doctor`. Model packages, Ollama, and model weights are separate
optional components. ATEval does not automatically download weights. Verify
licenses and configure the model service to use loopback before passing
research text to it.

## Docker data retention

Application state remains in the named `ateval-data` volume after container
removal. Inspect and remove that volume only when its contents are no longer
needed.

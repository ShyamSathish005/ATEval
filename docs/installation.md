# Installation

ATEval is an alpha research preview. Initial installation does not download
large language models or research datasets. Python 3.11 or newer is required.

## Native Python installation

From the ATEval project directory:

```sh
python -m venv .venv
# macOS/Linux:
. .venv/bin/activate
# Windows PowerShell:
# .venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[ui-server,writing-docs]"
python -m ateval doctor
```

Start the local API with `python -m ateval api`. It binds to loopback at port
8000 by default. In another shell, build and run the frontend:

```sh
cd frontend
npm ci
npm run build
cd ..
python -m ateval api
```

Open `http://127.0.0.1:8000` for the built same-origin application. For UI
development use `cd frontend && npm run dev`; Vite's proxy targets the local
API. Keep the API loopback-bound.

## Docker Compose

Install Docker Desktop or Docker Engine with the Compose plugin, then run:

```sh
docker compose -f compose.yaml up --build
```

Open `http://127.0.0.1:8000`. Compose maps the service only to host loopback,
runs the container as a non-root user with a read-only root filesystem, and
stores local state in the named `ateval-data` volume. The initial build does
not fetch model weights or datasets. To change the port or request byte limit,
set `ATEVAL_PORT` or `ATEVAL_UPLOAD_LIMIT_BYTES` before starting Compose.

## Optional capabilities

- DOCX and text-layer PDF ingestion: installed by `writing-docs`; PDF is
  read-only and extraction quality varies.
- Classical revision baselines: `python -m pip install -e '.[revision-ml]'`.
- Transformer experiments: `python -m pip install -e '.[revision-transformer]'`.
  This installs frameworks but not checkpoints. Model acquisition is explicit,
  requires internet access, and can require several gigabytes.
- Generation with XtraGPT: install and license the chosen model locally and
  configure the optional local Ollama endpoint. No model is downloaded by
  ATEval's default install.
- LaTeX compilation is not performed by manuscript analysis. Installing
  `latexmk` or `pdflatex` enables only the separate LaTeX workspace tools.

The public repository is available at
`https://github.com/ShyamSathish005/ATEval`. Release publication remains
blocked until the release checklist and readiness report show that ownership,
installation, and security gates are cleared.

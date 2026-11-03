# Installation

ATEval v0.1.0-alpha.1 is an alpha research preview. The supported initial
configuration is macOS with Python 3.11+, Node.js 22+, and a user-managed
loopback Ollama installation. Installation does not download language models
or research datasets.

## Automated desktop setup (one-click)

To automate environment creation, dependency installation, frontend compilation, and server startup:

The portable launchers are retained for experimentation, but Linux, Windows,
and Docker Compose have not had clean lifecycle verification and are not
supported by this alpha.

The launcher verifies prerequisites, configures `.venv`, installs `ui-server` and `writing-docs` extras, builds the web interface, runs `ateval doctor`, and starts the workspace on `http://127.0.0.1:8000`.

## Common desktop installation hurdles and mitigations

- **Python Version Mismatch**: System `python` on macOS and Linux distributions may point to Python 3.9 or 3.10. ATEval requires `>= 3.11`. Ensure Python 3.11+ is installed via python.org, Homebrew (`brew install python@3.12`), or your Linux package manager.
- **Windows PowerShell Execution Policy**: Windows may restrict script execution (`Activate.ps1`). `launch.bat` bypasses PowerShell script execution restrictions by running directly via batch or using `.venv\Scripts\python.exe` directly.
- **Node.js / npm Availability**: Node.js 20 or 22 is required to compile the client workspace under `frontend/`. If `npm` is missing, the API still runs for CLI operations, but the UI cannot be built.
- **Port Conflicts**: Port `8000` is the default. If port `8000` is in use by another application, set `ATEVAL_PORT=8080` prior to running the launcher or `python -m ateval api`.

## macOS quick install

The supported M6.2 path is macOS with Python 3.11+, Node.js 22+, and npm:

```sh
./scripts/install_macos.sh
./scripts/run_ateval.sh
```

Open `http://127.0.0.1:8000`. The installer creates `.venv`, installs local
document support, builds the frontend, and runs `ateval doctor`. It does not
install model weights or modify system packages.

## Manual Python installation

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

## Docker Compose (unverified)

Docker image builds are covered by CI, but Docker Compose startup, upload,
shutdown, and volume cleanup were not verified in the release environment.
Do not treat this path as supported. If testing it independently, install
Docker Desktop or Docker Engine with the Compose plugin, then run:

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

# ATEval Desktop Application Architecture

## 1. Architectural Overview

ATEval Desktop delivers an installable native desktop experience for academic manuscript evaluation and revision while strictly preserving the existing Python FastAPI backend and React 19 / Vite frontend.

```
+-------------------------------------------------------------------------+
|                              ATEval Desktop                             |
|                                                                         |
|  +--------------------------------+   +-------------------------------+ |
|  |     Tauri v2 Native Host       |   |       WebView Frontend        | |
|  |           (Rust)               |   |      (React 19 + Vite)        | |
|  |                                |   |                               | |
|  |  * Native window & menu        |   |  * Academic Revision UI       | |
|  |  * Process lifecycle watchdog  |   |  * Document diff inspection   | |
|  |  * Ephemeral token generator   |   |  * Edit acceptance/rejection  | |
|  |  * Handshake parser            |   |  * LaTeX / HTML export        | |
|  +---------------+----------------+   +---------------+---------------+ |
|                  |                                    |                 |
|                  | Spawn child                        | HTTP / JSON     |
|                  | Pipe stdin (watchdog)              | (127.0.0.1:P)   |
|                  v                                    v                 |
|  +--------------------------------------------------------------------+ |
|  |                Python Desktop Sidecar (FastAPI)                    | |
|  |             `src-tauri/binaries/ateval-api-<triple>`               | |
|  |                                                                    | |
|  |  * Pre-bound loopback socket (port 0 -> eliminates port collisions)| |
|  |  * Readiness handshake emission to stdout                         | |
|  |  * Token authentication guard (`X-ATEval-Token`)                   | |
|  |  * Stdin EOF watchdog thread (instant graceful termination)        | |
|  |  * Document ingestion, parsing (TeX, DOCX, MD, TXT, PDF)           | |
|  |  * SCAR claim preservation & sentence span tracking                | |
|  +-----------------------------------+--------------------------------+ |
|                                      |                                  |
+--------------------------------------|----------------------------------+
                                       | HTTP (127.0.0.1:11434)
                                       v
                     +-----------------------------------+
                     |       Local Ollama Engine         |
                     |  `ateval-xtragpt-1_5b-q8_0` /     |
                     |  `llama3.2:3b`                    |
                     +-----------------------------------+
```

---

## 2. Core Components

### 2.1 Tauri v2 Host (`src-tauri/`)
- **Native Windowing**: Configured in `tauri.conf.json` with standard 1280x850 window, minimum 960x640 bounds, and macOS native menus (Cmd+C, Cmd+V, Cmd+Q, etc.).
- **Process Orchestration (`src-tauri/src/lib.rs`)**:
  - Generates a 32-byte cryptographically secure per-launch hex token.
  - Spawns the packaged `ateval-api` sidecar with dynamic port parameter `--port 0`.
  - Parses the JSON readiness handshake from stdout: `{"event": "ready", "protocol_version": "1.0", "host": "127.0.0.1", "port": <port>, "pid": <pid>}`.
  - Exposes the Tauri command `get_backend_connection()` returning connection details to the webview.
  - Monitors child lifecycle and closes stdin / kills child upon window closure or application exit.
- **Least-Privilege IPC (`src-tauri/capabilities/default.json`)**:
  - Exposes only `core:default`.
  - Disallows all dangerous shell capabilities (`shell:allow-execute`, `shell:allow-spawn`) from the webview.

### 2.2 Python Sidecar (`ateval/desktop_sidecar.py`)
- **Port Race Prevention**: Instead of guessing an open port, calls `socket.socket(socket.AF_INET, socket.SOCK_STREAM)` with `bind(("127.0.0.1", 0))`, extracts the OS-assigned ephemeral port, and passes the open socket directly to `uvicorn.Server.run(sockets=[sock])`.
- **Readiness Handshake**: Emits standard versioned JSON to stdout upon socket readiness.
- **Stdin Watchdog**: A background daemon thread reads standard input. When the parent Tauri process closes the pipe (on termination or crash), the sidecar shuts down cleanly within 1 second.
- **Authentication**: Validates that all non-health incoming requests present the per-launch `X-ATEval-Token`.

### 2.3 React 19 Frontend (`frontend/src/`)
- **Desktop Detection**: Detects Tauri via `initDesktopConnection()` in `frontend/src/services/api.ts`.
- **Dynamic Routing**: Configures the base URL to `http://127.0.0.1:<port>` and attaches `X-ATEval-Token` on all API and export requests.
- **First-Run Onboarding Modal**: Provides guided setup showing backend status, local Ollama connectivity, model command guidance, and interactive diagnostic checks without forcing multi-gigabyte automatic downloads.

---

## 3. Technology Choices & Tradeoffs

| Choice | Selected | Alternative | Rationale |
| :--- | :--- | :--- | :--- |
| **Desktop Shell** | Tauri v2 + Rust | Electron | Tauri produces ~15-20 MB native bundles using OS WebViews (WebKit on macOS), consuming ~40 MB RAM compared to Electron's 200+ MB Chromium overhead. |
| **Sidecar Packaging** | PyInstaller `--onefile` | PyInstaller `--onedir` | Tauri's `externalBin` bundle mechanism expects a single binary matching the target triple. `--onefile` packages all dependencies into a standalone binary in `src-tauri/binaries/` with zero loose DLLs or path collisions. |
| **Port Allocation** | Pre-bound Socket (`port 0`) | Port scanning loop | Scanning for an unused port introduces a TOCTOU race condition where another process can grab the port before uvicorn binds. Passing the already-bound socket to uvicorn eliminates the race entirely. |
| **Model Inference** | Local Ollama Loopback | Bundled PyTorch/GGUF | Bundling PyTorch and model weights bloats the installer by 4-15 GB and causes platform incompatibilities. Connecting to local Ollama on loopback ensures lightweight (~230 MB total) desktop distribution while keeping all LLM computation strictly local. |

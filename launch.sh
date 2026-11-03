#!/usr/bin/env bash
# ATEval desktop automated launcher (Linux / macOS)
# Sets up virtual environment, installs dependencies, builds frontend,
# runs system diagnostics, and launches the local API & UI workspace.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== ATEval Desktop Launcher ==="

# 1. Check Python (>= 3.11 required)
PYTHON_BIN=""
for candidate in python3.13 python3.12 python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >/dev/null 2>&1; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "Error: Python 3.11 or newer is required to run ATEval."
    echo "Please install Python 3.11+ from https://www.python.org/ or your system package manager."
    exit 1
fi

echo "[1/5] Using Python: $($PYTHON_BIN --version) ($PYTHON_BIN)"

# 2. Check Node.js and npm
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
    echo "Node.js/npm not found; using the packaged frontend when available."
    echo "Please install Node.js (v20 or v22 recommended) from https://nodejs.org/"
fi

# 3. Setup Virtual Environment
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[2/5] Creating virtual environment at $VENV_DIR..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
else
    echo "[2/5] Existing virtual environment found at $VENV_DIR."
fi

# Activate virtual environment
if [ -f "$VENV_DIR/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
fi

# 4. Install Dependencies
echo "[3/5] Checking and installing Python dependencies..."
python -m pip install --upgrade pip --quiet
python -m pip install -e ".[ui-server,writing-docs]" --quiet

# 5. Build Frontend if needed
if [ ! -f "frontend/dist/client/index.html" ] && [ ! -f "ateval/static/index.html" ]; then
    if command -v npm >/dev/null 2>&1; then
        echo "[4/5] Building frontend application..."
        (cd frontend && npm ci && npm run build)
    else
        echo "Warning: frontend/dist/client/index.html not found and npm is unavailable."
    fi
else
    echo "[4/5] Frontend production build present."
fi

# 6. Run Doctor Check
echo "[5/5] Running doctor checks..."
python -m ateval doctor || true

# 7. Start Workspace Server
PORT="${ATEVAL_PORT:-8000}"
echo ""
echo "=========================================================="
echo " Starting ATEval local workspace at http://127.0.0.1:${PORT}"
echo " Press Ctrl+C to stop the server."
echo "=========================================================="
echo ""

# Launch browser if supported and DISPLAY / desktop session is active
if [ -n "${DISPLAY:-}" ] || [ "$(uname -s)" = "Darwin" ]; then
    (
        sleep 2
        if command -v open >/dev/null 2>&1; then
            open "http://127.0.0.1:${PORT}" 2>/dev/null || true
        elif command -v xdg-open >/dev/null 2>&1; then
            xdg-open "http://127.0.0.1:${PORT}" 2>/dev/null || true
        fi
    ) &
fi

exec python -m ateval api

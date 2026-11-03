#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  printf 'This installer targets macOS. Use docs/INSTALLATION.md for Linux and Windows.\n' >&2
  exit 1
fi

command -v python3 >/dev/null 2>&1 || {
  printf 'Python 3 is required. Install Python 3.11+ from https://www.python.org/downloads/macos/ or Homebrew.\n' >&2
  exit 1
}
command -v npm >/dev/null 2>&1 || {
  printf 'Node.js and npm are required. Install Node.js 22+ from https://nodejs.org/ or Homebrew.\n' >&2
  exit 1
}

python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11 or newer is required.")
PY

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[ui-server,writing-docs]'

(
  cd frontend
  npm ci
  npm run build
)

.venv/bin/python -m ateval doctor
printf '\nATEval is installed. Start it with:\n  ./scripts/run_ateval.sh\n'

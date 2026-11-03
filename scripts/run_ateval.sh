#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -x .venv/bin/python ]]; then
  printf 'ATEval is not installed. Run ./scripts/install_macos.sh first.\n' >&2
  exit 1
fi
if [[ ! -f frontend/dist/client/index.html ]]; then
  printf 'The frontend is not built. Run ./scripts/install_macos.sh or build it with: (cd frontend && npm run build)\n' >&2
  exit 1
fi

export ATEVAL_HOST=127.0.0.1
exec .venv/bin/python -m ateval api --host 127.0.0.1 --port "${ATEVAL_PORT:-8000}"

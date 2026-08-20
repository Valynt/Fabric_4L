#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$SCRIPT_DIR/../../../.venv/bin/python"
if [ -f "$VENV_PY" ]; then
  exec "$VENV_PY" "$@"
else
  exec python3 "$@"
fi

#!/usr/bin/env bash
set -euo pipefail

cd /workspace/Fabric_4L
if [[ -e .env ]]; then
  echo "ERROR: .env already exists; refusing to overwrite it." >&2
  exit 1
fi
cp -- .env.example .env
chmod 0600 .env
echo "Created gitignored .env from .env.example by explicit request. Review it before use."
echo "Run with: DEVCONTAINER_ENV_FILE=.env .devcontainer/dev-stack.sh <command>"

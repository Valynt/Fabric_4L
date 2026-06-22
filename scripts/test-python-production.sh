#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/test-python-production.sh [--mandatory-only|--full|--collect-only]

Production Python test profile for H-04.

Prerequisites:
  pip install -r tests/requirements-test.txt
  docker compose -f infra/compose/docker-compose.test.yml up -d postgres redis neo4j keycloak

Modes:
  --mandatory-only  Run mandatory unit/contract/security tests only.
  --full            Run the full repository Python suite, including infra-gated tests.
  --collect-only    Collect the full repository suite without executing tests.
USAGE
}

mode="--mandatory-only"
if [[ $# -gt 1 ]]; then
  usage >&2
  exit 2
fi
if [[ $# -eq 1 ]]; then
  mode="$1"
fi

case "$mode" in
  --mandatory-only)
    exec pytest -m "mandatory" --strict-markers
    ;;
  --full)
    exec pytest --strict-markers
    ;;
  --collect-only)
    exec pytest --collect-only -q --strict-markers
    ;;
  -h|--help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

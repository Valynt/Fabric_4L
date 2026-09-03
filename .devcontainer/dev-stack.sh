#!/usr/bin/env bash
set -euo pipefail

readonly workspace=/workspace/Fabric_4L
readonly prod_compose=infra/compose/docker-compose.prod.yml
readonly full_compose=infra/compose/docker-compose.full.yml
readonly cloud_override=.devcontainer/docker-compose.cloud.yml
readonly infisical_paths=(
  --path=/shared --path=/infra
  --path=/layer1-ingestion --path=/layer2-extraction
  --path=/layer2-5-signal-refinery --path=/layer3-knowledge
  --path=/layer4-agents --path=/layer5-ground-truth
  --path=/layer6-benchmarks
  --path=/apps/web
)

cd "$workspace"

usage() {
  cat <<'EOF'
Usage: .devcontainer/dev-stack.sh COMMAND

Commands:
  infra       Start PostgreSQL, Redis, and Neo4j from the production topology
  full        Start the full canonical production-parity topology
  migrate     Run repository migrations explicitly
  frontend    Start the frontend-only Vite server on port 3001
  down        Stop the production-parity development project
  config      Render the production-parity Compose configuration
  help        Show this help

Infisical is required by default and injects secrets into child processes only.
For the explicit legacy workflow, first run .devcontainer/legacy-env.sh and then
set DEVCONTAINER_ENV_FILE=.env for the requested command.
EOF
}

run_with_secrets() {
  local -a paths=("${infisical_paths[@]}")
  while [[ "${1:-}" == --path=* ]]; do
    paths=("$1" "${paths[@]}")
    shift
  done

  if [[ -n "${DEVCONTAINER_ENV_FILE:-}" ]]; then
    [[ -f "$DEVCONTAINER_ENV_FILE" ]] || {
      echo "ERROR: DEVCONTAINER_ENV_FILE does not exist: $DEVCONTAINER_ENV_FILE" >&2
      exit 1
    }
    set -a
    # shellcheck disable=SC1090
    source "$DEVCONTAINER_ENV_FILE"
    set +a
    "$@"
    return
  fi

  command -v infisical >/dev/null 2>&1 || {
    echo "ERROR: Infisical CLI is unavailable. Install/login, or explicitly opt into .devcontainer/legacy-env.sh." >&2
    exit 1
  }
  infisical run --env=dev "${paths[@]}" -- "$@"
}

compose_prod=(docker compose --project-directory "$workspace/infra/compose" -p fabric4l-cloud -f "$prod_compose" -f "$cloud_override")
compose_full=(docker compose --project-directory "$workspace/infra/compose" -p fabric4l-cloud -f "$full_compose" -f "$cloud_override")

case "${1:-help}" in
  infra)
    run_with_secrets "${compose_prod[@]}" up -d --wait postgres redis neo4j
    ;;
  full)
    run_with_secrets "${compose_full[@]}" up -d --build --wait
    ;;
  migrate)
    run_with_secrets make migrate
    ;;
  frontend)
    run_with_secrets --path=/shared --path=/apps/web pnpm --dir apps/web run dev --host 0.0.0.0 --port 3001
    ;;
  down) run_with_secrets "${compose_full[@]}" down --remove-orphans ;;
  config) run_with_secrets "${compose_full[@]}" config ;;
  help|-h|--help) usage ;;
  *) echo "ERROR: unknown command: $1" >&2; usage >&2; exit 2 ;;
esac

#!/usr/bin/env bash
set -euo pipefail

cd /workspace/Fabric_4L

if docker info >/dev/null 2>&1; then
  docker_status=ready
else
  docker_status="not ready; inspect: docker compose -f .devcontainer/docker-compose.yml logs docker"
fi

printf 'Value Fabric Dev Container started (Docker: %s).\n' "$docker_status"
cat <<'EOF'
Nothing was migrated or started automatically.
  .devcontainer/dev-stack.sh infra     # lightweight data infrastructure
  .devcontainer/dev-stack.sh full      # production-parity stack
  .devcontainer/dev-stack.sh migrate   # explicit migrations
  .devcontainer/dev-stack.sh frontend  # Vite on port 3001
EOF

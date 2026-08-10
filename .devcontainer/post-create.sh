#!/usr/bin/env bash
set -euo pipefail

readonly workspace=/workspace/Fabric_4L
cd "$workspace"

echo "Configuring the pinned JavaScript toolchain..."
sudo corepack enable
corepack prepare pnpm@10.18.1 --activate

echo "Installing workspace dependencies from the frozen lockfile..."
pnpm install --frozen-lockfile

echo "Installing Python service dependencies through the canonical Make target..."
make setup

cat <<'EOF'

Dev Container bootstrap complete. No secrets, migrations, or services were started.
See docs/development/DEV_CONTAINERS.md or run:
  .devcontainer/dev-stack.sh help
EOF

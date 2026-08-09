#!/bin/bash
# Post-create script for devcontainer setup

set -e

echo "Setting up Value Fabric development environment..."

cd /workspace

# Enable corepack and activate pinned pnpm version
corepack enable
corepack prepare pnpm@10.18.1 --activate

# Install frontend dependencies
echo "Installing frontend dependencies..."
pnpm --dir apps/web install --frozen-lockfile

# Install Python dependencies for all layers via make setup
echo "Installing Python service dependencies..."
if command -v pipx &>/dev/null; then
    pipx install pytest 2>/dev/null || true
fi
make setup

# Set up pre-commit hooks if pre-commit is available
if command -v pre-commit &>/dev/null; then
    echo "Setting up pre-commit hooks..."
    pre-commit install
fi

# Make scripts executable
chmod +x scripts/*.sh 2>/dev/null || true

echo ""
echo "Development environment setup complete!"
echo ""
echo "Quick start commands:"
echo "  pnpm env:dev && docker compose -f docker-compose.dev.yml --env-file .env.generated up  # Start full stack"
echo "  pnpm dev:web                  # Start frontend only (mock API, port 3001)"
echo "  make test                     # Run all backend tests"
echo "  make lint                     # Run linting"
echo "  make verify                   # Full verification gate"
echo ""

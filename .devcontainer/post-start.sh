#!/bin/bash
# Post-start script - runs each time the container starts

set -e

echo "🚀 Devcontainer started!"

# Check if docker daemon is accessible
if docker info &>/dev/null; then
    echo "✅ Docker-in-Docker is ready"
else
    echo "⚠️  Docker daemon not yet available (this is normal on first start)"
fi

# Display current branch and status
cd /workspace
if [ -d ".git" ]; then
    echo ""
    echo "📁 Repository status:"
    git status -sb 2>/dev/null || true
fi

echo ""
echo "💡 Tip: Run 'make dev-up' to start the development services"

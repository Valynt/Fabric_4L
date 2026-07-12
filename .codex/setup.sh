#!/bin/bash
# Codex setup script for Unix/macOS/Linux
# This script runs automatically when Codex creates a new worktree

set -e

echo "→ Setting up Value Fabric environment..."

# Enable corepack and activate the repo-pinned pnpm version
echo "→ Enabling corepack and activating pnpm@10.34.5..."
corepack enable
corepack use pnpm@10.34.5

# Install JavaScript/TypeScript dependencies
echo "→ Installing dependencies with pnpm..."
pnpm install --frozen-lockfile

# Check if .env exists, if not copy from example
if [ ! -f .env ]; then
  echo "→ Creating .env from example..."
  cp .env.example .env
  echo "⚠️  Please fill in .env with your secrets (OPENAI_API_KEY, JWT_SECRET, etc.)"
fi

echo "✅ Setup complete"

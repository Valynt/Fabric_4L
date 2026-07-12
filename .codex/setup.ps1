# Codex setup script for Windows
# This script runs automatically when Codex creates a new worktree

Write-Host "→ Setting up Value Fabric environment..."

# Enable corepack and activate the repo-pinned pnpm version
Write-Host "→ Enabling corepack and activating pnpm@10.34.5..."
corepack enable
corepack use pnpm@10.34.5

# Install JavaScript/TypeScript dependencies
Write-Host "→ Installing dependencies with pnpm..."
pnpm install --frozen-lockfile

# Check if .env exists, if not copy from example
if (-not (Test-Path .env)) {
  Write-Host "→ Creating .env from example..."
  Copy-Item .env.example .env
  Write-Host "⚠️  Please fill in .env with your secrets (OPENAI_API_KEY, JWT_SECRET, etc.)"
}

Write-Host "✅ Setup complete"

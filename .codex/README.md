# Codex Workspace Bridge

This folder documents how Codex should interpret the repository's existing `.devin/`
workspace (renamed from `.windsurf/` in commit `342c3249d`) and provides setup scripts and actions for local development.

## Setup Scripts

Codex automatically runs setup scripts when creating a new worktree. This repository includes:

- `setup.sh` - Default setup script for Unix/macOS/Linux
- `setup.ps1` - Windows-specific setup script

These scripts:
- Enable corepack and activate the repo-pinned pnpm version (10.34.5)
- Install JavaScript/TypeScript dependencies with pnpm
- Create `.env` from `.env.example` if it doesn't exist (you'll need to fill in secrets)

## Codex Actions

Configure these actions in the [Codex app settings](codex://settings) for quick access to common tasks:

| Action | Script | Description |
|--------|--------|-------------|
| Start Dev Server | `cd apps/web && pnpm run dev` | Start React frontend dev server (port 5173) |
| Start Full Stack | `docker compose -f docker-compose.dev.yml up -d` | Start all backend services with Docker |
| Stop Services | `docker compose -f docker-compose.dev.yml down` | Stop all Docker Compose services |
| Run Tests | `pnpm run test` | Run all unit tests across the monorepo |
| Run Linting | `pnpm run lint` | Run linting across all packages and services |
| Type Check | `pnpm run typecheck` | Run TypeScript type checking |
| Build Frontend | `pnpm run build` | Build frontend production bundle |
| Generate API Types | `pnpm run generate:api` | Generate TypeScript types from OpenAPI specs |
| Run Migrations | `make migrate` | Run database migrations for all layers |
| View Logs | `docker compose -f docker-compose.dev.yml logs -f` | Tail logs for all Docker services |

## Devin Workspace Mapping

`.devin/` is the project's assistant-runtime source of truth (renamed from `.windsurf/` in
commit `342c3249d`). Codex cannot automatically execute that runtime, but it can use the
files as local project guidance.

### Mapping

- `.devin/AGENTS.md` -> agent roles, boundaries, and task framing reference
- `.devin/CONTEXT.md` -> context assembly and conflict-checking reference
- `.devin/MEMORY.md` -> memory/documentation conventions reference
- `.devin/rules/` -> policy and safety reference
- `.devin/skills/` -> reusable playbook reference
- `.devin/workflows/` -> orchestration playbook reference
- `.devin/mcp/` -> reference manifests only; not automatically active in Codex

### Practical Rule

For Codex sessions in this repo, prefer:

1. Root `AGENTS.md`
2. `packages/platform-contract/CONTRACT.md`
3. Relevant `.devin/` documents for additional local guidance

If these sources conflict, follow the higher item in the list.

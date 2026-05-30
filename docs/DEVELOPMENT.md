# Development Setup Guide

This guide covers local development environment setup for the Value Fabric platform.

## Prerequisites

- Docker ≥ 24.0 and Docker Compose v2
- Python 3.11+ (any patch release; the project does not require Python 3.11.10 specifically)
- Node.js ≥ 22.12.0 (for frontend / tooling)
- `make` (optional but recommended)

## Quick Start

Python tooling resolves `python3.11` first when available, then falls back to `python3`/`python`. For pyenv, the root `.python-version` intentionally contains `3.11` so `pyenv local 3.11` can select the latest installed 3.11 patch instead of forcing one brittle patch version.

```bash
# Optional for pyenv users
pyenv install --skip-existing "$(pyenv latest -k 3.11)"
pyenv local 3.11

# Start core dev services (Postgres, Redis, Neo4j)
make up
# or
docker compose -f docker-compose.dev.yml up -d
```

## Environment Variables

Copy `.env.example` to `.env` and adjust for your machine:

```bash
cp .env.example .env
```

### Required Variables

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | See `.env.example` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `NEO4J_URI` | Neo4j Bolt URI | `bolt://localhost:7687` |

## Vault (HashiCorp) – Dev Mode

The file `docker-compose.full.dev-vault.yml` starts Vault in **dev mode** for
local secret management.  Dev mode is intentionally insecure and should
**never** be used outside of a local developer workstation.

### Vault Root Token

The Vault dev root token is controlled by the `VAULT_DEV_ROOT_TOKEN_ID`
environment variable:

```bash
# .env
VAULT_DEV_ROOT_TOKEN_ID=my-local-dev-token
```

If the variable is not set it defaults to `root`, which is a well-known value
and **must not** be used in any shared or long-lived environment (CI, staging,
production).

**Best practice:** Set `VAULT_DEV_ROOT_TOKEN_ID` to a random token in your
personal `.env`:

```bash
# Generate a random token
python3 -c "import secrets; print(secrets.token_hex(16))"
# Add to .env
echo "VAULT_DEV_ROOT_TOKEN_ID=<generated-token>" >> .env
```

Then start Vault:

```bash
docker compose -f docker-compose.full.dev-vault.yml --profile local-dev up -d vault
```

### Vault in CI and Staging

- CI uses mock secret backends — Vault dev mode is not started.
- Staging uses production-mode Vault with TLS and auto-unseal; see
  `docs/secrets-management.md` and `k8s/base/vault/` for configuration.

## Running Tests

```bash
# Run all unit tests from repo root
pytest

# Run billing service tests
cd services/billing
pip install -e ".[dev]"
pytest
```

## Linting and Formatting

```bash
# Python
ruff check .
black --check .

# Frontend
pnpm lint
```

## Useful Make Targets

```bash
make up        # Start all dev services
make down      # Stop all dev services
make logs      # Tail service logs
make test      # Run unit tests
make lint      # Run all linters
```

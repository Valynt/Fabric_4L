# GitHub Codespaces Guide

Get a fully configured Fabric 4L development environment running in under 5 minutes — zero local setup required.

---

## One-Click Launch

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/bmsull560/Fabric_4L)

Click the badge above, select your machine type (recommended: 4-core), and Codespaces will:

1. Provision a container with Python 3.11, Node 22, Docker, and the GitHub CLI
2. Install all Python and Node.js dependencies
3. Start PostgreSQL, Neo4j, and Redis via Docker Compose
4. Apply all database migrations
5. Copy `.env.example` to `.env`

**Expected startup time:** 3–5 minutes on a 4-core machine.

---

## Post-Launch Validation

Once the terminal shows the post-create commands have finished, run:

```bash
make verify
```

This should pass completely. If all checks are green, your environment is ready for development.

**What `make verify` validates:**

| Check | Tool | Expected Result |
|-------|------|-----------------|
| Unit & integration tests | pytest | All pass |
| Type safety | mypy + tsc | Zero errors |
| Lint | ruff + eslint | Clean |
| Contract tests | custom runner | All ratified |

---

## Available Services

After startup, the following services are forwarded and accessible:

| Port | Service | Description |
|------|---------|-------------|
| 5173 | Frontend | React dev server |
| 8001 | Layer 1: Ingestion | Document intake API |
| 8002 | Layer 2: Extraction | Entity extraction API |
| 8003 | Layer 3: Knowledge | Knowledge graph API |
| 8004 | Layer 4: Agents | Agent runtime API |
| 8005 | Layer 5: Ground Truth | Validation workflows API |
| 8006 | Layer 6: Benchmarks | Benchmarking API |
| 5432 | PostgreSQL | Relational database with RLS |
| 6379 | Redis | Cache and job queues |
| 7474 | Neo4j Browser | Graph database UI |

---

## Troubleshooting

### Issue 1: Docker Compose fails to start services

**Symptoms:** `postStartCommand` exits with an error about Docker daemon not being available.

**Resolution:**

```bash
# Wait a few seconds for Docker-in-Docker to initialize, then retry:
docker compose -f infra/compose/docker-compose.dev.yml up -d
make migrate
```

If the issue persists, restart the Codespace from the command palette (`Codespaces: Rebuild Container`).

---

### Issue 2: `make verify` fails with database connection errors

**Symptoms:** Tests fail with `ConnectionRefusedError` to PostgreSQL or Neo4j.

**Resolution:**

```bash
# Check that services are running:
docker compose -f infra/compose/docker-compose.dev.yml ps

# If any service shows as exited, restart:
docker compose -f infra/compose/docker-compose.dev.yml restart

# Re-run migrations after services are healthy:
make migrate
make verify
```

---

### Issue 3: Port already in use / forwarding conflicts

**Symptoms:** VS Code shows "Port 5xxx is already in use" or forwarded ports are unreachable.

**Resolution:**

```bash
# Check what is listening on the conflicting port:
lsof -i :5173

# If a stale process is holding the port, kill it:
kill -9 <PID>

# Or restart the dev server on an alternative port:
cd apps/web && pnpm dev --port 5174
```

You can also reload the window (`Developer: Reload Window`) to reset port forwarding.

---

## Need Help?

- Open an issue in the [Fabric_4L repository](https://github.com/bmsull560/Fabric_4L/issues)
- Check the [CONTRIBUTING.md](CONTRIBUTING.md) guide for development workflows
- See the [docs/](docs/) directory for architecture deep-dives and runbooks

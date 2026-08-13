---
title: "Dev Containers and Cloud Workspaces"
category: "how-to"
audience: "contributors"
last-reviewed: "2026-08-09"
freshness: "current"
related: ["./BUILD_SYSTEM", "./COMMANDS", "../../.devcontainer/devcontainer.json"]
---

# Dev Containers and Cloud Workspaces

The repository has one Dev Container topology for cloud-provider-neutral hosted
workspaces. It builds the `dev` service from `.devcontainer/Dockerfile`, mounts
the repository at `/workspace/Fabric_4L`, and connects to a separate rootless
Docker daemon. The default topology never mounts the host Docker socket.

## Create or rebuild the container

Open the repository in a Dev Container client and choose **Rebuild Container**.
From a host with the Dev Container CLI, the equivalent commands are:

```bash
devcontainer up --workspace-folder .
devcontainer exec --workspace-folder . bash
```

`post-create.sh` activates pnpm 10.18.1, runs
`pnpm install --frozen-lockfile`, and runs `make setup`. Re-running it is safe.
It does not create environment files, start services, or run migrations.
`post-start.sh` is informational and does not mutate the workspace or databases.

## Secrets

Infisical process injection is the default. Authenticate once in the container:

```bash
infisical login
.devcontainer/dev-stack.sh infra
```

Stack commands fail with an actionable error when the Infisical CLI or session
is unavailable. They do not silently fall back to placeholder credentials or
write an exported secret file. Credentials are never copied into the image.

The legacy `.env` workflow is opt-in only:

```bash
.devcontainer/legacy-env.sh
# Review the new, gitignored file before use.
DEVCONTAINER_ENV_FILE=.env .devcontainer/dev-stack.sh infra
```

The helper refuses to overwrite an existing `.env`. Delete the file yourself
when it is no longer required.

## Explicit startup workflows

Nothing starts automatically. Choose the smallest workflow needed:

| Workflow | Command | Behavior |
|---|---|---|
| Lightweight infrastructure | `.devcontainer/dev-stack.sh infra` | Starts canonical PostgreSQL, Redis, and Neo4j definitions and waits for health. |
| Full production parity | `.devcontainer/dev-stack.sh full` | Merges `docker-compose.full.yml` with the cloud development override, then builds and waits. |
| Migrations | `.devcontainer/dev-stack.sh migrate` | Runs `make migrate` explicitly. Run after infrastructure is healthy. |
| Frontend only | `.devcontainer/dev-stack.sh frontend` | Runs Vite on `0.0.0.0:3001`; backend calls use the frontend's configured mock behavior. |
| Stop the cloud stack | `.devcontainer/dev-stack.sh down` | Stops the `fabric4l-cloud` project without deleting named volumes. |

The cloud override contains development-only resource/log bounds and dependency
conditions. PostgreSQL, Redis, and Neo4j remain defined exclusively by the
canonical production/full Compose files.

## Ports and visibility

The editor forwards frontend port `3001`, application ports `8001` through
`8006`, and Layer 2.5 Signal Refinery on `8007`. Dev Container clients decide
whether forwarded ports are private, organization-visible, or public; keep them
private unless a test explicitly requires broader access. Database and Docker
daemon ports are not forwarded by the Dev Container configuration. Never expose
Docker TCP port `2375` outside the internal Compose network.

## Persistence and disk use

Named volumes retain Docker daemon state, pnpm downloads, pip downloads, and
canonical service data across ordinary container restarts. Logs rotate at
10 MiB with three files per container, and cloud services have bounded CPU and
memory. The rootless daemon uses the portable `vfs` driver, which consumes more
disk than production overlay storage. Recover space by removing unused build
state deliberately:

```bash
docker system df
docker builder prune
```

To erase only the Dev Container daemon and dependency caches, stop the Dev
Container project from the host and remove its named volumes. To erase
application data, run `.devcontainer/dev-stack.sh down` and then explicitly
remove the `fabric4l-cloud` project volumes. These operations are destructive
and are intentionally not automated.

## Local host-socket override

The safer sidecar is always the default. A trusted local workstation may opt
into the host socket by adding the named override explicitly:

```json
"dockerComposeFile": [
  "docker-compose.yml",
  "docker-compose.local-socket.yml"
]
```

Do not commit that personal edit. A host socket grants the container control of
the host Docker daemon and is not supported in hosted cloud workspaces.

## Recovery

1. If Docker is unavailable, inspect the sidecar from the host with
   `docker compose -f .devcontainer/docker-compose.yml logs docker` and rebuild.
2. If dependency bootstrap was interrupted, rerun `.devcontainer/post-create.sh`.
   The script is idempotent and skips the pnpm activation step when pnpm is
   already on `PATH`.
3. If Infisical authentication expired, run `infisical login`; do not create an
   untracked environment file unless deliberately choosing the legacy flow.
4. If service health checks fail, inspect the canonical stack with
   `docker compose -p fabric4l-cloud -f infra/compose/docker-compose.full.yml -f .devcontainer/docker-compose.cloud.yml -f .devcontainer/docker-compose.cloud.full.yml ps`.
5. Remove named volumes only when data loss is acceptable.

## Known differences from production

- The editor and Docker daemon are development-only services.
- Source is bind-mounted for editing; production uses immutable images.
- Cloud resource limits are deliberately smaller than production sizing.
- Docker uses rootless `vfs` storage for portability rather than the production
  host's storage driver.
- Ports are forwarded by the workspace client instead of a production ingress.
- Infisical uses the `dev` environment, and local-safe credentials may be used.
- Migrations, backups, scaling, TLS termination, and the complete stack are not
  started automatically.

Validate changes with:

```bash
python scripts/ci/check_devcontainer_config.py
```

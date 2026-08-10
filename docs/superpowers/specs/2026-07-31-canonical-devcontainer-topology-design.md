# Canonical Dev Container Topology Design

## Objective

Replace the independent and permissive `.devcontainer/` configuration with one
deterministic topology that works in hosted cloud workspaces and remains usable
for explicit local development. The topology must reuse the repository's
canonical Compose definitions, install dependencies through repository-owned
commands, avoid automatic secret persistence, and be statically enforceable in
CI.

## Architecture

The Dev Container attaches to a `dev` service built from
`.devcontainer/Dockerfile` with the repository root as its build context. The
workspace is mounted at `/workspace/Fabric_4L`, and lifecycle hooks call the
checked-in `post-create.sh` and `post-start.sh` scripts. The editor container
runs as the non-root `vscode` user with all capabilities dropped and
`no-new-privileges` enabled.

Hosted environments use a dedicated Docker-in-Docker sidecar. The editor
container reaches it over an internal network through `DOCKER_HOST`; it does
not run privileged and does not mount the host Docker socket. A separately
named local-only override may replace this connection with
`/var/run/docker.sock`, but that override is never selected by default.

Application and infrastructure startup is separate from the editor lifecycle.
Cloud development commands layer a development override onto the canonical
`infra/compose/docker-compose.prod.yml` or
`infra/compose/docker-compose.full.yml`. The override may change bind mounts,
hot reload, debugging, safe local credentials, published ports, and resource
limits, but it does not independently redefine PostgreSQL, Redis, or Neo4j.

## Deterministic Toolchain

The Dockerfile base image and every Dev Container feature are referenced by
OCI digest. The lock file contains exactly the features declared by
`devcontainer.json`. The resulting amd64 and arm64 environment provides Python
3.11, Node.js 22.12 or newer, pnpm 10.18.1, Docker CLI and Compose, GitHub CLI,
Infisical CLI, kubectl, kustomize, cosign, build tools, and the repository's
Python/bootstrap prerequisites.

Downloaded architecture-specific tools use explicit version pins and checksum
verification. No credential or generated environment file is copied into an
image layer.

## Lifecycle and Secrets

`post-create.sh` is the only dependency/bootstrap entrypoint. It is idempotent,
activates pnpm 10.18.1, runs `pnpm install --frozen-lockfile`, and runs
`make setup`. It does not mask failures, create `.env`, modify broad file sets,
run migrations, or start application services.

`post-start.sh` is non-destructive. It reports Docker availability and points
to explicit startup commands without changing repository or database state.

Infisical injection is the default secrets workflow. Commands that need
secrets first verify that the CLI and credentials are available, then generate
the gitignored `.env.generated` only for the requested operation. Missing
credentials produce a clear failure without falling back to insecure defaults.
The legacy `.env` path requires an explicit opt-in command that copies
`.env.example`; automatic lifecycle hooks never invoke it.

## Startup Profiles and Runtime Safety

Documented scripts or tasks expose four deliberate workflows:

1. Lightweight infrastructure: start only required data and identity services.
2. Full production parity: start the canonical full stack with the development
   override.
3. Migrations: run `make migrate` explicitly after infrastructure is healthy.
4. Frontend only: run the Vite development server on canonical port 3001.

Optional application services depend on healthy PostgreSQL, Redis, and Neo4j
where they use those stores. Stateful services and development caches use named
volumes. Cloud overrides apply bounded CPU and memory, rotated logs, and
bounded/replaceable Docker daemon storage appropriate to ephemeral workspaces.
Only required application ports are exposed or forwarded; the frontend is
forwarded and labelled on port 3001.

## Validation and Documentation

A static CI validator performs Dev Container configuration validation and
`docker compose config` for every supported base/profile/override combination.
Repository assertions verify:

- digest-pinned images and features;
- lock/config feature agreement;
- the required Python, Node.js, and pnpm versions;
- non-root editor execution and hardened container options;
- absence of committed secret material and automatic `.env` creation;
- health checks and valid `service_healthy` dependencies;
- canonical frontend port 3001;
- no default host Docker socket mount; and
- reuse of canonical PostgreSQL, Redis, and Neo4j definitions.

The CI workflow runs the validator as a required configuration check. A
cloud-provider-neutral guide under `docs/development/` describes rebuilds,
startup profiles, Infisical and legacy secrets, volume persistence, port
visibility, recovery, and intentional differences from production. The build
system documentation links to that guide.

## Scope and Compatibility

This change does not alter application API contracts, tenant behavior,
database schemas, or production deployment defaults. It changes development
orchestration and its CI contract only. Existing local users who require the
host Docker socket must opt into the named local-only override.

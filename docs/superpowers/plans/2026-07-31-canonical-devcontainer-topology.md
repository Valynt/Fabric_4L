# Canonical Dev Container Topology Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one secure, deterministic Dev Container topology backed by canonical repository Compose definitions and enforced by CI.

**Architecture:** A non-root editor container connects to a Docker-in-Docker sidecar by default, while an explicitly selected local override provides host-socket access. Repository scripts own lifecycle and startup behavior, and cloud application stacks merge canonical production/full Compose files with a development-only override.

**Tech Stack:** Dev Container specification, Docker Compose, Bash, Python 3.11, Node.js 22.18.0, pnpm 10.18.1, GitHub Actions.

## Global Constraints

- Use `/workspace/Fabric_4L` as the workspace path and `dev` as the Dev Container service.
- Pin the base image and all Dev Container features by SHA-256 digest.
- Support native linux/amd64 and linux/arm64 tooling.
- Never persist secrets automatically or mount the host Docker socket by default.
- Keep lifecycle hooks non-destructive; migrations and stacks are explicit operations.
- Reuse `infra/compose/docker-compose.prod.yml` and `infra/compose/docker-compose.full.yml` for application and infrastructure definitions.

---

### Task 1: Add the static contract first

**Files:**
- Create: `scripts/ci/check_devcontainer_config.py`
- Create: `tests/ci/test_devcontainer_config.py`

**Interfaces:**
- Consumes: JSON, Dockerfile, shell, and Compose files under `.devcontainer/`.
- Produces: `python scripts/ci/check_devcontainer_config.py [--skip-cli-validation]`, returning zero only when every topology invariant and rendered Compose combination is valid.

- [ ] Write unit tests using temporary repositories for digest pins, feature-lock parity, non-root execution, port 3001, health dependencies, secret safety, and default socket absence.
- [ ] Run `python -m pytest tests/ci/test_devcontainer_config.py -q` and confirm the current topology fails contract cases.
- [ ] Implement a focused validator with deterministic error messages and optional external Dev Container CLI execution.
- [ ] Run `python -m pytest tests/ci/test_devcontainer_config.py -q` and confirm it passes.

### Task 2: Build the canonical editor and Docker topology

**Files:**
- Modify: `.devcontainer/devcontainer.json`
- Modify: `.devcontainer/devcontainer-lock.json`
- Modify: `.devcontainer/Dockerfile`
- Modify: `.devcontainer/docker-compose.yml`
- Create: `.devcontainer/docker-compose.local-socket.yml`

**Interfaces:**
- Consumes: repository root build context and pinned Dev Container features.
- Produces: `dev` editor service at `/workspace/Fabric_4L`, default sidecar Docker connection, and explicit local socket override.

- [ ] Change `devcontainer.json` to select `.devcontainer/docker-compose.yml`, `service: dev`, the canonical workspace, checked-in lifecycle scripts, and port 3001.
- [ ] Align the feature lock to the exact digest-addressed features in the configuration.
- [ ] Make the Dockerfile multi-architecture, version/checksum pinned, and non-secret-bearing.
- [ ] Replace duplicated databases with the hardened `dev` and Docker sidecar services, named caches, bounded logs/resources, and no default socket.
- [ ] Add the explicitly named local-only socket override.
- [ ] Run the static validator in CLI-skip mode.

### Task 3: Make lifecycle and startup commands explicit

**Files:**
- Modify: `.devcontainer/post-create.sh`
- Modify: `.devcontainer/post-start.sh`
- Create: `.devcontainer/dev-stack.sh`
- Create: `.devcontainer/legacy-env.sh`
- Create: `.devcontainer/docker-compose.cloud.yml`

**Interfaces:**
- Consumes: Infisical authentication, canonical Compose files, and root package/Make targets.
- Produces: idempotent bootstrap plus `infra`, `full`, `migrate`, `frontend`, `down`, and explicit `legacy-env` operations.

- [ ] Make post-create run only Corepack activation, root frozen pnpm installation, and `make setup`, without masked failures.
- [ ] Make post-start report readiness and commands without mutating state.
- [ ] Add a fail-closed Infisical-aware startup dispatcher and an explicit legacy environment opt-in.
- [ ] Add a cloud override limited to development behavior, health-gated application dependencies, bounded resources/logs, and named state/cache volumes.
- [ ] Render every supported canonical/override combination with `docker compose config`.

### Task 4: Document and wire CI enforcement

**Files:**
- Create: `docs/development/DEV_CONTAINERS.md`
- Modify: `docs/development/BUILD_SYSTEM.md`
- Modify: `.github/workflows/pr-checks.yml`

**Interfaces:**
- Consumes: repository scripts and supported topology combinations.
- Produces: provider-neutral operator guidance and a PR check that installs the Dev Container CLI and runs the static validator plus Compose rendering.

- [ ] Document rebuild, profiles, secrets, persistence, ports, recovery, local socket opt-in, and production differences.
- [ ] Link the guide from the canonical build system.
- [ ] Add a digest-pinned GitHub Actions setup and validator step to the Docker Compose configuration job.
- [ ] Run docs checks and workflow/static validation.

### Task 5: Verify and deliver

**Files:**
- Modify only files required by failures found during verification.

**Interfaces:**
- Consumes: completed topology.
- Produces: a clean commit and pull request.

- [ ] Run shell syntax checks, unit tests, the static validator, Dev Container validation, and all Compose renders.
- [ ] Run the narrowest repository governance checks and report any environment-limited checks honestly.
- [ ] Inspect the final diff for secrets, broad changes, and unexpected generated files.
- [ ] Commit with a conventional message and `Co-authored-by: Ona <no-reply@ona.com>`.
- [ ] Create the pull request using the required template sections.

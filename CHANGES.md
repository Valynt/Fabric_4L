# Fabric_4L Dev Environment Hardening & Validation Changes

This document summarizes the audit findings, hardening changes, verified invariants, and deferred items from the development environment validation.

---

## 1. What Was Fixed

1. **Pinned `uv` Toolchain in Dev Container (`.devcontainer/Dockerfile`)**:
   - Added explicit `ARG UV_VERSION=0.11.6`.
   - Installed `uv` via `pipx` globally (`PIPX_BIN_DIR=/usr/local/bin PIPX_HOME=/opt/pipx pipx install uv==${UV_VERSION}`) with an immediate build-step verification (`uv --version`) so Docker builds fail fast if the installation breaks.
   - Eliminates the defect where `uv` was missing from the container toolchain.

2. **Environment Verification Suite (`.devcontainer/verify.sh`)**:
   - Created executable script with `set -euo pipefail`.
   - Formatted, deterministic assertions for all required toolchains:
     - Python 3.11.x
     - Node.js 22.x
     - pnpm
     - uv
     - Docker CLI + Docker Compose
     - Docker daemon / rootless DinD sidecar reachability (`docker info`)
     - kubectl (client)
     - kustomize
     - cosign
     - Infisical CLI
     - GitHub CLI (`gh`)
     - make + jq
   - Returns exit code 0 on health, exit code 1 with specific failure details if broken.

3. **Lifecycle Integration (`.devcontainer/post-create.sh`)**:
   - Wired `.devcontainer/verify.sh` into `post-create.sh` so every fresh container build or rebuild validates the full environment automatically.

4. **Dev Container CI Smoke Test Workflow (`.github/workflows/devcontainer-smoke.yml`)**:
   - Added GitHub Actions workflow using `devcontainers/ci@v0.3` running on pull requests and main pushes touching `.devcontainer/**`.
   - Executes `bash .devcontainer/verify.sh` to ensure the devcontainer image builds and passes health checks from scratch.
   - Updated and validated the CI workflow registry (`scripts/ci/verify_workflow_registry.py`, `workflow-registry.json`, `WORKFLOW_REGISTRY.md`).

5. **Nebius Host Infrastructure Bootstrap (`infra/nebius/cloud-init.yaml` & `infra/nebius/README.md`)**:
   - Created idempotent cloud-init bootstrap for Ubuntu 24.04 LTS on Nebius Cloud.
   - Configures host-level infrastructure: Docker Engine installation, `ubuntu` user in docker group, UFW firewall (default deny incoming, allow SSH), fail2ban, unattended security upgrades, and SSH hardening (disabled password authentication and root login).
   - Strictly host-level: does not install Python/Node on host OS.
   - Provided complete step-by-step setup documentation.

6. **Single Canonical Dev Setup Path in `README.md`**:
   - Updated repo `README.md` to specify `devcontainer up --workspace-folder .` as the single canonical path.
   - Deprecated bare-metal host installation to prevent contributor and AI agent drift.

---

## 2. What Was Already Correct (Preserved)

- **Rootless Docker-in-Docker Sidecar Architecture**:
  - Dev container connects to `DOCKER_HOST=tcp://docker:2375` hosted in an isolated Docker network.
  - No host `/var/run/docker.sock` is ever mounted into the development container.
- **Security Boundaries**:
  - `cap_drop: [ALL]` and `no-new-privileges: true` enforced on services.
  - Non-root `vscode` user (UID 1000) for development tasks.
  - Bounded resource limits (memory and CPU constraints).
- **Tool Version Pinning**:
  - Base container digest-pinned (`mcr.microsoft.com/devcontainers/base@sha256:...`).
  - Docker Compose (`v2.35.1`), kubectl (`v1.29.15`), kustomize (`v5.4.3`), cosign (`v2.4.1`), and Infisical (`0.41.11`) pinned to exact versions.
  - Python (`3.11`), Node.js (`22.18.0`), and pnpm (`10.18.1`) digest-pinned in devcontainer features.
- **Hook Idempotence**:
  - `post-create.sh` and `post-start.sh` use `set -euo pipefail` and do not mutate production databases or write unversioned credentials.

---

## 3. Issues Noted but Deferred (With Reasons)

1. **Terraform for Nebius Infrastructure**:
   - **Reason**: Single VM / early cluster setups are simpler, more maintainable, and less prone to state drift with idempotent cloud-init. Terraform is deferred until multi-VM or automated VPC management is needed.
2. **TLS on DinD Docker Socket (`tcp://docker:2375` vs `2376`)**:
   - **Reason**: The DinD daemon runs on an internal, isolated Docker bridge network (`devcontainer`) not exposed to host ports. Adding TLS certificates adds complexity with minimal security gain for single-user devcontainers; deferred until multi-tenant network sharing is introduced.
3. **Binary Download Checksum Verification (SHA256)**:
   - **Reason**: Upstream releases for kubectl, kustomize, cosign, and Infisical are fetched from official GitHub release URLs with exact version tags over HTTPS. Adding inline sha256 checksum arrays can be added in a future supply-chain hardening sweep without affecting current functionality.

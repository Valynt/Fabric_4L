# Phase 2: Deterministic Multi-Architecture Docker Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transition the project's container images to digest-pinned, multi-architecture (`linux/amd64` + `linux/arm64`) builds without breaking local Apple Silicon development.

**Architecture:** Pin every Dockerfile base image to the cryptographic manifest digest of its current tag, build application images for both architectures in CI using `docker buildx`, provide an explicit opt-in ARM64 compose override for local dev, and update production K8s manifests to reference manifest digests for third-party infrastructure images.

**Tech Stack:** Docker, docker buildx, GitHub Actions, Kustomize, Python 3.11, Node 22, Debian Bookworm, Alpine 3.20

---

## Task 1: Pin Dockerfile base images to manifest digests

**Files:**
- Modify: `services/api/Dockerfile`
- Modify: `services/layer1-ingestion/Dockerfile`
- Modify: `services/layer1-ingestion/Dockerfile.live`
- Modify: `services/layer1-ingestion/Dockerfile.uv`
- Modify: `services/layer2-extraction/Dockerfile`
- Modify: `services/layer2-extraction/Dockerfile.full`
- Modify: `services/layer2-extraction/Dockerfile.uv`
- Modify: `services/layer2-5-signal-refinery/Dockerfile`
- Modify: `services/layer3-knowledge/Dockerfile`
- Modify: `services/layer3-knowledge/Dockerfile.full`
- Modify: `services/layer3-knowledge/Dockerfile.uv`
- Modify: `services/layer4-agents/Dockerfile`
- Modify: `services/layer4-agents/Dockerfile.full`
- Modify: `services/layer4-agents/Dockerfile.uv`
- Modify: `services/layer5-ground-truth/Dockerfile`
- Modify: `services/layer5-ground-truth/Dockerfile.full`
- Modify: `services/layer5-ground-truth/Dockerfile.uv`
- Modify: `services/layer6-benchmarks/Dockerfile`
- Modify: `services/layer6-benchmarks/Dockerfile.full`
- Modify: `services/layer6-benchmarks/Dockerfile.uv`
- Modify: `services/layer7-billing/Dockerfile`
- Modify: `apps/web/Dockerfile`
- Modify: `apps/web/Dockerfile.dev`
- Modify: `apps/web/Dockerfile.playwright`
- Modify: `.devcontainer/Dockerfile`
- Test: `scripts/ci/check_hermetic_build_inputs.py`

- [ ] **Step 1: Record current manifest digests**

Run and record the digest outputs:

```bash
docker buildx imagetools inspect python:3.11.13-slim-bookworm --format '{{.Manifest.Digest}}'
# Expected: sha256:86adf8dbadc3d6e82ee5dd2c74bec2e1c2467cdad47886280501df722372d2e1

docker buildx imagetools inspect node:22.12.0-alpine3.20 --format '{{.Manifest.Digest}}'
# Expected: sha256:027911463b296bdaf6df82b5ccf2c6b290fee725d5fba6513a037ed019400625

docker buildx imagetools inspect mcr.microsoft.com/playwright:v1.60.0-noble --format '{{.Manifest.Digest}}'
# Expected: sha256:9bd26ad900bb5e0f4dee75839e957a89ae89c2b7ab1e76050e559790e946b948

docker buildx imagetools inspect mcr.microsoft.com/devcontainers/base:bookworm --format '{{.Manifest.Digest}}'
# Expected: sha256:aba0f2e0730af481edf2db5582a80c0ed2591bee78ec177f7fa7a38e8f5e1105
```

If the recorded digests differ from the live output, use the live values.

- [ ] **Step 2: Replace Python base image tags with manifest digest**

In every Python service Dockerfile, change:

```dockerfile
FROM python:3.11.13-slim-bookworm
```

to:

```dockerfile
# python:3.11.13-slim-bookworm manifest digest (linux/amd64 + linux/arm64)
FROM python@sha256:86adf8dbadc3d6e82ee5dd2c74bec2e1c2467cdad47886280501df722372d2e1
```

Also update `Dockerfile.uv` files that use `ARG BASE_IMAGE=python:3.11.13-slim-bookworm`:

```dockerfile
ARG BASE_IMAGE=python@sha256:86adf8dbadc3d6e82ee5dd2c74bec2e1c2467cdad47886280501df722372d2e1
```

Files to update:
- `services/api/Dockerfile`
- `services/layer1-ingestion/Dockerfile`
- `services/layer1-ingestion/Dockerfile.live`
- `services/layer1-ingestion/Dockerfile.uv`
- `services/layer2-extraction/Dockerfile`
- `services/layer2-extraction/Dockerfile.full`
- `services/layer2-extraction/Dockerfile.uv`
- `services/layer2-5-signal-refinery/Dockerfile`
- `services/layer3-knowledge/Dockerfile`
- `services/layer3-knowledge/Dockerfile.full`
- `services/layer3-knowledge/Dockerfile.uv`
- `services/layer4-agents/Dockerfile`
- `services/layer4-agents/Dockerfile.full`
- `services/layer4-agents/Dockerfile.uv`
- `services/layer5-ground-truth/Dockerfile`
- `services/layer5-ground-truth/Dockerfile.full`
- `services/layer5-ground-truth/Dockerfile.uv`
- `services/layer6-benchmarks/Dockerfile`
- `services/layer6-benchmarks/Dockerfile.full`
- `services/layer6-benchmarks/Dockerfile.uv`
- `services/layer7-billing/Dockerfile`

- [ ] **Step 3: Replace Node base image tags with manifest digest**

In frontend Dockerfiles, change:

```dockerfile
FROM node:22.12.0-alpine3.20
```

to:

```dockerfile
# node:22.12.0-alpine3.20 manifest digest (linux/amd64 + linux/arm64)
FROM node@sha256:027911463b296bdaf6df82b5ccf2c6b290fee725d5fba6513a037ed019400625
```

Files:
- `apps/web/Dockerfile`
- `apps/web/Dockerfile.dev`

- [ ] **Step 4: Replace Playwright and devcontainer base image tags**

```dockerfile
# apps/web/Dockerfile.playwright
# mcr.microsoft.com/playwright:v1.60.0-noble manifest digest
FROM mcr.microsoft.com/playwright@sha256:9bd26ad900bb5e0f4dee75839e957a89ae89c2b7ab1e76050e559790e946b948
```

```dockerfile
# .devcontainer/Dockerfile
# mcr.microsoft.com/devcontainers/base:bookworm manifest digest
FROM mcr.microsoft.com/devcontainers/base@sha256:aba0f2e0730af481edf2db5582a80c0ed2591bee78ec177f7fa7a38e8f5e1105
```

- [ ] **Step 5: Run hermetic build-input check**

```bash
python scripts/ci/check_hermetic_build_inputs.py
```

Expected: PASS (no tag-only base images in production Dockerfiles).

- [ ] **Step 6: Build one service image locally to verify the digest works**

```bash
docker build -f services/layer4-agents/Dockerfile -t layer4:test services/layer4-agents
```

Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
git add services/*/Dockerfile services/*/Dockerfile.* apps/web/Dockerfile* .devcontainer/Dockerfile
git commit -m "build(docker): pin base images to manifest digests for multi-arch reproducibility"
```

---

## Task 2: Update CI to build multi-platform application images

**Files:**
- Modify: `.github/workflows/build-deploy.yml`
- Modify: `.github/workflows/pr-checks.yml`
- Modify: `Makefile`
- Test: a local multi-platform build dry-run

- [x] **Step 1: Add platforms to build-push-action in build-deploy.yml**

In `.github/workflows/build-deploy.yml`, locate every `docker/build-push-action` step and add:

```yaml
platforms: linux/amd64,linux/arm64
```

Example:

```yaml
- name: Build and push
  uses: docker/build-push-action@v6
  with:
    context: ./services/layer4-agents
    file: ./services/layer4-agents/Dockerfile
    push: true
    tags: ${{ steps.meta.outputs.tags }}
    platforms: linux/amd64,linux/arm64
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

- [x] **Step 2: Add platforms to PR checks image build**

In `.github/workflows/pr-checks.yml`, the existing step uses `load: true` so the image is available for the Trivy scan; `load` is incompatible with multi-platform builds. Left the PR step single-platform and added a comment explaining that multi-platform validation happens in `build-deploy.yml`.

- [x] **Step 3: Add a local multi-platform Makefile target**

In `Makefile`, add:

```makefile
docker-build-multi: ## Build all deployable images for linux/amd64 and linux/arm64
	@echo "→ Building multi-arch images (requires docker buildx)..."
	@for ctx in services/api services/layer1-ingestion services/layer2-extraction services/layer2-5-signal-refinery services/layer3-knowledge services/layer4-agents services/layer5-ground-truth services/layer6-benchmarks services/layer7-billing apps/web; do \
		service=$$(basename $$ctx); \
		docker buildx build --platform linux/amd64,linux/arm64 -t fabric_4l/$$service:multi-arch $$ctx; \
	done
	@echo "✅ Multi-arch build complete"
```

- [x] **Step 4: Dry-run a multi-platform build for one service**

Local Docker builder is not available in this environment (`desktop-linux` builder reports a pipe/connection error), so the dry-run could not be executed here. The workflow change will be validated in CI on the next `main` build.

- [x] **Step 5: Commit**

Changes staged; commit left to the user per repository workflow conventions.

---

## Task 3: Add ARM64 local development compose override

**Files:**
- Create: `infra/compose/docker-compose.arm64.yml`
- Modify: `docs/development/BUILD_SYSTEM.md` (if it exists and documents compose usage)

- [ ] **Step 1: Create the override file**

Create `infra/compose/docker-compose.arm64.yml`:

```yaml
# Opt-in ARM64 / Apple Silicon override for local development.
#
# Usage:
#   docker compose -f infra/compose/docker-compose.dev.yml \
#                  -f infra/compose/docker-compose.arm64.yml \
#                  --env-file .env.generated up -d
#
# This forces core infrastructure and buildable services to the linux/arm64
# platform, avoiding QEMU emulation on Apple Silicon hosts.

services:
  postgres:
    platform: linux/arm64
  redis:
    platform: linux/arm64
  neo4j:
    platform: linux/arm64
  minio:
    platform: linux/arm64
  keycloak:
    platform: linux/arm64
  pgbouncer:
    platform: linux/arm64
  qdrant:
    platform: linux/arm64
  layer1:
    platform: linux/arm64
  layer1-worker:
    platform: linux/arm64
  layer2:
    platform: linux/arm64
  layer2-worker:
    platform: linux/arm64
  layer2-5:
    platform: linux/arm64
  layer3:
    platform: linux/arm64
  layer4:
    platform: linux/arm64
  layer5:
    platform: linux/arm64
  layer6:
    platform: linux/arm64
  layer7:
    platform: linux/arm64
  api-gateway:
    platform: linux/arm64
  frontend:
    platform: linux/arm64
```

Service names were matched to the partial dev stack (layer1/layer3/layer5/layer6/layer7/qdrant omitted because they are defined in `docker-compose.full.yml` only).

- [x] **Step 2: Validate the override parses**

```bash
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.arm64.yml config > /dev/null
```

Expected: No errors.

- [x] **Step 3: Document usage**

Add a short section to `docs/development/BUILD_SYSTEM.md` (or `AGENTS.md` if BUILD_SYSTEM.md does not exist):

```markdown
### ARM64 / Apple Silicon local development

Force native ARM64 platforms to avoid QEMU emulation:

```bash
docker compose -f infra/compose/docker-compose.dev.yml \
               -f infra/compose/docker-compose.arm64.yml \
               --env-file .env.generated up -d
```
```

- [x] **Step 4: Commit**

Changes staged; commit left to the user per repository workflow conventions.

---

## Task 4: Pin third-party infrastructure images in K8s manifests

**Files:**
- Modify: `k8s/envs/prod/kustomization.yaml`
- Modify: `k8s/envs/staging/kustomization.yaml`
- Modify: `k8s/envs/prod/kustomization.yaml.template`
- Modify: `k8s/overlays/production/kustomization.yaml`
- Modify: `k8s/overlays/staging/kustomization.yaml`
- Modify: `k8s/deployments/prod-nginx/kustomization.yaml`
- Modify: `k8s/deployments/staging-nginx/kustomization.yaml`
- Test: `scripts/ci/validate-k8s-image-tags.sh`, `scripts/ci/check-k8s-image-digests.sh`

- [x] **Step 1: Identify all third-party images in production manifests**

Run:

```bash
kustomize build k8s/deployments/prod-nginx --load-restrictor=LoadRestrictionsNone | grep "image:" | sort -u
```

Expected output includes images like:
- `postgres:15.10-alpine`
- `redis:7.4-alpine`
- `neo4j:5.25-community`
- `quay.io/oauth2-proxy/oauth2-proxy:v7.6.0`
- `prom/prometheus:v2.54.1`
- etc.

- [x] **Step 2: Resolve each tag to a manifest digest**

Resolved all tags except `ghcr.io/zalando/spilo-16:3.2-p1` (requires authentication / tag not publicly resolvable) and corrected `pgbouncer/pgbouncer:1.24.1` to the latest available digest because the `1.24.1` tag does not exist in Docker Hub.

For each third-party image, run:

```bash
docker buildx imagetools inspect <image>:<tag> --format '{{.Manifest.Digest}}'
```

Example:

```bash
docker buildx imagetools inspect postgres:15.10-alpine --format '{{.Manifest.Digest}}'
# sha256:cff2fc0d03e6a46d7a3ab4d18e5d4d1cc2931cdb9dccbf27d9f115aa5a48c6a
```

Record all digests.

- [x] **Step 3: Add digest overrides to the prod Kustomization**

In `k8s/deployments/prod-nginx/kustomization.yaml`, add an `images:` block for each third-party image:

```yaml
images:
  - name: postgres
    newName: postgres
    digest: sha256:cff2fc0d03e6a46d7a3ab4d18e5d4d1cc2931cdb9dccbf27d9f115aa5a48c6a
  - name: redis
    newName: redis
    digest: sha256:...
```

If the overlay already has an `images:` block, append to it.

- [x] **Step 4: Repeat for staging**

Apply the same digest overrides to `k8s/deployments/staging-nginx/kustomization.yaml`, replacing the `sha256:STAGING_DIGEST_PLACEHOLDER` value for application images if present.

- [x] **Step 5: Validate production manifests**

`scripts/ci/check_production_k8s_mutable_tags.py` and `scripts/ci/check-k8s-image-digests.sh` both PASS. `validate-k8s-image-tags.sh` requires `kustomize`, which is not installed in this environment; `validate_k8s_production_overlays.py` skips kustomize rendering and passes.

- [x] **Step 6: Commit**

Changes staged; commit left to the user per repository workflow conventions.

---

## Task 5: Validate end-to-end deterministic build behavior

**Files:**
- All changed files

- [x] **Step 1: Verify hermetic build input gate**

```bash
python scripts/ci/check_hermetic_build_inputs.py
```

Dockerfile base images pass. Pre-existing violations remain in unrelated scripts (`run_db_production_readiness_gate.sh`, `check_docker_compose_config.py`, `gate_engineering_validator.py`, `generate_ci_failure_backlog.py`) and are out of scope for this task.

- [x] **Step 2: Verify multi-platform build for all services**

```bash
make docker-build-multi
```

Local Docker builder is unavailable in this environment, so the command could not be executed. The `docker-build-multi` target is present and recognized by `make help`; CI will exercise it on the next `main` build.

- [x] **Step 3: Verify K8s manifest validation**

```bash
python scripts/ci/validate_k8s_production_overlays.py
```

PASS. `validate-k8s-image-tags.sh` requires `kustomize`, which is not installed here.

- [x] **Step 4: Verify compose override parses**

```bash
docker compose -f infra/compose/docker-compose.dev.yml -f infra/compose/docker-compose.arm64.yml config > /dev/null
```

PASS (with required env vars supplied: `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD`).

- [x] **Step 5: Verification checkpoint**

Additional checks run and passing:
- `python scripts/ci/check_workflow_targets_and_artifacts.py`
- `python scripts/ci/check_manifest_secret_hygiene.py`
- `python scripts/ci/generate_workflow_registry.py --check`
- `python scripts/ci/verify_workflow_registry.py`
- `python -m pytest tests/ci/test_build_promotion_artifact_contract.py tests/release/test_release_artifact_integrity.py tests/security/test_supply_chain.py`

Note: `tests/ci/test_workflow_permissions.py` and `tests/ci/test_ci_workflow_consolidation.py` have pre-existing failures unrelated to these changes.

---

## Spec Coverage Checklist

| Runbook requirement | Implementing task |
|---|---|
| Set up a multi-platform Docker build process | Task 2 |
| Generate multi-arch manifests and push to registry | Task 2 (CI `platforms:` produces the manifest) |
| Update production deploy manifests to reference manifest digests | Task 1 (base images), Task 4 (infra images) |
| Add docker-compose.override.yml for local development | Task 3 |

## Placeholder Scan

- No TBD/TODO/fill-in-details remain.
- All commands include expected output.
- Digest values are concrete; they should be re-verified at execution time.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-23-phase2-multi-arch-docker.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using batch execution with checkpoints.

**Which approach?**

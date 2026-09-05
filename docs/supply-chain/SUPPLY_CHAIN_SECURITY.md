# Secure Software Supply Chain — Architecture & Implementation

> **Status:** Production  
> **Owner:** Platform Engineering / Security Architecture  
> **Last Reviewed:** 2026-04-14  
> **SLSA Target:** Level 3  
> **NIST SSDF Alignment:** PO.1, PS.1, PS.2, PW.1–PW.9, RV.1–RV.3

---

## Table of Contents

1. [Repository Architecture](#1-repository-architecture)
2. [Environment & Reproducibility](#2-environment--reproducibility)
3. [Build System](#3-build-system)
4. [Artifact Packaging](#4-artifact-packaging)
5. [Security Hardening](#5-security-hardening)
6. [Supply Chain Integrity](#6-supply-chain-integrity)
7. [CI/CD Pipeline](#7-cicd-pipeline)
8. [Observability & Verification](#8-observability--verification)
9. [Testing Strategy](#9-testing-strategy)
10. [Production Readiness Checklist](#10-production-readiness-checklist)
11. [Risk Analysis & Roadmap](#11-risk-analysis--roadmap)

---

## 1. Repository Architecture

### Folder Structure

```
Fabric_4L/
├── .devcontainer/             # Reproducible dev environment (VS Code Dev Containers)
├── .github/
│   ├── workflows/             # 10 CI/CD workflows
│   │   ├── build-deploy.yml           # Build → Sign → Attest → Deploy
│   │   ├── codeql.yml                 # CodeQL SAST (Python + JS/TS)
│   │   ├── security-gates.yml         # Trivy, gitleaks, bandit, DAST, SBOM
│   │   ├── pr-checks.yml             # Lint, typecheck, test, contract, release-smoke gates
│   │   ├── integration-tests.yml      # Cross-layer integration
│   │   ├── k8s-readiness.yml         # K8s manifest validation
│   │   ├── performance-load-tests.yml # k6 SLO evaluation
│   │   ├── zero-trust-validation.yml  # Network policy enforcement
│   │   └── publish-sdk.yml           # SDK artifact publication
│   ├── scripts/               # CI helper scripts
│   └── pull_request_template.md
├── contracts/                 # Source of truth for all interfaces
│   ├── openapi/               # Auto-generated OpenAPI specs (do not hand-edit)
│   ├── tool-manifests/        # JSON Schema for agent tools
│   └── jsonschema/            # Shared data model schemas
├── docs/
│   ├── supply-chain/          # This document and related supply chain docs
│   ├── security/              # Threat models, triage
│   ├── compliance/            # Control matrix
│   ├── trust/                 # Trust framework, CVD, vendor risk
│   ├── operations/            # Escalation, KPIs, postmortems
│   ├── runbooks/              # 25+ operational runbooks
│   ├── reliability/           # DR policy
│   └── slo/                   # Performance SLO definitions
├── frontend/                  # React + TypeScript (Vite)
├── k8s/                       # Kubernetes manifests
│   ├── base/                  # Base resources + HPA + PDB + network policies
│   ├── overlays/              # Kustomize overlays (dev, prod)
│   ├── external-secrets/      # HashiCorp Vault integration
│   └── infisical/             # Infisical secrets integration
├── layer4-agents/             # Agent definitions, skills, workflows
├── monitoring/                # Prometheus + Grafana + AlertManager
├── packs/                     # Domain vertical extensions
├── scripts/
│   ├── ci/                    # CI automation (preflight, reproducibility, billing evidence)
│   ├── security/              # Security validation (zero trust, artifact verification)
│   └── smoke/                 # Production smoke tests
├── tests/                     # Cross-layer tests
│   ├── arch/                  # Architecture enforcement
│   ├── contract/              # API contract validation
│   ├── evals/                 # Agent golden-trace evaluations
│   ├── integration/           # Integration regression
│   └── performance/           # k6 load tests
├── value-fabric/              # Backend microservices
│   ├── layer1-ingestion/      # Data ingestion (Playwright, Redis, PostgreSQL)
│   ├── layer2-extraction/     # Ontology extraction (LLM, RDF/OWL)
│   ├── layer3-knowledge/      # Knowledge graph (Neo4j, pgvector)
│   ├── layer4-agents/         # Agent engine (LangGraph)
│   ├── layer5-ground-truth/   # Ground-truth store
│   ├── layer6-benchmarks/     # Benchmark harness
│   └── shared/
│       ├── identity/          # Cross-layer auth (JWT, API keys, RBAC)
│       ├── audit/             # Append-only audit log (DB trigger-enforced)
│       └── testability/       # DI primitives (Clock, IDGenerator, HTTPClient)
├── AGENTS.md                  # Concise agent entry point
├── Architecture.md            # System architecture overview
├── SECURITY.md                # Security policy and vulnerability reporting
└── Makefile                   # 31 automation targets
```

### Required Root Files

| File | Purpose |
|------|---------|
| `AGENTS.md` | Workspace package map and scoped guidance links |
| `Architecture.md` | 6-layer pipeline architecture |
| `SECURITY.md` | Vulnerability reporting, security design principles |
| `CONTRIBUTING.md` | Contribution workflow and standards |
| `CHANGELOG.md` | Release history |
| `.gitattributes` | Line-ending and binary handling |

### Dependency Management Strategy

| Ecosystem | Tool | Lock File | Pinning |
|-----------|------|-----------|---------|
| Python (backend) | pip + pyproject.toml | `requirements.txt` per layer | Hash-pinned in production Dockerfiles |
| Node.js (frontend) | pnpm | `pnpm-lock.yaml` | `--frozen-lockfile` enforced |
| GitHub Actions | version pins | N/A | SHA-pinned (`actions/checkout@v4` = specific SHA) |
| Container base images | Docker | N/A | Tag-pinned (`python:3.11-slim`, `node:20-alpine`) |
| Rust/Cargo | Not used | N/A | Not required; no tracked `Cargo.toml`, `Cargo.lock`, or `.rs` files |

### Versioning Strategy

- **Artifacts:** `sha-<8-char-git-sha>` as primary tag, branch name as secondary
- **API contracts:** Semantic versioning (`/v1/`, `/v2/`) with deprecation policy
- **Deprecations:** Tracked in `docs/deprecation_register.json` with CI enforcement

---

## 2. Environment & Reproducibility

### Local Development Environment

**Tool:** VS Code Dev Containers (`.devcontainer/devcontainer.json`)

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11 | Backend services |
| Node.js | 20 LTS | Frontend, CI tooling |
| Docker-in-Docker | Latest | Container builds |
| kubectl | 1.30 | K8s management |
| Helm | 3.14 | Chart management |
| cosign | 2.4.1 | Artifact signing/verification |
| trivy | Latest | Local vulnerability scanning |

**Environment setup:** `bash .devcontainer/post-create.sh` installs all tools with pinned versions.

### Dependency Pinning Strategy

1. **Python:** `pip install --frozen-lockfile` semantics via `requirements.txt` with hashes
2. **Node.js:** `pnpm install --frozen-lockfile` — any lockfile drift fails CI
3. **Docker:** `PIP_NO_CACHE_DIR=1` prevents non-deterministic pip cache behavior
4. **CI Actions:** All GitHub Actions pinned to major version tags with SHA verification

### Secrets Management

| Secret Type | Storage | Rotation | Access |
|-------------|---------|----------|--------|
| API keys | Infisical / Vault | 90-day rotation | Per-service identity |
| JWT signing keys | K8s ExternalSecret → Vault | 30-day rotation | `shared/identity/` only |
| Database credentials | Vault dynamic secrets | Per-connection lease | Layer-specific |
| CI tokens | GitHub Actions OIDC | Per-run ephemeral | Workflow-scoped |
| Container registry | GitHub OIDC | Per-run ephemeral | Build workflow only |

**Zero hardcoded secrets:** Enforced by gitleaks in CI (`.github/workflows/security-gates.yml`).

### Infrastructure as Code

| Component | Tool | Location |
|-----------|------|----------|
| K8s resources | Kustomize | `k8s/base/`, `k8s/overlays/` |
| Secret injection | External Secrets Operator | `k8s/external-secrets/` |
| Monitoring | Prometheus + Grafana config | `monitoring/` |
| Network policies | K8s NetworkPolicy | `k8s/base/network-policies/` |

### Environment Drift Prevention

1. **Dev Containers** ensure identical local environments across all developers
2. **Frozen lockfiles** in CI reject any uncommitted dependency changes
3. **Kustomize overlays** enforce environment-specific config without manual edits
4. **`make check-env`** validates all env vars against Zod schemas before deploy

---

## 3. Build System

### Build Tooling

| Service | Build Tool | Runtime |
|---------|-----------|---------|
| Backend (L1–L6) | Docker multi-stage | `python:3.11-slim` |
| Frontend | Vite + Docker multi-stage | `node:20-alpine` |
| K8s manifests | Kustomize | N/A |
| CI orchestration | GitHub Actions | Ubuntu latest |

### Build Isolation Strategy

1. **Docker BuildKit** — All builds use BuildKit with layer caching
2. **No host dependencies** — Builds run entirely inside Docker; no host toolchain leaks
3. **Non-root builds** — Builder stages install deps; runtime stages run as `appuser`/`node`
4. **Network isolation** — Build stages do not have access to production secrets

### Caching Strategy

| Cache Type | Mechanism | TTL |
|-----------|-----------|-----|
| Docker layers | GitHub Actions cache (`type=gha`) | Per-branch, max mode |
| pip packages | `PIP_NO_CACHE_DIR=1` in Docker (deterministic) | None |
| pnpm store | `--frozen-lockfile` from lockfile | Per-lockfile hash |
| Build artifacts | `actions/cache@v4` | 7 days |

### Parallelization

- **Matrix builds** — All 7 services (6 layers + frontend) build in parallel
- **Parallel security scans** — Trivy, bandit, pip-audit run as parallel matrix jobs
- **Independent test suites** — Each layer's tests run independently

### Hermetic Build Principles

1. All inputs are version-locked (lockfiles, base image tags)
2. No network access during application build steps (deps pre-installed)
3. `PIP_NO_CACHE_DIR=1` and `PIP_DISABLE_PIP_VERSION_CHECK=1` eliminate pip non-determinism
4. `PYTHONDONTWRITEBYTECODE=1` prevents `.pyc` file timestamp variance
5. Build reproducibility verified via `scripts/ci/build-reproducibility-check.sh`

---

## 4. Artifact Packaging

### Artifact Types

| Artifact | Format | Registry |
|----------|--------|----------|
| Backend services (L1–L6) | OCI container images | `ghcr.io/bmsull560/fabric_4l/<layer>` |
| Frontend | OCI container image | `ghcr.io/bmsull560/fabric_4l/frontend` |
| Python SDK | PyPI package | GitHub Packages / PyPI |
| SBOMs | CycloneDX JSON | GitHub Actions artifacts (30-day retention) |
| Security evidence | SARIF + JSON | GitHub Actions artifacts (30-day retention) |

### Naming / Versioning Conventions

```
ghcr.io/bmsull560/fabric_4l/<layer>:sha-<8-char>     # Immutable (primary)
ghcr.io/bmsull560/fabric_4l/<layer>:<branch-name>     # Mutable (branch tracking)
ghcr.io/bmsull560/fabric_4l/<layer>:latest             # Optional (workflow_dispatch)
```

### Image Hardening

| Control | Implementation |
|---------|---------------|
| Minimal base images | `python:3.11-slim`, `node:20-alpine` |
| No dev dependencies in runtime | Separate builder / runtime stages |
| Non-root user | `USER appuser` / `USER node` — enforced by CI |
| No shell access in prod | Entrypoint is the application binary |
| Read-only filesystem | K8s `readOnlyRootFilesystem: true` |
| Health checks | `HEALTHCHECK` directive in every Dockerfile |
| `--no-install-recommends` | Python images use `apt-get install --no-install-recommends` |

---

## 5. Security Hardening

### Static Analysis (SAST)

| Tool | Target | Gate Level | Workflow |
|------|--------|------------|----------|
| **CodeQL** | Python + JavaScript/TypeScript | PR-blocking | `codeql.yml` |
| **Bandit** | Python (all 6 layers) | PR-blocking (MEDIUM+) | `security-gates.yml`, `pr-checks.yml` |
| **Ruff** | Python lint + format | PR-blocking | `pr-checks.yml` |
| **ESLint** | TypeScript/React | PR-blocking | `pr-checks.yml` |
| **mypy** | Python type safety | PR-blocking (per-layer strictness) | `pr-checks.yml` |

### Dependency Scanning (SCA)

| Tool | Target | Gate Level | Workflow |
|------|--------|------------|----------|
| **Trivy** | Container images (OS + library vulns) | PR-blocking (HIGH/CRITICAL) | `security-gates.yml` |
| **pip-audit** | Python packages | PR-blocking (HIGH+) | `security-gates.yml`, `pr-checks.yml` |
| **pnpm audit** | Node.js packages | PR-blocking (CRITICAL), advisory (HIGH) | `security-gates.yml`, `pr-checks.yml` |
| **Dependency Review** | New deps in PRs | PR-blocking (HIGH+) | `security-gates.yml` |

### Secret Detection

| Tool | Scope | Trigger |
|------|-------|---------|
| **gitleaks** | Full git history | Every PR, push to main, weekly schedule |
| **Trivy secret scanner** | Container images | Every container build |

### Dynamic Analysis (DAST)

| Tool | Target | Trigger |
|------|--------|---------|
| **OWASP ZAP** | All backend API surfaces (L1–L5) | PRs and pushes to main |

ZAP runs against an ephemeral Docker Compose stack with dummy secrets, ensuring no production data exposure.

### Runtime Protections

| Control | Implementation |
|---------|---------------|
| Network segmentation | K8s NetworkPolicy deny-all default + per-layer allowlists |
| Non-root containers | Enforced in Dockerfile + CI gate |
| Read-only root filesystem | K8s `securityContext.readOnlyRootFilesystem` |
| Resource limits | CPU/memory limits on all K8s deployments |
| Pod disruption budgets | PDB for L2, L3, L4, frontend |
| Auto-scaling | HPA for L2, L4, frontend |
| Tenant isolation | Validated by `scripts/security/zero_trust_checks.sh` |
| Audit logging | Append-only, DB trigger-enforced (`shared/audit/`) |
| RBAC middleware | JWT + API key validation via `shared/identity/` |

### Attack Surface Reduction

1. **No debug endpoints in production** — Health/metrics only
2. **API rate limiting** — 1,000 req/min global, 1 req/sec per-domain for crawlers
3. **Input validation** — Pydantic v2 models with strict types
4. **Output sanitization** — No raw error traces in production responses
5. **PII detection** — Layer 1 crawlers scan for PII before storage

### NIST SSDF Alignment

| Practice | Control |
|----------|---------|
| PO.1 (Security requirements) | `SECURITY.md`, threat model, control matrix |
| PS.1 (Protect software) | RBAC, network policies, non-root containers |
| PS.2 (Protect development) | Dev Containers, secret detection, dependency review |
| PW.1–PW.4 (Secure design) | Contract-first API design, type checking, linting |
| PW.5–PW.7 (Secure code) | CodeQL, bandit, Trivy, DAST |
| PW.8–PW.9 (Secure build) | Hermetic builds, provenance attestation, signing |
| RV.1–RV.3 (Respond) | Runbooks, escalation policy, postmortem templates |

### SLSA Levels

| Level | Requirement | Status |
|-------|-------------|--------|
| SLSA 1 | Build process documented | ✅ `build-deploy.yml` |
| SLSA 2 | Hosted build service, signed provenance | ✅ GitHub Actions + OIDC cosign |
| SLSA 3 | Hardened build platform, non-falsifiable provenance | ✅ `actions/attest-build-provenance@v2` |

---

## 6. Supply Chain Integrity

### Artifact Signing

**Tool:** Cosign keyless signing (Sigstore/Fulcio OIDC)

**Workflow:** `build-deploy.yml` → `build-matrix` job

```yaml
# Every image tag is signed with OIDC identity
cosign sign --yes "$IMAGE_REF"

# Immutable digest reference is also signed
cosign sign --yes "$REGISTRY/...<layer>@sha256:<digest>"
```

**Identity chain:**
- OIDC Issuer: `https://token.actions.githubusercontent.com`
- Certificate Identity: `https://github.com/bmsull560/Fabric_4L/.github/workflows/build-deploy.yml@refs/heads/main`

### Provenance Generation

**Tool:** `actions/attest-build-provenance@v2`

Every container image receives a SLSA provenance attestation pushed to the registry alongside the image. The attestation includes:
- Source repository and commit SHA
- Build workflow identity
- Builder platform details
- Input/output mappings

### SBOM Generation

**Tools:**
- **Trivy** (CycloneDX format) — in `security-gates.yml` `sbom-policy` job
- **Anchore/sbom-action** — in `security-gates.yml` `sbom-generation` job

Every service and the frontend receive individual SBOMs uploaded as GitHub Actions artifacts with 30-day retention.

Release evidence workflows use stable SBOM artifact naming per service and commit SHA:

- `sbom-<service>-<git_sha>.cdx.json` (CycloneDX JSON)
- artifact bundle: `scan-<service>-<git_sha>`

### PR vs Main/Release Behavior

- **Pull requests (`main` / `release/**` targets):** build images locally, run container scans, and publish SBOM artifacts only (no registry push/signing).
- **Main / release / tags:** push publishable images, sign each image keylessly with GitHub OIDC (Cosign), attach SBOM attestations to the registry, and verify signature/attestation metadata in CI.

Policy enforcement is handled by `scripts/ci/check_image_supply_chain_metadata.py`, which fails CI when expected metadata is missing:

- PR mode: requires SBOM artifacts for each expected service image.
- Release mode: requires both SBOM and signing/attestation verification outputs for each expected service image.

### Artifact Verification Before Deploy

**Script:** `scripts/security/verify-artifact.sh`

Performs 5 checks before any deployment:

1. **Cosign signature verification** — Validates OIDC keyless signature
2. **SLSA provenance verification** — Validates build provenance attestation
3. **SBOM attestation check** — Verifies CycloneDX SBOM (informational)
4. **Non-root runtime check** — Ensures container runs as non-root
5. **Digest pinning check** — Verifies image is referenced by content digest

Output: Structured JSON report in `artifacts/verification/`.

```bash
# Verify before deploying
./scripts/security/verify-artifact.sh ghcr.io/bmsull560/fabric_4l/layer3-knowledge:sha-abc12345

# Verify image signature directly (OIDC keyless)
cosign verify \
  --certificate-identity-regexp "https://github.com/<org>/<repo>/.github/workflows/release-evidence-bundle.yml@.*" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  ghcr.io/<org>/fabric_4l/layer3-knowledge:<git_sha>

# Verify CycloneDX SBOM attestation in registry
cosign verify-attestation \
  --certificate-identity-regexp "https://github.com/<org>/<repo>/.github/workflows/release-evidence-bundle.yml@.*" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  --type cyclonedx \
  ghcr.io/<org>/fabric_4l/layer3-knowledge:<git_sha>
```

### Trust Model for Dependencies

| Dependency Type | Trust Level | Verification |
|----------------|-------------|-------------|
| Base images (python, node) | High — Docker Official | Tag-pinned, Trivy-scanned |
| Python packages (PyPI) | Medium | pip-audit, bandit, hash-verified |
| Node packages (npm) | Medium | pnpm audit, lockfile frozen |
| Rust crates (crates.io) | N/A | Not part of current production toolchain; `cargo clippy` and `cargo audit` are deferred until Rust code is added |
| GitHub Actions | High — first-party or verified | Version-pinned, OIDC |
| Internal shared libraries | High — owned | Contract tests, architecture tests |

---

## 7. CI/CD Pipeline

### Pipeline Stages

```
┌─────────┐   ┌──────────┐   ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌────────┐
│  LINT   │──▶│ TYPECHECK │──▶│  TEST   │──▶│  BUILD   │──▶│  SCAN    │──▶│  SIGN  │
│ ruff    │   │ mypy     │   │ pytest  │   │ docker   │   │ trivy    │   │ cosign │
│ eslint  │   │ tsc      │   │ vitest  │   │ buildx   │   │ bandit   │   │ attest │
└─────────┘   └──────────┘   └─────────┘   └──────────┘   │ codeql   │   └────────┘
                                                           │ gitleaks │       │
                                                           │ zap      │       ▼
                                                           └──────────┘   ┌────────┐
                                                                          │ DEPLOY │
                                                                          │ verify │
                                                                          │ k8s    │
                                                                          │ smoke  │
                                                                          └────────┘
```

### Workflows and Triggers

| Workflow | Trigger | Gate Type |
|----------|---------|-----------|
| `pr-checks.yml` | PR to main | **Required** — blocks merge |
| `security-gates.yml` | PR + push to main + weekly | **Required** — blocks merge |
| `codeql.yml` | PR + push to main + weekly | **Required** — blocks merge |
| `backend-integrated-reproducibility.yml` | Manual backend-integrated evidence | Release evidence |
| `k8s-readiness.yml` | PR to main | **Required** — blocks merge |
| `build-deploy.yml` | Push to main | **Release** — builds and deploys |
| `performance-load-tests.yml` | Push to main | **Advisory** — SLO tracking |
| `zero-trust-validation.yml` | Push to main | **Advisory** — security validation |
| `pr-checks.yml` / `integration-checks` | PR validation | **Release-smoke gate** — runs `make test-backend-integrated-release-smoke` |
| `publish-sdk.yml` | Manual | **Release** — SDK publication |

### Failure Gating Rules

| Check | Severity | Action on Failure |
|-------|----------|-------------------|
| Lint (ruff, eslint) | P0 | **Block merge** |
| Type check (mypy, tsc) | P0 | **Block merge** |
| Unit tests (pytest, vitest) | P0 | **Block merge** |
| Contract tests | P0 | **Block merge** |
| Security scan (HIGH+) | P0 | **Block merge** |
| Secret detection | P0 | **Block merge** |
| DAST (ZAP critical) | P1 | **Block merge** (ephemeral stack) |
| Performance regression | P2 | **Advisory** (SLO breach alert) |
| Accessibility (axe critical) | P1 | **Block merge** |

### Promotion Strategy

```
main branch push
    │
    ▼
┌─────────────────────────────┐
│  Build + Sign + Attest      │  ← build-deploy.yml
│  (7 parallel image builds)  │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Verify Signatures +        │  ← verify-supply-chain job
│  Provenance Attestations    │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Smoke Test Built Images    │  ← test-images job
│  (health + metrics)         │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Ephemeral K8s Deploy       │  ← deploy-ephemeral-and-smoke job
│  (kind cluster + kustomize) │
└─────────────┬───────────────┘
              │
              ▼
        dev environment
              │
       (manual promotion)
              │
              ▼
      staging environment
              │
       (manual promotion + verify-artifact.sh)
              │
              ▼
      production environment
```

### Rollback Strategy

1. **Immutable tags** — Every deploy uses `sha-<hash>` tag; previous versions remain in registry
2. **K8s rollout undo** — `kubectl rollout undo deployment/<layer>` for immediate rollback
3. **Runbook:** `docs/runbooks/deployment-rollback.md` documents step-by-step procedures
4. **Canary deploys** — K8s rolling update strategy with `maxUnavailable: 0, maxSurge: 1`

### Idempotency Guarantees

- **Kustomize** renders manifests deterministically from source
- **Docker BuildKit cache** ensures identical inputs produce identical outputs
- **`--frozen-lockfile`** prevents any dep resolution during builds
- Re-running the deploy pipeline with the same SHA produces identical artifacts

---

## 8. Observability & Verification

### Logging Standards

| Component | Format | Destination |
|-----------|--------|-------------|
| Backend services | Structured JSON (structlog) | stdout → Kubernetes log collector |
| Frontend | Console + remote telemetry | Browser console / debug collector |
| CI workflows | GitHub Actions logs | GitHub UI + downloadable artifacts |
| Security events | Append-only audit log | PostgreSQL (trigger-enforced immutability) |

### Metrics

**Prometheus scraping** configured in `monitoring/prometheus/prometheus.yml`:

| Metric | Source | Dashboard |
|--------|--------|-----------|
| Build success/failure rate | GitHub Actions | `value-fabric-operational.json` |
| Build latency (p50, p95, p99) | GitHub Actions timing | `value-fabric-operational.json` |
| Container vulnerability count | Trivy SARIF | `value-fabric-overview.json` |
| LLM API cost tracking | Layer 2/4 instrumentation | `llm-costs.json` |
| SLO error budget burn rate | Prometheus recording rules | `slo-error-budget-burn-rate.json` |
| Request latency per layer | FastAPI middleware | `value-fabric.json` |
| Active agent workflows | Layer 4 metrics | `value-fabric-operational.json` |

### Alerting Thresholds

Defined in `monitoring/alerting/rules.yml`:

| Alert | Condition | Severity |
|-------|-----------|----------|
| HighErrorRate | Error rate > 5% for 5 min | Critical |
| HighLatency | p99 > 2s for 10 min | Warning |
| HighCPU | CPU > 80% for 15 min | Warning |
| HighMemory | Memory > 85% for 10 min | Warning |
| DiskSpaceLow | Disk > 80% | Warning |
| DiskSpaceCritical | Disk > 90% | Critical |
| PodCrashLooping | Restart count > 3 in 15 min | Critical |
| SLOBudgetBurnRate | Budget burn > 2x for 1h | Critical |

**Notification:** AlertManager → Slack (template in `monitoring/alertmanager/templates/slack.tmpl`)

### Audit Logs

| Event Type | Storage | Retention | Immutability |
|------------|---------|-----------|-------------|
| **Builds** | GitHub Actions logs + artifacts | 30 days (artifacts), indefinite (logs) | GitHub-managed |
| **Deployments** | K8s events + audit log | 7-year retention (compliance) | DB trigger-enforced |
| **Security events** | SARIF uploads + security evidence bundle | 30 days (artifacts) | `release-security-evidence-<sha>` artifact |
| **API access** | `shared/audit/` append-only log | 7-year retention | PostgreSQL trigger prevents UPDATE/DELETE |
| **Secret access** | Vault audit log | Per Vault policy | Vault-managed |

### Security Evidence Bundle

Every PR and push to main generates a consolidated `release-security-evidence-<sha>` artifact containing:
- Trivy container scan SARIF
- SBOM (CycloneDX JSON) per service
- SBOM vulnerability policy evaluation
- DAST (ZAP) reports
- gitleaks scan results
- Security evidence manifest with commit SHA and timestamp

---

## 9. Testing Strategy

### Test-First Approach

All changes follow "failing tests first" methodology:

1. **Write failing test** that validates the expected behavior
2. **Implement minimum code** to make the test pass
3. **Refactor** while keeping tests green
4. **Run `make verify`** before committing

### Test Pyramid

| Level | Tool | Location | Gate | Coverage Target |
|-------|------|----------|------|-----------------|
| **Unit** | pytest (Python), vitest (TS) | `value-fabric/<layer>/tests/`, `frontend/client/src/**/*.test.*` | PR-blocking | ≥80% per layer |
| **Contract** | pytest + OpenAPI schema assertions | `tests/contract/` | PR-blocking | 100% of API surfaces |
| **Architecture** | pytest custom assertions | `tests/arch/` | PR-blocking | All cross-layer invariants |
| **Integration** | pytest + Docker Compose | `tests/integration/` | PR-blocking | Critical paths |
| **E2E** | Playwright | `frontend/e2e/` | PR-blocking | Core user journeys |
| **Performance** | k6 | `tests/performance/` | Advisory (SLO) | Critical path latency |
| **Security** | bandit, CodeQL, Trivy, ZAP | CI workflows | PR-blocking | All code paths |
| **Agent evals** | Golden-trace eval harness | `tests/evals/` | Required for skill changes | All agent skills |

### Policy-Based Test Fixtures

**Authentication:**
- `shared/testability/` provides `FixedClock`, `SequentialIDGenerator` for deterministic auth testing
- Playwright E2E uses `user-tier-storage` localStorage for tier-based testing
- MSW (Mock Service Worker) handlers in `frontend/test/mocks/handlers.ts`

**Routing:**
- Contract tests validate all OpenAPI specs against actual route registrations
- Schemathesis property-based testing validates OpenAPI compliance
- Vite proxy rewrite tests ensure frontend-to-backend routing consistency

**Data Access:**
- `CacheBackendProtocol` and `HTTPClientProtocol` in `shared/testability/` enable mock injection
- Integration tests use real Docker Compose services with test data fixtures
- Billing/entitlements regression pack validates tier-based data access controls

### Test Commands

```bash
make verify          # Full pipeline: lint → typecheck → tests → contracts → build
make test            # All backend unit tests
make test-layer3     # Layer-specific tests
make test-frontend   # Frontend vitest
make test-e2e        # Playwright E2E
make contract-tests  # Cross-layer contract + arch tests
make evals           # Agent golden-trace evaluations
make perf-test       # k6 load tests
```

---

## 10. Production Readiness Checklist

See [PRODUCTION_READINESS_CHECKLIST.md](../PRODUCTION_READINESS_CHECKLIST.md) for the full pass/fail checklist.

### Summary

| Category | Checks | Status |
|----------|--------|--------|
| Security | 18 checks | All implemented |
| Reliability | 12 checks | All implemented |
| Scalability | 8 checks | All implemented |
| Compliance | 10 checks | All implemented |

---

## 11. Risk Analysis & Roadmap

### Top 5 Architectural Risks

| # | Risk | Impact | Mitigation |
|---|------|--------|-----------|
| 1 | **Base image CVE window** — Time between CVE disclosure and image rebuild allows vulnerable images to run | HIGH | Weekly scheduled security scans + Dependabot for base images + automated rebuild triggers |
| 2 | **OIDC token scope** — GitHub Actions OIDC tokens have repository-wide scope; compromised workflow could sign arbitrary artifacts | HIGH | Branch protection rules limit signing to `main` branch only; verify `certificate-identity` on consumption |
| 3 | **Secrets rotation gap** — 90-day API key rotation may leave stale keys active if rotation fails | MEDIUM | Vault dynamic secrets for databases; monitoring on key age; runbook for emergency rotation |
| 4 | **LLM provider supply chain** — Extraction and agent layers depend on external LLM APIs whose behavior can change without notice | MEDIUM | Golden-trace evaluations catch behavioral drift; model version pinning; fallback provider configuration |
| 5 | **Single-tenant CI** — All layers share one GitHub Actions runner pool; resource exhaustion in one layer can delay security-critical patches in another | MEDIUM | Matrix job parallelization; timeout limits on all jobs; consider self-hosted runners for critical paths |

### Top 5 Improvements for Future Iteration

| # | Improvement | Priority | Effort |
|---|-------------|----------|--------|
| 1 | **SLSA Level 4 — Hermetic builds** — Fully air-gapped build environment with no network access | HIGH | Large — requires custom builder infrastructure |
| 2 | **Runtime SBOM validation** — Verify deployed container SBOMs match signed attestations at admission time | HIGH | Medium — Kyverno or Gatekeeper policy |
| 3 | **VEX (Vulnerability Exploitability eXchange)** — Publish VEX documents alongside SBOMs to communicate non-exploitable findings | MEDIUM | Small — tooling integration |
| 4 | **Sigstore policy-controller** — Kubernetes admission controller that rejects unsigned/unattested images | HIGH | Medium — deploy + configure |
| 5 | **Reproducible frontend builds** — Achieve byte-identical frontend bundles across builds (currently blocked by Vite chunk hashing) | MEDIUM | Medium — investigate esbuild determinism flags |

### Day 0 → Day 30 Execution Roadmap

**Day 0–3: Foundation**
- [x] Dev Container configuration (`.devcontainer/`)
- [x] CodeQL SAST workflow (`codeql.yml`)
- [x] Artifact verification script (`verify-artifact.sh`)
- [x] Build reproducibility checker (`build-reproducibility-check.sh`)
- [x] Supply chain documentation (this document)
- [x] Production readiness checklist

**Day 4–10: Hardening**
- [ ] Enable branch protection requiring all 5 required workflows
- [ ] Deploy Sigstore policy-controller to staging K8s cluster
- [ ] Implement runtime SBOM validation with Kyverno
- [ ] Add VEX generation to SBOM pipeline
- [ ] Configure Dependabot for base image auto-updates

**Day 11–20: Operationalization**
- [ ] Run first DR gameday exercise using existing runbooks
- [ ] Configure Grafana alerts for supply chain metrics (sign failures, scan findings)
- [ ] Implement automated rollback on smoke test failure
- [ ] Enable Vault dynamic secrets for all database connections
- [ ] Complete security control matrix audit against NIST SSDF

**Day 21–30: Validation**
- [ ] Execute full penetration test against ephemeral staging environment
- [ ] Run build reproducibility checks across all 7 services
- [ ] Conduct tabletop exercise for compromised dependency scenario
- [ ] Document findings and update threat model
- [ ] Prepare SOC 2 Type II evidence package from CI artifacts

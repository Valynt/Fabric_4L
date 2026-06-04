# Secure Software Supply Chain Blueprint (Production-Grade)

**Scope:** End-to-end controls for Value Fabric from source to deployable artifacts in an enterprise, multi-tenant SaaS environment.

**Design targets:** deterministic builds, immutable artifacts, cryptographic verifiability, auditability, and fail-closed promotion.

---

## 1. Repository architecture

### 1.1 Directory model

```text
value-fabric/
  .devcontainer/                # Reproducible local runtime
  .github/workflows/            # CI/CD and policy gates
  .github/actions/              # Composite actions (reused workflows)
  .slsa/                        # Provenance generator config
  .policy/
    conftest/                   # OPA/Rego policy checks
    kyverno/                    # Admission and image verification policies
  build/
    docker/                     # Dockerfiles (layered, pinned, distroless runtime)
    scripts/                    # Reproducible build scripts
  contracts/
  docs/
  frontend/
  infra/
    terraform/                  # IaC modules + root stacks
    helm/                       # Deployment charts
  layer1-ingestion/
  layer2-extraction/
  layer3-knowledge/
  layer4-agents/
  layer5-ground-truth/
  layer6-benchmarks/
  shared/
  tests/
    unit/
    integration/
    e2e/
    security/
    policy/
```

### 1.2 Required root files

- `AGENTS.md`: contributor and AI-agent guardrails.
- `ARCHITECTURE.md`: system boundaries, trust zones, data flows.
- `SECURITY.md`: threat model summary, incident handling, reporting channel.
- `RELEASE.md`: release process, version gates, rollback criteria.
- `SBOM_POLICY.md`: SBOM format, retention, verification process.
- `PROVENANCE_POLICY.md`: SLSA provenance and verification requirements.
- `Makefile`: canonical build/test/security entrypoints.
- `.tool-versions` or `mise.toml`: pinned developer CLI versions.
- `.gitignore`, `.gitattributes`: normalized line-endings and archive determinism.
- `CODEOWNERS`: review boundaries for high-risk paths.

### 1.3 Dependency management strategy

- **Python:** `uv` with fully locked `uv.lock`; hashes required; no floating ranges in lock.
- **Node/TypeScript:** `pnpm` with `pnpm-lock.yaml` committed; `--frozen-lockfile` in CI.
- **Container bases:** digest-pinned images only (`FROM cgr.dev/chainguard/python@sha256:...`).
- **Terraform providers/modules:** version pinned + checksums via lock file.
- **Rust/Cargo:** not part of the current production toolchain; the repository has no tracked `Cargo.toml`, `Cargo.lock`, or Rust source files, so `cargo clippy` and `cargo audit` are intentionally not required checks.
- **No untrusted registries:** allowlist package registries via network egress policy.

### 1.4 Versioning strategy

- **Trunk versioning:** SemVer for external APIs and deployable services.
- **Build version:** `<semver>+git.<shortsha>.build.<runid>`.
- **OCI image tags:**
  - immutable: `ghcr.io/value-fabric/layer4-agents:1.9.3-git.a1b2c3d`
  - convenience: `:1.9`, `:1`, `:stable` (never used for deployment pins).
- **Promotion references:** deployments use digest (`@sha256:<digest>`), never mutable tag.

---

## 2. Environment & reproducibility

### 2.1 Local development environment

- **Dev Container + Docker BuildKit** as default local substrate.
- Optional **Nix flakes** for teams requiring maximal hermeticity.
- Bootstrapping:
  - `devcontainer up` for IDE/runtime parity.
  - `make bootstrap` installs pinned toolchain versions from `mise`.

Example `.devcontainer/devcontainer.json`:

```json
{
  "name": "value-fabric",
  "image": "mcr.microsoft.com/devcontainers/base:ubuntu-24.04@sha256:<digest>",
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:2": {},
    "ghcr.io/devcontainers/features/node:1": { "version": "22.11.0" },
    "ghcr.io/devcontainers/features/python:1": { "version": "3.12.6" }
  },
  "postCreateCommand": "make bootstrap",
  "remoteUser": "vscode"
}
```

### 2.2 Dependency pinning

- Every active language ecosystem has a committed lockfile.
- CI enforces lockfile freshness (`git diff --exit-code` after install).
- Rust/Cargo is excluded from this rule until tracked Rust code is introduced. Future Rust adoption must add a root or workspace `Cargo.lock` and CI coverage for `cargo clippy --all-targets --all-features` and `cargo audit`.
- `SOURCE_DATE_EPOCH` set from commit timestamp for deterministic archives.
- Build timestamps in binaries/artifacts normalized or omitted.

### 2.3 Secrets management

- **Runtime secrets:** HashiCorp Vault or cloud secret manager (AWS Secrets Manager/GCP Secret Manager).
- **CI secrets:** OIDC workload identity; short-lived tokens only.
- **Developer secrets:** `.env` from template + secret broker CLI; never committed.
- Pre-commit and CI secret scanning (`gitleaks`) fail hard.

### 2.4 IaC baseline and drift prevention

- **Terraform** for cloud resources; **Helm** for Kubernetes workloads.
- `terraform plan` in CI and nightly drift detection.
- `terraform apply` only from CI on protected branches and approved change sets.
- Kubernetes declarative drift checks with Argo CD sync status + alerting.

---

## 3. Build system

### 3.1 Tooling

- **Monorepo orchestration:** `turbo` for task graph + remote cache.
- **Frontend:** Vite + pnpm.
- **Python services:** `uv` + `pytest` + `ruff` + `mypy`.
- **Containers:** Docker Buildx with BuildKit, provenance disabled at build stage if external attest step is used; enabled if standardized.

### 3.2 Build isolation

- Ephemeral CI runners (one job, one clean VM/container).
- Network-restricted build steps for compile/test stages (dependency fetch happens in explicit prefetch stage).
- No host mounts except workspace; read-only mounts where possible.

### 3.3 Caching

- Remote cache scoped by repo + branch + lockfile hash.
- Cache keys include compiler version and lockfile checksum.
- Cache poisoning defense: trusted write cache only on protected branches.

### 3.4 Parallelization

- Turbo task DAG for independent package/layer builds.
- Test sharding by timing history.
- Per-service container builds parallelized with concurrency caps.

### 3.5 Hermetic and deterministic guarantees

- Pinned toolchains + digest-pinned base images.
- Locked dependencies + checksum verification.
- Rebuild reproducibility job compares generated checksums from two independent runs.
- Deterministic archives (`tar --sort=name --mtime=@$SOURCE_DATE_EPOCH --owner=0 --group=0`).

---

## 4. Artifact packaging

### 4.1 Artifact types

- OCI images for each service/layer.
- Frontend static bundle (content-addressed, immutable).
- Python wheels/sdists for shared libraries (internal index only).
- IaC module package snapshots.

### 4.2 Naming/versioning conventions

- OCI repo pattern: `ghcr.io/value-fabric/<component>`.
- Artifact labels (OCI annotations):
  - `org.opencontainers.image.source`
  - `org.opencontainers.image.revision`
  - `org.opencontainers.image.created`
  - `org.opencontainers.image.version`

### 4.3 Registry strategy

- Primary registry: GHCR or cloud Artifact Registry.
- Geo-replicated mirror for DR.
- Retention:
  - release artifacts: 7 years (audit/compliance)
  - non-release CI artifacts: 30–90 days

### 4.4 Image hardening

- Multi-stage Dockerfiles: builder → distroless runtime.
- Non-root user (`USER 65532:65532`), read-only root FS.
- Drop Linux capabilities (`ALL`) and add only required.
- Explicit seccomp/AppArmor profiles.
- Example runtime base: Chainguard/Wolfi distroless.

---

## 5. Security hardening

### 5.1 Static analysis and dependency scanning

- **SAST:** Semgrep + CodeQL (critical repos/services).
- **SCA:** Trivy + OSV scanner + Dependabot/Renovate.
- **Container scan:** Trivy/Grype on final image digest.
- **IaC scan:** Checkov + tfsec + kube-linter.
- **Secrets scan:** gitleaks in pre-commit and CI.

### 5.2 Runtime protections

- Kubernetes Pod Security Standards (`restricted`).
- NetworkPolicies default deny ingress/egress; explicit allow rules.
- mTLS service-to-service with cert rotation.
- WAF/API gateway rate limiting and schema validation.
- Runtime threat detection with Falco.

### 5.3 Attack surface reduction

- Disable shell/package manager in runtime images.
- Remove unused ports and debug endpoints in production.
- Build-time feature flags default-off for experimental code.
- Strict CORS and CSP for frontend.

### 5.4 Input/output sanitization policies

- JSON schema validation at API boundaries.
- Output encoding by context (HTML, JSON, SQL, shell).
- Parameterized queries only; deny raw SQL in handlers.
- File upload constraints (type, size, malware scan, quarantine).

### 5.5 Secure defaults

- TLS 1.2+ everywhere; HSTS for public endpoints.
- Deny-by-default RBAC roles.
- Token TTLs short; refresh with rotation and revocation.
- Config drift to insecure modes blocked by policy checks.

### 5.6 Alignment targets

- **NIST SSDF (SP 800-218):** mapped in control matrix (`PO`, `PS`, `PW`, `RV`).
- **SLSA:** target **SLSA 3** for build provenance and hardened CI; roadmap to SLSA 4.

---

## 6. Supply chain integrity

### 6.1 Signing

- **Cosign keyless signing** via OIDC identity in CI.
- Sign container digests and non-container artifacts.

### 6.2 Provenance

- Generate in-toto/SLSA provenance attestations for each build output.
- Provenance links: repo URI, commit SHA, workflow run ID, builder image digest.

### 6.3 SBOM

- Generate CycloneDX + SPDX SBOMs using Syft.
- Attach SBOM as OCI referrers and archive in artifact store.

### 6.4 Verification before deploy

- Admission control requires:
  1. valid cosign signature
  2. trusted identity issuer/subject
  3. provenance predicate meets SLSA policy
  4. vulnerability policy pass (no critical open vulns unless approved exception)

Example verification gate:

```bash
cosign verify --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --certificate-identity-regexp 'https://github.com/value-fabric/.github/workflows/release.yml@refs/heads/main' \
  ghcr.io/value-fabric/layer4-agents@sha256:<digest>

cosign verify-attestation --type slsaprovenance ghcr.io/value-fabric/layer4-agents@sha256:<digest>
```

### 6.5 Dependency trust model

- Allowlist upstream dependencies by registry + namespace.
- Require signed releases where ecosystem supports it.
- Transitive dependency risk scoring and policy exceptions with expiry.

---

## 7. CI/CD pipeline

### 7.1 Pipeline stages

1. **Preflight:** formatting, lint, policy-as-code checks.
2. **Test:** unit/integration/e2e/security tests.
3. **Build:** deterministic builds for all deployables.
4. **Scan:** SAST/SCA/container/IaC scanning.
5. **Package:** publish immutable artifacts by digest.
6. **Sign + attest:** cosign signatures + provenance + SBOM attach.
7. **Deploy Dev:** automatic on main with post-deploy checks.
8. **Promote Staging:** manual approval + policy gate.
9. **Promote Prod:** change window + two-party approval + progressive rollout.

### 7.2 Failure gating

- Any critical severity scan finding blocks promotion.
- Missing signature/provenance/SBOM blocks deployment.
- Test flake budget exceeded blocks merge (flakes quarantined with owner + SLA).
- Policy engine errors fail closed.

### 7.3 Promotion strategy

- GitOps promotion via environment-specific manifest repo overlays.
- Only digest-pinned artifacts promoted.
- Same artifact promoted across environments (no rebuild).

### 7.4 Rollback strategy

- Rollback = redeploy previous known-good digest.
- Automated rollback trigger on SLO burn rate and canary failure.
- Database migrations: backward-compatible expand/contract and tested rollback scripts.

### 7.5 Idempotency guarantees

- Re-running pipeline for same commit produces same artifact checksum.
- Deploy job re-apply is no-op when desired state equals current state.

---

## 8. Observability & verification

### 8.1 Logging standards

- Structured JSON logs with consistent fields:
  - `timestamp`, `service`, `env`, `trace_id`, `span_id`, `request_id`, `actor`, `outcome`.
- No secret values in logs (redaction middleware required).
- Tamper-evident archival for security/audit logs.

### 8.2 Metrics

- CI metrics: pipeline success rate, mean duration, queue time, flaky test rate.
- Supply chain metrics: signed artifact coverage, provenance verification pass rate.
- Security metrics: MTTR for vulnerabilities, open critical findings.

### 8.3 Alerting thresholds

- Build failure rate > 10% over 30 min → page CI owner.
- Signature/provenance verification failure > 0 in prod deploy path → page security.
- Critical vuln detected on deployed digest → page on-call + security.

### 8.4 Audit logs (required)

- Build audit: who triggered, commit, workflow, runner identity, artifact digest.
- Deployment audit: approver, environment, old/new digest, rollout status.
- Security audit: scan findings, policy exceptions, expiry, approver.

---

## 9. Testing strategy (critical)

### 9.1 Test-first approach

- PRs must include failing tests first for behavior/security regressions.
- Review rule: no production code merge unless new/changed behavior has corresponding test delta.
- Test changes required in same commit set as code change.

### 9.2 Test pyramid

- **Unit tests:** deterministic, fast, no network.
- **Integration tests:** service + datastore via ephemeral containers.
- **E2E tests:** user/business critical paths in staging-like environment.
- **Security tests:** authz bypass, injection, SSRF, deserialization, misconfiguration checks.

### 9.3 Policy-based fixtures

- **Auth fixtures:** role matrix (`tenant_admin`, `analyst`, `readonly`) and token scopes.
- **Routing fixtures:** allow/deny route map with expected status and audit event.
- **Data access fixtures:** tenant-boundary assertions, row-level policy validation.

### 9.4 Non-functional verification

- Load tests for p95 latency budgets and saturation behavior.
- Chaos drills for dependency outages.
- Backup/restore test with RTO/RPO assertions.

---

## 10. Production readiness checklist (PASS/FAIL)

| Domain | Check | PASS criteria | FAIL criteria |
|---|---|---|---|
| Security | Critical vulns | 0 open critical in runtime artifacts | Any unapproved critical |
| Security | Artifact signing | 100% deployable artifacts signed | Any unsigned deployable |
| Security | Provenance | SLSA attestation verified in deploy gate | Missing/invalid attestation |
| Reliability | Test health | Unit/integration/e2e pass on release commit | Any required suite failing |
| Reliability | Rollback | Last known-good digest rollback tested in last 30 days | No recent validated rollback |
| Scalability | Performance | Meets p95/p99 SLO under expected peak + 30% headroom | SLO miss at baseline load |
| Compliance | Audit trail | Immutable build+deploy+security logs retained per policy | Missing or mutable audit logs |
| Compliance | Access control | Least-privilege review completed and approved | Broad/unreviewed permissions |
| Operations | Drift control | No unmanaged infra drift in weekly report | Drift unresolved > SLA |
| Supply chain | SBOM | SBOM generated + stored + linked for each release | Missing SBOM on release |

---

## Top 5 architectural risks

1. **Cache poisoning in shared build caches** causing untrusted artifact reuse.
2. **OIDC trust misconfiguration** allowing unauthorized signing identities.
3. **Policy bypass through emergency/manual deploy paths** outside GitOps controls.
4. **Transitive dependency compromise** (malicious package update) despite lockfiles.
5. **Observability blind spots** that miss provenance/signature verification failures.

## Top 5 improvements for future iteration

1. Move from SLSA 3 to **SLSA 4** with two-party reviewed, hermetic isolated builders.
2. Add **reproducible rebuild service** that continuously re-builds and diff-verifies release artifacts.
3. Enforce **binary authorization at cluster level** with mandatory attestations.
4. Introduce **tenant-aware security scorecards** mapped to SLA and compliance controls.
5. Add **automated exception expiry enforcement** for vulnerabilities/policy waivers.

## Day 0 → Day 30 execution roadmap

### Day 0–3 (Foundations)

- Pin toolchains (`mise`, lockfiles, digest-pinned base images).
- Stand up baseline CI stages: lint/test/build with fail-closed behavior.
- Enable gitleaks, Semgrep, Trivy in blocking mode for main branch.

### Day 4–10 (Integrity)

- Implement cosign keyless signing in CI.
- Generate and attach SBOM + SLSA provenance for all OCI artifacts.
- Add admission policies for signature and provenance verification.

### Day 11–20 (Hardening)

- Convert runtime images to distroless/non-root/read-only FS.
- Enforce NetworkPolicies and Pod Security restricted profile.
- Add policy-based security tests (auth/routing/data access fixtures).

### Day 21–30 (Operationalization)

- Implement progressive delivery with canary + auto rollback.
- Add audit dashboards and alerts for build/deploy/security events.
- Run first formal release readiness review with PASS/FAIL checklist.


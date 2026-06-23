# Production Signoff Runway

## Scope Freeze (Phase 0)

- **Signoff scope:** Full enterprise SaaS monorepo production-readiness gate across architecture, contracts, security, data, frontend, backend, infra, and release governance.
- **Included apps/services:**
  - `apps/web`
  - `services/api`
  - `services/layer1-ingestion`
  - `services/layer2-extraction`
  - `services/layer3-knowledge`
  - `services/layer4-agents`
  - `services/layer5-ground-truth`
  - `services/layer6-benchmarks`
- **Explicitly excluded from signoff execution:**
  - `docs/archive/**` historical artifacts
  - Experimental or deprecated paths not mapped to maintained deployable services
- **Architecture drift policy:** Frozen for this signoff runway. Architecture-changing work requires approved ADR and explicit signoff issue linkage.
- **Tracking issue authority:** `docs/launch/PRODUCTION_SIGNOFF_ISSUE.md` is the canonical signoff issue artifact. All production-signoff work must map to it.

## Signoff Decision Rule

Production signoff is allowed only when:

`clean build + clean migrations + clean security gate + clean contract gate + clean live P0 Playwright evidence + clean observability gate + documented rollback + named owners = production candidate`

## Production Signoff Phases

### Phase 1 — Establish Source of Truth

- Confirm canonical package paths.
- Deprecate duplicate service/package locations.
- Publish ADRs for unresolved architectural decisions.
- Lock canonical OpenAPI specs.
- Lock canonical env var schema.
- Lock canonical route map.
- Lock canonical tenant/auth model.
- Lock canonical deployment topology.

### Phase 2 — Monorepo Hygiene

- Run full dependency audit.
- Remove dead packages.
- Remove unused feature flags.
- Remove stale compatibility aliases.
- Remove duplicate utilities.
- Normalize naming across services.
- Ensure every package has owner, purpose, and lifecycle status.
- Ensure no generated files are incorrectly committed.
- Ensure lockfiles are clean and reproducible.

### Phase 3 — Build Reproducibility

- Clean clone test.
- Install from scratch.
- Build all packages.
- Build all Docker images.
- Run all migrations from empty DB.
- Run all migrations against existing staging DB.
- Verify rollback scripts.
- Pin runtime versions.
- Pin base images by digest.
- Confirm no local-only assumptions.

### Phase 4 — Contract Enforcement

- Export OpenAPI for every service.
- Compare generated OpenAPI against committed specs.
- Fail CI on contract drift.
- Run frontend API-client generation.
- Run backend contract tests.
- Validate request/response schemas.
- Validate error envelope consistency.
- Validate pagination conventions.
- Validate auth-required endpoints.
- Validate tenant-scoped endpoints.

### Phase 5 — Security Gate

- Threat model core flows.
- Verify tenant isolation tests.
- Verify RBAC tests.
- Verify auth bypass tests.
- Verify CSRF/session behavior.
- Verify service-to-service auth.
- Verify API key handling.
- Verify no raw secrets in logs.
- Verify no raw secrets in seed data.
- Verify dependency vulnerability scan.
- Verify container image scan.
- Verify SAST.
- Verify secret scan.
- Verify production debug routes are disabled.
- Verify non-production validation endpoints cannot run in prod.

### Phase 6 — Data and Migration Readiness

- Validate all DB migrations.
- Validate seed scripts.
- Validate tenant bootstrap.
- Validate RLS or schema-per-tenant enforcement.
- Validate backup process.
- Validate restore process.
- Validate point-in-time recovery.
- Validate data retention policy.
- Validate PII classification.
- Validate audit log persistence.
- Validate migration rollback plan.

### Phase 7 — Frontend Readiness

- Run TypeScript check.
- Run lint.
- Run unit tests.
- Run component tests.
- Run accessibility checks.
- Run Playwright against mock mode.
- Run Playwright against live backend.
- Verify auth flows.
- Verify empty states.
- Verify loading states.
- Verify error states.
- Verify no broken navigation.
- Verify no dead routes.
- Verify production build passes.

### Phase 8 — Backend Readiness

- Run unit tests per service.
- Run integration tests per service.
- Run cross-service workflow tests.
- Run contract tests.
- Run async/queue tests.
- Run database tests.
- Run failure-path tests.
- Run idempotency tests.
- Run retry behavior tests.
- Run rate-limit tests.
- Run auth/tenant middleware tests.
- Verify `/health`.
- Verify `/ready`.
- Verify `/metrics`.

### Phase 9 — Live Full-Stack Environment

- Deploy full stack to staging/Bunnyshell/live environment.
- Use production-like secrets mechanism.
- Use production-like ingress.
- Use production-like database.
- Use production-like queues.
- Use production-like object storage.
- Use production-like observability.
- Run smoke tests after deploy.
- Run full P0 Playwright suite against live environment.
- Store JUnit, trace, video, and screenshots as evidence.
- Fail signoff if live P0 evidence is missing.

### Phase 10 — Observability and Operations

- Confirm logs are structured.
- Confirm request IDs propagate across services.
- Confirm traces work across service boundaries.
- Confirm Prometheus metrics are exposed.
- Confirm dashboards exist.
- Confirm alerts exist.
- Confirm alert routing works.
- Confirm runbooks exist.
- Confirm SLOs are defined.
- Confirm error budget policy exists.
- Confirm on-call ownership.
- Confirm incident process.

### Phase 11 — Performance and Resilience

- Run load tests.
- Run concurrency tests.
- Run queue backlog tests.
- Run database saturation tests.
- Run cold-start tests.
- Run large tenant tests.
- Run failure injection tests.
- Validate graceful degradation.
- Validate timeout behavior.
- Validate retry limits.
- Validate circuit breakers.
- Validate autoscaling.
- Validate resource limits.

### Phase 12 — Kubernetes / Infra Readiness

- Validate Kustomize overlays.
- Validate production overlay.
- Validate staging overlay.
- Validate ingress.
- Validate TLS.
- Validate cert-manager.
- Validate ExternalSecrets/Vault.
- Validate HPA.
- Validate probes.
- Validate network policies.
- Validate pod security context.
- Validate image pull policy.
- Validate rollout strategy.
- Validate rollback command.
- Validate disaster recovery procedure.

### Phase 13 — Release Governance

- Create release candidate tag.
- Generate changelog.
- Attach test evidence.
- Attach security evidence.
- Attach live E2E evidence.
- Attach migration evidence.
- Attach rollback plan.
- Attach known issues list.
- Attach deferred decisions list.
- Attach launch risk register.
- Require product signoff.
- Require engineering signoff.
- Require security signoff.
- Require operations signoff.

### Phase 14 — Final Go / No-Go

- No critical vulnerabilities.
- No unresolved P0 bugs.
- No missing production secrets.
- No missing migrations.
- No contract drift.
- No tenant isolation gaps.
- No failed live P0 workflows.
- No unowned services.
- No unmonitored services.
- No undocumented rollback path.
- No fake/stub/mock dependencies in production path.

## Immediate Execution Order

1. Create `PRODUCTION_SIGNOFF.md`.
2. Create signoff issue with all phases.
3. Freeze architecture drift.
4. Run clean clone/build/test.
5. Export and compare OpenAPI specs.
6. Run tenant/auth/security suite.
7. Deploy full stack to live staging/Bunnyshell.
8. Run full P0 Playwright live workflows.
9. Collect evidence artifacts.
10. Hold go/no-go review.

## Key Principle

No production claim without live full-stack evidence.

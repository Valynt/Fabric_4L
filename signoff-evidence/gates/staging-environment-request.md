# Packet (h) — Staging-Environment Request

- **Task refs:** #1257 (V1-DR-001), #1260 (V1-GOLDEN-001/002), #1261 (V1-OPS-001)
- **Packet status:** awaiting Platform/Infra authority — ONE signature provisions the environment; three launch blockers unblock.
- **Requested by:** release-engineering swarm (auto-mode)
- **UTC:** 2026-08-11T04:10:00Z
- **Authority:** Platform/Infra + Release Management

---

## 1. What is blocked and why (one sentence each, evidence-linked)

| Issue | Root cause | Smallest-unblock |
|---|---|---|
| #1257 V1-DR-001 | The DR posture contradicts the contract at every level: WAL-G/S3 disabled (`ENABLE_WALG_BACKUP: "false"`), `dr-drill.yml` verifies artifacts nothing produces, the only executed rollback drill FAILED (`signoff-evidence/p0-rollback-20260613.json`), and no production-like deployment has ever completed (`.deployments/` empty). | A production-like staging namespace with S3-compatible object storage (minio or S3) so WAL-G can be enabled and one restore drill + one rollback rehearsal can run green with committed evidence. |
| #1260 V1-GOLDEN-001/002 | No SHA-bound executable golden-path certification exists; the deterministic clickpath (j24) is fully mocked and the live specs cover only fragments; the Meridian certification harness seed lives on #1252, which carries two blocking defects (see `signoff-evidence/v1-routing-001-decomposition-review.md` F-1/F-2) and cannot merge as-is. | The staging stack below + the decomposed routing PRs landed; then execute `make certify-meridian-journey` (13 stages) and the extended golden-path suite at one SHA, including the Tenant-B hostile leg. |
| #1261 V1-OPS-001 | Observability is configured but never exercised: Alertmanager receivers DEFERRED, dashboards PARTIAL (metrics 200 only on L4/L5/L6), log/trace aggregation DEFERRED, and only 1 of 5 critical journeys has SLI rules/alerts/dashboards (`signoff-evidence/p1-operational-20260613.json`). | The monitoring profile of the staging stack (Prometheus + Alertmanager + Grafana + Loki + Jaeger) with a reachable test receiver, so span-attribute assertions, all-5-journey SLI evaluation, and a delivered test alert can be evidenced. |

## 2. Requested staging environment

### 2.1 Services (compose profiles already in-repo)

Base: `infra/compose/docker-compose.dev.yml` — postgres:16, pgbouncer, redis, neo4j, keycloak, minio, layer2, layer2-worker, layer2-5, layer4, api-gateway, frontend.
Production-like overlay: `infra/compose/docker-compose.live.yml` (L1/L3/L5/L6 complete the L1–L6 stack).
Observability: `infra/compose/docker-compose.observability.yml` / `docker-compose.monitoring.yml` — Prometheus, Grafana, Alertmanager (with a real test receiver), Loki, Jaeger, Fluent-bit.
Release smoke: `infra/compose/docker-compose.release-smoke.yml` for `make test-backend-integrated-release-smoke`.

### 2.2 Data fixtures

- Two seeded tenants (Tenant A and hostile Tenant B) via `scripts/db/seed-e2e-data.ts` / `scripts/db/reset-e2e-data.ts` (already on main).
- E2E personas: `E2E_VALIDATION_ADMIN_ID`, `E2E_VALIDATION_READONLY_ID`, `E2E_VALIDATION_REVIEWER_ID`, `E2E_VALIDATION_SALES_ID`; `BACKEND_E2E_TENANT_ID`, `BACKEND_E2E_TENANT_BETA_ID`.
- Meridian account fixture: `E2E_MERIDIAN_ACCOUNT_UUID`.
- One WAL-G/S3-produced backup artifact for the restore drill (or the daily pg_dump artifact if the honest-RPO amendment route is taken by the named risk owner — see packet (d)).

### 2.3 Environment variables (names only; values via Infisical per AGENTS.md §17)

- Core: `DATABASE_URL`, `REDIS_URL`, `STORAGE_TYPE`, `S3_ENDPOINT`, `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`
- Auth: `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_ADMIN_USER`, `KEYCLOAK_ADMIN_PASSWORD`, `JWT_ISSUER`, `JWT_AUDIENCE`, `JWT_SECRET`, `FABRIC_AUTH_*`
- DR: `ENABLE_WALG_BACKUP` (currently "false" — enabling is the DR fix or the documented gap), WAL-G `WALG_*`/S3 vars as defined by `k8s/base/postgres-backup-cronjob.yaml`
- Observability: `SENTRY_DSN`, `SENTRY_DSN_BACKEND`, `ALERTMANAGER_WEBHOOK_URL`, `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`
- Frontend live mode: `VITE_API_BASE_URL`, `VITE_PROXY_L1_URL` … `VITE_PROXY_L6_URL`, `PLAYWRIGHT_LIVE_MODE`, `PLAYWRIGHT_LIVE_FRONTEND_URL`, `PLAYWRIGHT_BACKEND_URL`
- LLM (only if packet (b) decision = live workflows mandatory): `OPENAI_API_KEY`/provider equivalents, `AGENT_DEFAULT_MODEL`

### 2.4 Exact commands once the environment exists (execution order)

```bash
# Boot + migrate
pnpm env:dev && docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated up -d
make migrate

# #1257 DR (V1-DR-001)
make test-backup-drills
make check-migration-postgres-roundtrip
# + WAL-G restore drill → commit docs/launch/evidence/walg-restore-drill-evidence.json

# #1260 golden path (V1-GOLDEN-001/002) — after routing PRs land
make certify-meridian-journey            # 13 stages, Meridian harness
make test-backend-integrated-release-smoke
pnpm --dir apps/web run test:e2e:live    # browser leg (V1-GOLDEN-002)

# #1261 observability (V1-OPS-001)
pytest tests/observability tests/reliability tests/recovery
# + alertmanager test-receiver delivery evidence; SLI evaluation j01–j05

# Candidate certification at the merged SHA (Movement II)
make validate-launch-contract && make release-baseline
CERTIFY_LIVE=1 make certify-release-candidate RELEASE_SHA=<merged-candidate-sha>
make build-release-evidence RELEASE_SHA=<merged-candidate-sha>
```

## 3. One-signature approval block

```
Staging environment approved for provisioning per this packet.
Name: ______________________  Role: ______________________  Date (UTC): __________
Scope: services + fixtures + env names in §2. No production credentials.
```

# Level-10 Rubric

**Core principle: Level 10 means production-proven, not merely implemented or passing
once.** Evidence MUST be automated, tied to an immutable commit and artifact digest,
fail-closed, and sustained through normal operation, deployments, failures, and recovery
exercises.

## Scoring rules

- **Weakest-link scoring**: a category scores 10 only when every critical subcategory is at
  least 9 and no weakest-link control is below 10. The category score is bounded by its
  weakest critical subcategory.
- **90-day sustained evidence**: Level 10 requires ≥ 90 consecutive days of proven
  operation — SLO attainment, synthetic journeys, deployments, tested alert delivery,
  restore drills, rollback exercises, security validation, and controlled incident
  response.
- **Production Operations cannot score 10 on repository evidence alone** — it requires
  sustained production telemetry and repeated recovery evidence.

## Category 1 — Product and Architecture

*Essence: the implemented production system matches the documented architecture, delivers
the complete ValuePilot outcome reliably, and resists contract, data, and structural drift.*

| # | Subcategory | Definition |
|---|---|---|
| 1.1 | Core ValuePilot Journey | Complete tenant-scoped journey runs on real services/data with no hidden mocks; every branch, auth state, failure, retry, recovery path tested and SLOs met ≥ 90 days. |
| 1.2 | Gateway Orchestration | Gateway is the only public ingress; every request passes authN/authZ, tenant validation, quotas, audit, correlation, policy; internal services reject direct access; failover/throttling proven under load. |
| 1.3 | Cross-Layer Integration | All L1–L6 boundaries use versioned contracts, durable IDs, idempotency, trace propagation, explicit failure semantics; retries never duplicate logical operations. |
| 1.4 | API Contract Integrity | Runtime-generated OpenAPI is authoritative; clients reproducibly generated; compatibility checked per consumer; CI fails on drift; no drift/breaking deployment for ≥ 90 days. |
| 1.5 | Data Ownership and Consistency | Every entity has one authoritative owner; outbox/saga for cross-store writes; automatic reconciliation; forward/backward schema compatibility; zero unreconciled writes under failure injection. |
| 1.6 | Frontend Domain Architecture | UI consumes validated domain view models, not raw DTOs; identity/tenant/account/authz scope all caches; accessibility, performance, stale-session behavior meet targets across browsers. |
| 1.7 | Release and Certification Architecture | Every release built once, signed, SBOM-attached, promoted by immutable digest, certified against exact candidate SHA; no uncertified artifact reaches production. |
| 1.8 | Maintainability | Module boundaries match business domains; zero dependency cycles; complexity/size ratchets; ownership/ADRs/docs let a qualified engineer safely change and deploy any critical component. |

## Category 2 — CI and Governance

*Essence: the delivery control plane reliably prevents unsafe changes, cannot be silently
bypassed, and produces an exact, immutable record of why every release was permitted.*

| # | Subcategory | Definition |
|---|---|---|
| 2.1 | Branch Protection Enforcement | All changes via reviewed PRs and merge queue; required reviews/checks, force-push prevention, admin enforcement; emergency bypasses time-limited, audited, with follow-ups. |
| 2.2 | Required-Check Name Alignment | Rulesets, policy, workflow job names, merge-queue contexts exactly synchronized; scheduled drift check blocks releases when any context is missing, renamed, duplicated, or non-reporting. |
| 2.3 | Workflow Determinism | Same SHA + locked inputs produce same artifacts/conclusions; pinned deps, reproducible generated files; flake rate < 0.1%. |
| 2.4 | Merge-Group Support | 100% of merges validated in their actual merge group; stale approvals/results invalidated; ≥ 90 days with no bypass or merge-caused main regression. |
| 2.5 | Aggregate Release Gates | Every child check reports into exactly one authoritative aggregate with tested fail-closed propagation of failed/cancelled/skipped/missing/neutral/stale/timed-out results. |
| 2.6 | Authoritative Gate Coverage | Every material release risk has an authoritative blocking control; no known critical risk is monitored only by a non-blocking check. |
| 2.7 | CI Execution Reliability | Required CI availability > 99.9%; fast-lane p95 < 15 min; release-lane p95 < 45 min; queue wait p95 < 5 min; infrastructure failures distinguished from product failures. |
| 2.8 | Independent Review Control | Sensitive changes require qualified independent CODEOWNER approval; no self-approval; approvals invalidated after material changes; review evidence bound to final SHA. |
| 2.9 | Evidence and Readiness Consistency | Readiness reports, risk registers, issue status, workflow conclusions, release records generated from the same authoritative evidence; missing/stale evidence shown as blocked/unknown, never inferred as passing. |

## Category 3 — Security and Tenancy

*Essence: tenant isolation and security controls are enforced at every boundary,
continuously attacked in production-shaped environments, and supported by sustained runtime
evidence.*

| # | Subcategory | Definition |
|---|---|---|
| 3.1 | Authorization Source of Truth | Backend authorization snapshot is the sole authority for roles, permissions, account scope, entitlements; snapshots tenant/session-bound, short-lived, revocable, integrity-protected, fail closed. |
| 3.2 | Frontend Fail-Closed Behavior | Loading/denied/expired/unauthenticated/tenant-switch/prior-session/malformed/backend-unavailable states cannot expose protected data or actions; proven via unit, integration, browser, hostile tests. |
| 3.3 | Tenant-Context Propagation | Verified tenant context accompanies every API request, queue message, DB op, graph query, vector retrieval, object key, cache entry, trace, audit event; each boundary independently verifies; missing/conflicting context rejected before business logic. |
| 3.4 | Queue and Worker Isolation | Queue envelopes authenticated and tenant-bound; least-privilege workers with durable idempotency, replay protection, bounded retries, poison-message isolation, tenant-safe DLQs. |
| 3.5 | Hostile Tenant Testing | Continuous tests with ≥ 2 real seeded tenants and known foreign resources across all surfaces; cross-tenant reads/writes/inference/leakage/replay succeed zero times. |
| 3.6 | AI Safety Boundaries | Prompts, retrieval, memory, tools, outputs tenant-scoped and policy-controlled; least-privilege tools with explicit approval for irreversible actions; injection/unsafe-output/provider-failure/cost fail closed. |
| 3.7 | Secrets and SAST Governance | One canonical secret provider, workload identity, automatic rotation; full-history secret scanning and required SAST clean of unapproved critical findings; every exception has owner, compensating control, expiry, automated expiration enforcement. |
| 3.8 | Supply-Chain Security | Every artifact has SBOM, verified provenance, vulnerability results, signature, source SHA, immutable digest; pinned dependencies/actions; admission policy blocks unsigned/mutable/critically vulnerable artifacts. |
| 3.9 | Live Security Proof | Authenticated DAST, hostile tenancy, admission checks, runtime detection, independent pentest cover the deployed release; zero unresolved critical/high exploitable findings; detection/containment/revocation/forensics demonstrated. |

## Category 4 — Production Operations

*Essence: the system has sustained its SLOs in production and repeatedly demonstrated safe
deployment, failure containment, recovery, and incident response.*

| # | Subcategory | Definition |
|---|---|---|
| 4.1 | Production Ingress | One hardened HA ingress path through the gateway; direct layer access structurally denied by routing and NetworkPolicies; TLS, rate limits, timeouts, DDoS controls continuously tested. |
| 4.2 | Backup Durability | Authoritative data continuously protected by encrypted, versioned, immutable, off-cluster backups across an independent failure boundary; completeness/checksums auto-verified; zero unmonitored failures. |
| 4.3 | Off-Cluster Recovery | Total loss of primary cluster/account/region recoverable from independent infrastructure and credentials; declared RPO/RTO repeatedly achieved. |
| 4.4 | Restore and Rollback Proof | Automated clean-environment restore drills pass repeatedly; rollback, migration recovery, data restoration are separate documented procedures; RPO ≤ 15 min, RTO ≤ 60 min proven through scheduled and surprise exercises. |
| 4.5 | Observability Configuration | Every critical service/journey emits correlated metrics, structured logs, distributed traces; > 99.9% of eligible requests carry correlation context; no prohibited tenant/secret data in telemetry. |
| 4.6 | Alerting and Incident Response | Every paging alert actionable, routed to a tested receiver, linked to an executable runbook, governed by severity/escalation; delivery-to-mitigation exercised regularly. |
| 4.7 | Deployment Automation | Automated policy-controlled promotion of the same signed digest through staging, canary, production; health/SLI/security/migration/tenancy gates auto-stop or roll back unsafe releases. |
| 4.8 | Staging Certification | Staging matches production topology/policies/config except approved values and scale; every candidate completes full production-shaped certification against its immutable digest. |
| 4.9 | Capacity and Availability | Platform sustains ≥ 3× expected peak while meeting SLOs; autoscaling, PDBs, backpressure, circuit breakers, retry budgets proven; availability and error budgets met ≥ 90 days. |

| 4.10 | Runbooks and Evidence Freshness | Every critical failure mode has an owned, tested, version-controlled runbook (detection → communication); evidence generated automatically, current, validated through drills and real incidents. |

## Category 5 — Overall Repository Condition

*Essence: the repository is an accurate, maintainable, continuously verified representation
of a secure and successfully operated production system.*

| # | Subcategory | Definition |
|---|---|---|
| 5.1 | Functional Breadth | Every committed capability complete across UI, API, persistence, authZ, observability, operations, support; no undocumented manual steps, placeholders, hidden mocks, or unowned components. |
| 5.2 | Test Depth | Risk-based tests across unit/property/contract/integration/browser/hostile-tenancy/security/migration/performance/resilience/restore/rollback; mutation and fault injection prove tests detect meaningful defects. |
| 5.3 | Architecture Coherence | Runtime topology, code boundaries, manifests, data ownership, contracts, ADRs, docs describe the same system; architecture fitness tests prevent unauthorized dependencies and policy bypasses. |
| 5.4 | Integration Stability | Critical integrations meet reliability/latency SLOs under load, retries, partial failure, degradation, schema evolution; backward-compatible contracts; no recurring integration defect or unexplained flake. |
| 5.5 | Maintainability | Complexity, duplication, module size, dependency health, docs, ownership, debt within enforced limits; multiple qualified maintainers for critical areas. |
| 5.6 | Change-Control Discipline | Every production change reviewable, independently approved, merge-queue validated, progressively deployed, observable, reversible; change-failure rate < 2%; every exception audited with corrective action. |
| 5.7 | Backlog and Risk Truthfulness | Issues, risk registers, waivers, readiness reports, production reality fully reconciled; no blocker closed without acceptance evidence; no accepted risk without owner and expiry. |
| 5.8 | Evidence Freshness | All release/readiness claims generated from the current candidate or production digest; evidence immutable, retained per policy, **no more than 24 hours old during certification**; stale/missing/conflicting/unverifiable evidence automatically blocks the claim. |
| 5.9 | Operational Proof | ≥ 90 consecutive days of SLO attainment, deployments, tested alert delivery, restore drills, rollback exercises, security validation, controlled incident response; no unresolved critical gaps. |
| 5.10 | Velocity Versus Control | Delivery stays fast without weakening controls; lead time, deployment frequency, change-failure rate, recovery time, queue depth, reviewer load within targets. |

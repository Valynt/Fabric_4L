# Production Operations Plan
**Repo:** bmsull560/Fabric_4L
**Scope:** Production readiness workstream — ingress, backup/recovery, deployment/rollback, and operational observability.
**Status:** Highest-priority workstream.
**Last updated:** 2026-08-21
---
## 1. Definitions
| Term                               | Definition                                                                                                                                                     |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **RPO** (Recovery Point Objective) | The maximum acceptable amount of data loss measured in time, i.e., the farthest point in the past to which data must be recoverable. Target: **≤ 15 minutes**. |
| **RTO** (Recovery Time Objective)  | The maximum acceptable elapsed time from the onset of a failure to full service restoration. Target: **≤ 60 minutes**.                                         |
| **WAL-G**                          | A tool that archives PostgreSQL Write-Ahead Log (WAL) segments continuously to backup storage, enabling point-in-time recovery.                                |
| **SLI**                            | Service Level Indicator — a quantifiable measure of a portion of a service's performance.                                                                      |
| **SLO**                            | Service Level Objective — the target value for an SLI that defines acceptable performance.                                                                     |
| **DAST**                           | Dynamic Application Security Testing — automated security testing of a running application against external input.                                             |
| **mTLS**                           | Mutual Transport Layer Security — both the client and server authenticate each other with certificates.                                                        |
| **SLI selector / rule label**      | The stable selector identifying a metric or alert rule; alerts must reference valid selectors and must not reference nonexistent metrics.                      |
---
## 2. Score Target
> **Authority note:** This document is a **non-authoritative** working plan. Launch
> decisions and ship/no-ship criteria are governed by the canonical documents:
> the [launch blocker register](docs/launch/launch-blocker-register.md), the
> [environment-dependent evidence matrix](docs/launch/environment-dependent-evidence-matrix.md),
> and the [final testing launch checklist](docs/launch/final-testing-launch-checklist.md).
> Score values here are directional planning estimates, not approval criteria.
- **Current:** 3.6
- **Target:** **8.3 before launch**, **9.0 after production proof**
- This is a **highest-priority workstream** for planning purposes.
| Section                                | Score effect |
| -------------------------------------- | ------------ |
| A. Production ingress convergence      | 3.6 → 5.0    |
| B. Proven backup and recovery          | 5.0 → 6.5    |
| C. Proven deployment and rollback      | 6.5 → 7.2    |
| D. Operational observability           | 7.2 → 8.0    |
| **Sections A–D cumulative**            | **3.6 → 8.0** |
| **Gap − 0.3 (to 8.3) / − 1.0 (to 9.0)** | **Out of scope** |
> **Gap to target:** The four sections above sum to an 8.0 ceiling:
> **8.3 (launch) and 9.0 (post-production-proof)** exceed this figure by
> **0.3** and **1.0** respectively. The gap must be closed by **additional,
> separate workstreams** (for example hardened compliance controls, security
> hardening, or expanded production proof) — it is not covered by Sections A–D
> alone. Closing the gap is tracked as its own follow-up; the declared score
> targets are retained and validated against the canonical launch evidence
> documents before launch.
---
## 3. Operational Requirements
The following requirements apply to all four sections unless a section states otherwise:
- All changes must be **contract-aligned** and **tenant-safe**; no change may weaken authentication, authorization, tenant isolation, rate limiting, or audit logging.
- Required evidence must be recorded with **exact artifact and environment identifiers** (commit SHA, image digest, cluster name, environment).
- All verification must be automated via CI gates; ad-hoc manual claims are not accepted as evidence.
- Production and certified staging configurations must be identical **except** approved environment-specific values.
- No secrets may be committed to source control; all credentials must be injected via the approved secret-management path.
---
## 4. Section A — Production Ingress Convergence
### Objective
Ensure **100% of public traffic** traverses the API gateway and that no layer is directly reachable from outside the network boundary.
### Implementation steps
1. Ratify **NGINX** as the v1 ingress (unless architecture leadership selects an alternative implementation).
2. Route the public API host **exclusively** to the API gateway.
3. **Remove all public layer routes**; layers must not be independently reachable.
4. Add **default-deny NetworkPolicies** to reject unauthorized connections by default.
5. Require **mTLS or authenticated service credentials** for all internal service-to-service calls.
6. Add **ingress render tests for every overlay** to guarantee the rendered ingress behaves as specified.
7. Run **gateway-aware Dynamic Application Security Testing (DAST)** and **tenancy tests**.
### Numerical targets
- Zero public layer endpoints.
- 100% of public traffic traverses gateway controls.
### Exit criteria
- [ ] Zero public layer endpoints are reachable.
- [ ] 100% of public traffic traverses the gateway.
- [ ] Network-policy tests prove layers reject unauthorized direct connections.
- [ ] Gateway failure behavior, rate limits, timeouts, retries, and request-size limits are tested and verified.
- [ ] Ingress configuration is byte-identical between certified staging and production, except approved environment values.
### Score effect
Production Operations **3.6 → 5.0**.
---
## 5. Section B — Proven Backup and Recovery
**Goal:** Guarantee service-specific restorability, with **RPO/RTO objectives scoped per critical service** per the canonical DR policy (`docs/reliability/dr-policy.md`), proven by automated restore validation. The policy's Tier 0 / Tier 1 targets (for example PostgreSQL **RTO ≤ 60 min / RPO ≤ 15 min**, Neo4j **RTO ≤ 90 min / RPO ≤ 30 min**, Redis **RTO ≤ 120 min / RPO ≤ 60 min**) are the authoritative objectives for this plan. The blanket **RPO ≤ 15 min / RTO ≤ 60 min** below is the **PostgreSQL Tier 0** requirement for the platform's system of record, not a uniform target across every service.
### Implementation steps
1. Correct database inventory and host inconsistencies in the backup CronJob; the inventory must match the live cluster topology.
2. **Fail loudly when an expected database is missing** — do not silently skip it.
3. Enable **WAL-G** in staging.
4. Archive WAL continuously to **encrypted, off-cluster object storage**.
5. Enable **object versioning and immutable/retention** on backup storage.
6. Store backups in a **separate account or security boundary** from the source cluster.
7. Perform **scheduled full backups** in addition to WAL archival.
8. Record, per backup: **backup ID, source cluster, start time, end time, checksum, and schema version**.
9. Tie restore evidence to the **backup ID and the candidate SHA** of the restored image.
### Restore validation sequence (automated)
1. Restore into a **clean, ephemeral environment**.
2. Validate **tenants, records, graph projections, evidence, accounts, and authorization data**.
3. Rebuild derived Redis, vector, and graph state where appropriate.
4. Verify **application compatibility** after restore.
5. Measure documented **RPO and RTO**.
### Numerical targets
| Metric                               | Target                              |
| ------------------------------------ | ----------------------------------- |
| RPO                                  | ≤ 15 minutes                        |
| RTO                                  | ≤ 60 minutes                        |
| Successful automated restores        | ≥ 3 consecutive                     |
| Integrity / checksum mismatches      | 0 (zero)                            |
| Backup stored only in source cluster | 0 (none)                            |
| Restore evidence                     | Tied to backup ID and candidate SHA |
### Exit criteria
- [ ] RPO ≤ 15 minutes.
- [ ] RTO ≤ 60 minutes.
- [ ] Three consecutive successful automated restores.
- [ ] Zero checksum or integrity mismatches across all restores.
- [ ] No backup is stored only in the source cluster.
- [ ] Restore evidence is tied to the backup ID and candidate SHA.
### Scoring effect
> **5.0 → 6.5**.
---
## 6. Section C — Proven Deployment and Rollback
### Goal
Deploy with a **build-once** pipeline and prove rollback works within the **60-minute RTO** with **zero data loss**.
### Implementation steps
1. Build the application image once and **promote the same signed digest** through all environments.
2. Implement **staging → canary → production** promotion.
3. Gate each rollout step with **health, SLI, error-rate, migration, and tenant-isolation checks**.
4. **Stop or roll back automatically** when any gate threshold fails.
5. Use **expand-contract migrations**; never apply a destructive migration that the previous application version cannot tolerate.
6. Prove the **previous application image works against the expanded schema** during the rollback window.
7. Keep **application rollback, data restore, and migration recovery** as separate, independent operations.
### Required evidence
- Two successful **production-like rollback rehearsals**.
- One rollback executed after an **intentionally failed canary**.
- **Zero data loss** across all rollback scenarios.
- Rollback decision and completion within **60-minute RTO**.
- No mutable image references (deployments must reference fixed digests).
- Deployment records tied to exact **source commit and artifact digest**.
### Exit criteria
- [ ] 2 successful production-like rollback rehearsals completed.
- [ ] 1 rollback executed after an intentionally failed canary.
- [ ] Zero data loss observed in all rollback runs.
- [ ] Rollback decision and completion within 60 minutes.
- [ ] No mutable image references exist.
- [ ] Deployment record is traceable to source and artifact digests.
### Scoring effect
> **6.5 → 7.2**.
---
## 7. Section D — Operational Observability
### Goal
Achieve 100% coverage of critical services and journeys with consistent metrics, logs, and traces, and zero alert-reference drift.
### Implementation steps
1. Load `layer-sli-rules-production.yml` into **Prometheus**.
2. Align **Layer 2** metric names with their declared **SLI selectors**.
3. Add **Layer 2 FastAPI tracing**.
4. Correct the **compose Prometheus configuration path**.
5. Align **Layer 6 labels** with their SLI selectors.
6. Instrument the **gateway and all L1–L6 services** consistently.
7. Propagate **W3C trace context** through HTTP, queues, and agent workflows.
8. Prevent tenant-sensitive data from entering metrics or traces (PII/data-redaction controls).
9. Create **SLOs** for all five critical journeys:
   - **j01** — Tenant onboarding
   - **j02** — Core value case
   - **j03** — Admin support
   - **j04** — Export and deletion
   - **j05** — Billing and entitlements
### Numerical targets
| Metric                                                         | Target      |
| -------------------------------------------------------------- | ----------- |
| Critical services emitting metrics, logs, and traces           | 100%        |
| Requests containing trace and correlation IDs                  | > 99%       |
| Critical journeys with recording rules, dashboards, and alerts | 100%        |
| Test-alert delivery time                                       | < 5 minutes |
| Alerts referencing a nonexistent metric or label               | 0           |
| Paging alerts with an attached runbook                         | 100%        |
| Alert and incident-response drill cadence                      | Monthly     |
### Exit criteria
- [ ] 100% of critical services emit metrics, logs, and traces.
- [ ] > 99% of requests contain trace and correlation IDs.
- [ ] 100% of critical journeys have recording rules, dashboards, and alerts.
- [ ] Test-alert delivery is under 5 minutes.
- [ ] No alert references a nonexistent metric or label.
- [ ] Every paging alert has an attached runbook.
- [ ] Monthly alert and incident-response drill is scheduled and executed.
### Scoring effect
> **7.2 → 8.0**.
---
## 8. Compliance and Validation
### Cross-cutting compliance gates
- **Tenant isolation:** every restore and ingress change must be proven tenant-scoped; cross-tenant read or write must fail closed.
- **Contract alignment:** any change to ingress, metric, or deployment behavior must be reflected in the OpenAPI contract and frontend types.
- **Auditability:** rollback decisions, restore results, and gateway authorization failures must be auditable and time-stamped.
- **Security:** mTLS/authenticated credentials only; no weakening of auth, RBAC, rate limiting, or governance middleware.
### Validation and automation procedures
- Wire every exit criterion into a CI gate; the gate must be **red until proven** and green only when evidence artifacts are attached.
- Run the **automated restore harness** on a fixed cadence (at least one per release candidate and monthly).
- Run ingress render tests and DAST on every overlay and on every promotion.
- Run **monthly alert and incident-response drills**; record drill duration and delivery metrics.
- Provide runbooks for every paging alert and production recovery path.
- Record all evidence with **attribute of source and digest** (backup ID, candidate SHA, image digest).
---
## 9. Risk and Mitigation
| Risk                                               | Mitigation                                                                                                      |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Gateway becomes the single point of failure        | Test gateway failure behavior, timeouts, retries, and rate limits (Section A); monitor and runbook (Section D). |
| Backup silently misses a database                  | Fail the backup when an expected database is missing; inventory must match topology (Section B).                |
| Rollback cannot tolerate the expanded schema       | Use expand-contract migrations; prove previous image works against expanded schema (Section C).                 |
| Alert references drift as metrics/labels change    | Align metric names and selectors; add drift check (Section D).                                                  |
| Restore loses derived state (Redis, vector, graph) | Rebuild derived state; validate it explicitly during restore (Section B).                                       |
---
## 10. Rollout and Automation Notes
- Apply **Section A first**, as it is the mandate for ingress convergence and closed-path enforcement; Sections B through D build on the closed, gateway-routed network.
- Each section ships with an automated validation gate; do not promote a section until its exit-criteria checklist is fully green.
- Rehearse one production rollback per major release cycle; keep rollback rehearsals in the CI evidence trail.
- Run restore and ingress validation from **certified staging**, and re-run the same tests in production before launch.

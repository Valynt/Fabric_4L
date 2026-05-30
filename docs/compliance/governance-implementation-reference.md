# Governance & Compliance Implementation Reference (SOC 2 / GDPR / HIPAA / CCPA)

## Purpose

This document is the audit-facing implementation reference that maps privacy/security controls to **implementation artifacts**, **tests**, and **CI evidence generation**.

- **Frameworks covered:** SOC 2 (Common Criteria), GDPR, HIPAA Security/Privacy/Breach Notification Rule obligations (when PHI is in scope), CCPA/CPRA.
- **Audience:** Security Engineering, Privacy Operations, Internal Audit, and service owners.
- **Companion document:** `docs/compliance/control-matrix.md`.
- **Last updated:** 2026-04-29.

---

## 1) Control-to-Implementation Mapping

## 0) Framework Applicability and Audit Boundary

| Framework | Applicable | Scope Boundary | Evidence Trigger |
| --- | --- | --- | --- |
| SOC 2 | Yes | All production services and shared platform controls. | Every release/PR through standard CI and operational review cadence. |
| GDPR | Yes | Any tenant/user personal data processing, including DSAR operations and retention workflows. | Every DSAR request + quarterly privacy control sampling. |
| HIPAA | Conditional Yes | Required for any tenant/environment where PHI is processed in covered-entity or business-associate contexts. | Tenant onboarding PHI classification + HIPAA-mode periodic audit checks. |
| CCPA/CPRA | Yes | California consumer personal information lifecycle and rights handling. | Consumer request handling + privacy control sampling. |

When HIPAA is not in scope for a tenant, HIPAA rows below remain implementation-ready and are activated by onboarding classification.

| Control Theme | GDPR / CCPA / SOC 2 | Implementation Artifacts (Code Paths) | Validation Tests | CI / Evidence Generation |
| --- | --- | --- | --- | --- |
| Identity, authn/authz, tenant boundary enforcement | GDPR Art. 5(1)(f), Art. 25, Art. 32; CCPA §1798.150; SOC 2 CC6.1/CC6.6/CC6.7 | `shared/identity/middleware.py`, `shared/identity/isolation.py`, `shared/identity/permissions.py` | `tests/integration/test_tenant_isolation_end_to_end.py`, `tests/integration/test_cross_layer_tenant_isolation.py` | `.github/workflows/pr-checks.yml`, `.github/workflows/security-gates.yml`, `make verify` |
| Audit immutability and accountability | GDPR Art. 5(2), Art. 30, Art. 33; CCPA accountability; SOC 2 CC7.2/CC7.3 | `shared/audit/models.py`, `shared/audit/emitter.py`, `services/layer4-agents/migrations/versions/003_add_audit_events.py` | `tests/integration/test_tenant_provisioning_audit.md` (procedure), migration-level verification during service tests | `make test-layer4`, PR checks with migration and test execution |
| Retention/deletion policy enforcement | GDPR Art. 5(1)(e), Art. 17; CCPA §1798.105; SOC 2 CC3.2/CC8.1 | `services/layer1-ingestion/src/shared/config.py`, `services/layer1-ingestion/src/shared/tasks.py` (`cleanup_old_content`) | `tests/contract/test_retention_deletion_contract.py` | `make verify` (contract test stage), CI test artifacts |
| DSAR access/export/delete process control | GDPR Art. 15/17/20; CCPA §1798.100/105/110; SOC 2 CC2.3/CC8.1 | `services/layer4-agents/src/layer4_agents/tenants/api/routes/tenants.py`, `services/layer4-agents/src/layer4_agents/tenants/api/routes/users.py`, `services/layer4-agents/src/layer4_agents/tenants/api/routes/api_keys.py`, `services/layer4-agents/src/layer4_agents/api/routes/analysis.py` | Layer/service integration tests under `tests/integration/` (tenant provisioning/isolation paths) + operational DSAR workflow below | PR checks + release checklist runbooks in `docs/troubleshooting/runbooks/infrastructure/release-checklist.md` |
| Change governance and contract integrity | GDPR Art. 24; SOC 2 CC1.2/CC5.2 | `packages/platform-contract/CONTRACT.md`, `docs/platform-contract/DEPRECATION_MAP.md`, `contracts/` | `tests/contract/` suite | `make verify`, contract gate tests in `tests/contract/gate/` |
| HIPAA PHI data flow + encryption controls | HIPAA 45 CFR §164.306(a), §164.312(a)(1), §164.312(e)(1); SOC 2 CC6.1/CC6.6 | `shared/identity/middleware.py`, `shared/identity/isolation.py`, `docs/ENVIRONMENT.md`, `k8s/envs/*`, `docs/secrets-management.md` | Integration tests for tenant isolation; deployment/promotion checklist verification for PHI environments | `.github/workflows/security-gates.yml`, `.github/workflows/pr-checks.yml`, deployment review records |
| HIPAA access auditing and minimum necessary access | HIPAA 45 CFR §164.312(b), §164.502(b), §164.514(d); SOC 2 CC6.7/CC7.2 | `shared/audit/models.py`, `shared/audit/emitter.py`, `services/layer4-agents/migrations/versions/003_add_audit_events.py`, `services/layer4-agents/migrations/versions/007_add_rls_policies.py` | Audit immutability + tenant access integration tests/procedures | `make test-layer4`, CI test logs, periodic access-review records |
| HIPAA incident response and breach assessment evidence | HIPAA 45 CFR §164.308(a)(6), §164.404-414; GDPR Art. 33-34; SOC 2 CC7.4 | `docs/runbooks/README.md`, `docs/runbooks/*`, shared audit artifacts for forensics | Incident tabletop drills and post-incident review artifacts | Incident tickets, postmortems, and governance review packets |

---

## 2) Data Classes and Retention/Deletion Policies by Subsystem

| Subsystem | Data Class | Examples | Default Retention | Deletion/Disposition Mechanism | Owner |
| --- | --- | --- | --- | --- | --- |
| Layer 1 Ingestion | Raw content and crawl metadata | Raw HTML, capture artifacts, extraction staging records | 30 days | `cleanup_old_content(days)` marks aged content as `DELETED`; default policy derived from `retention_days` setting | Layer 1 Engineering + Data Governance |
| Layer 2 Extraction | Intermediate extraction payloads | Ontology extraction results, transform intermediates | Environment/policy controlled; align to tenant contract | Job lifecycle cleanup and downstream persistence controls | Layer 2 Engineering |
| Layer 3 Knowledge | Knowledge graph + analytics operational records | Entity/relationship views, operational security telemetry | Service policy controlled; operational telemetry defaults to short-lived windows where configured | Service-level cleanup managers and tenancy controls | Layer 3 Engineering |
| Layer 4 Agents | Workflow state and tenant administration records | Agent workflow state, tenant/user/API-key lifecycle records | Lifecycle-bound + policy constrained | Deactivation/delete APIs; workflow state cleanup mechanisms | Layer 4 Engineering + Privacy Ops |
| Shared Audit | Immutable audit events | Security-relevant CRUD and governance actions | 7 years (baseline objective) | Append-only model + archival/retention process by operations | Security Engineering + SRE |
| Telemetry / Observability | Traces, metrics, logs | OpenTelemetry traces, app/service metrics | Per observability backend policy (short/medium-term) | Backend retention policies + log routing lifecycle | SRE |
| Backups / DR Artifacts | Database/object store snapshots | Postgres backups, object storage snapshots | As defined by DR policy and legal/compliance requirements | Backup expiry/rotation + documented recovery tests | Platform Engineering + SRE |

### Policy notes

1. Legal hold supersedes ordinary deletion windows.
2. Tenant-specific contractual obligations may require longer retention than defaults.
3. Deletion in one layer can require asynchronous downstream completion in dependent layers.

---

## 3) DSAR Workflow and Ownership

## 2.1 GDPR lawful basis, transfer, and SLA controls

- **Lawful basis:** captured at onboarding/contract intake and associated with tenant processing profile before activation.
- **DSAR workflow:** intake, identity verification, lawful-basis and legal-hold checks, execution, evidence capture, and closure.
- **Deletion/export SLAs:** acknowledge within 72 hours; deletion target within 30 days; export/access initial delivery or status within 7 days.
- **Cross-border transfer controls:** deployment-region and environment overlays in `k8s/envs/*` and service/environment configuration in `docs/ENVIRONMENT.md`; exceptions require Legal + Security approval and auditable record.

## 2.2 HIPAA PHI data flow and obligations (activated when PHI is in scope)

1. **PHI data flow controls:** PHI remains tenant-scoped across ingestion, storage, retrieval, and agent workflows via authenticated APIs and isolation utilities.
2. **Encryption controls:** TLS for transport and encrypted storage/backups are required for PHI-capable environments; secret/key lifecycle follows secrets-management policy.
3. **Access auditing:** all PHI-relevant administrative/data operations must map to immutable audit events and periodic audit review.
4. **Minimum necessary access:** role and tenancy constraints must limit access to least privilege needed for fulfillment/operations.
5. **Incident response:** PHI incidents require documented triage, breach assessment, and notification-decision timelines/evidence.

## 3.1 DSAR API Surfaces

- Tenant and user management: `services/layer4-agents/src/layer4_agents/tenants/api/routes/tenants.py`, `users.py`, `api_keys.py`.
- Export-related routes: `services/layer4-agents/src/layer4_agents/api/routes/analysis.py` and Layer 3 export surface in `services/layer3-knowledge/src/api/main.py`.

## 3.2 DSAR process flow

1. **Intake & identity verification** (Privacy Operations).
2. **Scope and lawful-basis/legal-hold determination** (Privacy Operations + Legal).
3. **Execution via APIs and approved operations** (Layer owners).
4. **Evidence collection and fulfillment log** (Security/SRE + Privacy Operations).
5. **Customer response and closure** (Privacy Operations).

## 3.3 RACI (condensed)

| DSAR Activity | Responsible | Accountable | Consulted | Informed |
| --- | --- | --- | --- | --- |
| Intake and identity verification | Privacy Operations | Privacy Lead | Support, Legal | Security |
| Access/export data retrieval | Layer Engineering owners | Product/Platform Engineering manager | Security, Privacy Ops | Support |
| Delete/deactivate execution | Layer Engineering owners | Privacy Lead | Legal, Security | Support |
| Audit evidence packaging | Security Engineering + SRE | Security Lead | Privacy Ops | Internal Audit |

---

## 4) Audit Evidence Generation Mapping

| Evidence Type | Script/Workflow | Output | Control Coverage |
| --- | --- | --- | --- |
| Full verification suite | `make verify` | Lint/type/test/contract/build logs | SOC 2 change management + control operation evidence |
| Agent behavior/eval evidence | `make evals` | Golden-trace evaluation output | Agent safety/quality governance support |
| Governance matrix change enforcement | `.github/scripts/check-control-matrix.sh` via PR checks | CI status + job logs | Documentation governance and control traceability |
| Security gate scans | `.github/workflows/security-gates.yml` | Security scan logs/artifacts | Vulnerability and secure SDLC controls |
| Release readiness checks | `docs/troubleshooting/runbooks/infrastructure/release-checklist.md` | Human-run checklist evidence | Production change governance |

---

## 5) Operational Review Cadence

- **Monthly:** retention/deletion exceptions, DSAR SLA attainment, authn/authz changes.
- **Quarterly:** full control mapping review and sampling of evidence artifacts.
- **Per material change:** update this document and `docs/compliance/control-matrix.md` in the same PR when control mappings shift.

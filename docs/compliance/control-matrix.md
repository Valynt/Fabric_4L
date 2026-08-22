# Compliance Control Matrix (SOC 2 / GDPR / HIPAA / CCPA)

## Purpose

This matrix maps major SOC 2, GDPR, HIPAA, and CCPA control themes to concrete **code**, **configuration**, and **operational process** evidence in Value Fabric.

- **Scope:** Current repository implementation.
- **Last reviewed:** 2026-08-21.
- **Update trigger:** Any PR that changes security/governance-sensitive files must also evaluate (and, when needed, update) this matrix. Evaluated and refreshed for Security & Tenancy Hardening (PR #1392) covering hostile multi-tenant fixtures, security exception lifecycle governance, canonical Infisical secrets hierarchy, and production fail-closed controls.

---


## Execution-to-Evidence Artifacts

To operationalize this matrix into audit-ready execution evidence:
- Evidence inventory matrix: `docs/compliance/evidence-inventory-matrix.md`
- HIPAA applicability decision record: `docs/compliance/hipaa-applicability-decision-record.md`
- Quarterly control attestation runbook: `docs/runbooks/compliance/quarterly-control-attestation.md`
- Automated CI/CD artifact generation: `.github/workflows/audit-evidence.yml` (`automated-control-evidence` job)

## Control Matrix

## Framework Applicability Matrix

| Framework | Applicability | Rationale | Primary Owner |
| --- | --- | --- | --- |
| SOC 2 | Applicable | Value Fabric operates multi-tenant software services with security, availability, and processing integrity obligations that require auditable common-criteria control operation. | Security Engineering + Platform Engineering |
| GDPR | Applicable | The platform processes personal data for identifiable users/administrators and supports tenant operations that can include EU/EEA data subjects, requiring GDPR program controls and DSAR workflows. | Privacy Operations + Legal |
| HIPAA | Applicable (conditional by tenant workload) | HIPAA applies when a tenant workload includes protected health information (PHI) and Value Fabric is used in a covered-entity/business-associate context. Even where a tenant is non-healthcare, controls are documented to support auditable HIPAA-mode operation when PHI is in scope. | Privacy Operations + Security Engineering |
| CCPA/CPRA | Applicable | Tenant and user records can include California resident personal information; consumer rights and deletion/access requirements are therefore in scope. | Privacy Operations + Legal |

### HIPAA applicability operating note

HIPAA controls are mandatory for any tenant/environment handling PHI. Tenant onboarding and contract review must explicitly classify PHI scope before production go-live and trigger HIPAA-mode evidence collection.

| Framework / Control | Requirement Summary | Implementation & Configuration Evidence | Process / Operational Evidence | Owner | Review Cadence |
| --- | --- | --- | --- | --- | --- |
| GDPR Art. 5(1)(f), Art. 32 / CCPA §1798.150 / SOC 2 CC6.1, CC6.6 | Protect confidentiality and integrity of personal data in transit and at service boundaries. | Unified auth + tenant-resolution middleware in `shared/identity/middleware.py` enforces JWT/API key validation and resolves tenant context before protected requests proceed; `X-Tenant-ID` is mandatory for API access in docs. | Security controls are exercised in CI via PR and security workflows (`pr-checks.yml`, `security-gates.yml`) for lint/tests/scans and dependency checks. | Security Engineering | Monthly + per material auth change |
| GDPR Art. 5(1)(c), Art. 25 / CCPA data minimization principles / SOC 2 CC6.7 | Enforce tenant isolation and least data exposure across shared infrastructure. | Tenant isolation utilities in `shared/identity/isolation.py` (`TenantScopedMixin`, `TenantScopedCypher`, `tenant_cache_key`) plus PostgreSQL RLS migration `007_add_rls_policies.py` enforcing tenant filters at DB level. | Architecture and implementation plan document tenant isolation expectations and rollout baseline in `docs/phase3-implementation-plan.md`. | Platform Engineering | Monthly |
| GDPR Art. 30, Art. 5(2), Art. 33 / CCPA accountability / SOC 2 CC7.2, CC7.3 | Maintain immutable audit trail for security/compliance-relevant actions. | `003_add_audit_events.py` creates `audit_events` and DB trigger to block UPDATE/DELETE; shared audit models/emitter in `shared/audit/models.py` and `shared/audit/emitter.py` standardize action taxonomy and structured logging. | Incident/ops runbooks under `docs/runbooks/` + runbook index (`docs/runbooks/README.md`) provide investigation and response playbooks that rely on trace/audit data. | Security Engineering + SRE | Monthly + after incident |
| GDPR Art. 15 / CCPA §1798.100, §1798.110 / SOC 2 CC2.3 | DSAR **Access**: provide data subject access to data associated with an account/tenant. | Tenant/user read paths in Layer 4 tenant API (`src/tenants/api/routes/tenants.py`, `users.py`) provide controlled retrieval under role checks; API auth contract and tenant header requirements documented in `docs/API_REFERENCE.md`. | DSAR access request workflow: (1) verify requester identity, (2) retrieve scoped records via tenant/user APIs, (3) log fulfillment decision in audit trail. This procedural workflow is governed by this matrix and security review records. | Privacy Operations + Tenant Admin Support | Quarterly tabletop + monthly spot-check |
| GDPR Art. 17 / CCPA §1798.105 / SOC 2 CC8.1 | DSAR **Delete**: support deletion/deactivation and enforce downstream deletion windows. | Soft-delete/deactivation APIs for tenants/users/API keys in Layer 4 (`tenants.py`, `users.py`, `api_keys.py`) with service implementations in `tenants/service.py`; ingestion cleanup task `cleanup_old_content(days=30)` in `layer1-ingestion/src/shared/tasks.py` marks expired records deleted. | Deletion SLA: acknowledge request within 72h, complete application-level deletion/deactivation within 30 days unless legal hold applies; unresolved items escalated through on-call and runbook process. | Privacy Operations + Application Engineering | Monthly metrics review |
| GDPR Art. 20 / CCPA portability expectation / SOC 2 CC2.3 | DSAR **Export/Portability**: provide user-consumable export of subject-associated artifacts where supported. | Export paths exist in Layer 4 analysis/tooling (`src/api/routes/analysis.py` export endpoint, `src/tools/document_export.py`) and Layer 3 export proxy (`layer3-knowledge/src/api/main.py` `/v1/documents/export`). | Export SLA: deliver first export package or status update within 7 days of validated request; failures routed via workflow/incident runbooks (`docs/runbooks/workflow-stalled.md`, `high-error-rate.md`). | Product Engineering + Privacy Operations | Monthly |
| GDPR Art. 5(1)(e), Art. 24 / CCPA retention disclosures / SOC 2 CC3.2 | Define and enforce retention/deletion windows. | Layer 1 compliance settings include `retention_days=30` and `audit_log_retention_years=7` in `layer1-ingestion/src/shared/config.py`; model-level retention fields in `src/shared/models.py`; backup/security analytics cleanup use retention configs in Layer 3 managers. | Retention/deletion SLA baseline: 30-day default operational data retention unless overridden by policy; 7-year audit retention; changes require policy + matrix update in PR. | Data Governance | Quarterly |
| GDPR Chapter V (cross-border transfers) / CCPA service provider safeguards / SOC 2 CC9.2 | Control data residency and cross-region handling. | Deployment model supports environment-specific configuration (`docs/ENVIRONMENT.md`) and Kubernetes deployable compositions (`k8s/deployments/*`) built from env overlays (`k8s/envs/*`) + routing stacks (`k8s/routing/*`) allowing region-specific cluster deployments and data-store pinning; S3 region is configurable via `LAYER1_S3_REGION`. | Data residency handling: tenant residency requirement captured at onboarding, mapped to deployment target/region, and validated during environment promotion review; exceptions require security + legal sign-off. | Platform Engineering + Legal/Privacy | Quarterly + before new region launch |
| GDPR Art. 28, Art. 32 / CCPA vendor safeguards / SOC 2 CC1.2, CC5.2 | Govern secrets and third-party access. | Secrets management guidance in `docs/secrets-management.md` and runbook `docs/runbooks/alertmanager-secret-management.md`; repo guardrails prohibit committed secrets (AGENTS + CI secret scans in `security-gates.yml`). | Rotational and incident procedures documented in secrets runbooks; periodic checks via CI security jobs and manual review. | Security Engineering | Monthly |
| HIPAA 45 CFR §164.312(a)(1), §164.312(e)(1), §164.306(a) / SOC 2 CC6.1, CC6.6 | PHI confidentiality controls: strong access control and encryption for PHI in transit/at rest. | Authn/z and tenant boundary controls: `shared/identity/middleware.py`, `shared/identity/isolation.py`; transport boundary controls and deployment configuration in `docs/ENVIRONMENT.md`, `k8s/envs/*`; storage security baseline and secrets handling in `docs/secrets-management.md`. | HIPAA-mode configuration review at tenant onboarding and environment promotion; evidence packaged via CI/security run logs and deployment review records. | Security Engineering + Platform Engineering | Per PHI tenant onboarding + quarterly |
| HIPAA 45 CFR §164.312(b), §164.308(a)(1)(ii)(D) / SOC 2 CC7.2, CC7.3 | Audit controls for systems handling PHI. | Immutable audit event model and emitter: `shared/audit/models.py`, `shared/audit/emitter.py`, DB immutability migration `services/layer4-agents/migrations/versions/003_add_audit_events.py`. | Audit review workflow uses runbooks in `docs/runbooks/` and monthly sampling of PHI-relevant administrative actions; findings tracked through incident process. | Security Engineering + SRE | Monthly + post-incident |
| HIPAA 45 CFR §164.502(b), §164.514(d) / GDPR Art. 5(1)(c) / SOC 2 CC6.7 | Minimum necessary access to regulated data. | Tenant-scoped access patterns in `shared/identity/isolation.py`; role-aware tenant/user endpoints in `services/layer4-agents/src/layer4_agents/tenants/api/routes/tenants.py` and `users.py`; RLS enforcement migration `services/layer4-agents/migrations/versions/007_add_rls_policies.py`. | Access approvals and exception handling documented in onboarding/review workflow; quarterly access review includes minimum-necessary attestation for PHI tenants. | Privacy Operations + Security Engineering | Quarterly |
| HIPAA 45 CFR §164.308(a)(6), §164.404-414 / GDPR Art. 33-34 / SOC 2 CC7.4 | Security incident response and breach notification obligations for regulated data. | Operational incident runbooks index and playbooks in `docs/runbooks/README.md` and `docs/runbooks/*`; immutable audit trail supports investigation chain-of-custody. | Incident workflow enforces triage, containment, breach-assessment, and notification decision logging; timing obligations tracked in incident ticket and postmortem artifacts. | SRE + Security Engineering + Privacy Operations | Per incident + quarterly tabletop |

---

## DSAR Workflow Definitions

### GDPR lawful basis and rights handling

- **Lawful basis capture:** Tenant onboarding and contractual intake record intended processing basis (e.g., contract performance, legitimate interests, consent where required) and retention expectations before data activation.
- **Rights workflow linkage:** Access (Art. 15), deletion (Art. 17), and portability/export (Art. 20) workflows below are the operational DSAR paths; each request must log identity verification outcome, lawful-basis/hold checks, and fulfillment status in audit artifacts.
- **Cross-border transfer control:** Region placement and transfer constraints follow environment/deployment controls in `docs/ENVIRONMENT.md`, `k8s/envs/*`, and routing/deployment manifests under `k8s/`; transfer exceptions require Legal + Security approval.

### 1) Access workflow

1. Validate requester identity and tenant association.
2. Determine scope (tenant-level, user-level, timeframe).
3. Retrieve records through tenant-scoped APIs and approved read models.
4. Capture decision + fulfillment metadata in audit logs.

### 2) Delete workflow

1. Validate legal basis and hold status.
2. Execute tenant/user/key deactivation or delete operations via approved APIs.
3. Trigger/verify scheduled cleanup paths (retention jobs, storage cleanup).
4. Confirm completion or partial completion with rationale.

### 3) Export workflow

1. Validate requester identity and export scope.
2. Generate export package via document/API export endpoints.
3. Deliver through approved secure channel.
4. Log completion, checksum/manifest reference, and operator.

---

## Retention and Deletion SLA Baseline

| Data Class | Baseline SLA | Evidence |
| --- | --- | --- |
| Raw ingestion content | 30-day retention default; deleted/marked deleted after expiry job window. | `layer1-ingestion/src/shared/config.py`, `layer1-ingestion/src/shared/tasks.py` |
| Audit events | 7-year retention objective (archival process externalized). | `layer4-agents/migrations/versions/003_add_audit_events.py`, `layer1-ingestion/src/shared/config.py` |
| Security/analytics operational telemetry | 30-day retention defaults in cleanup-capable managers. | `layer3-knowledge/src/security/monitor.py`, `layer3-knowledge/src/analytics/manager.py` |

### GDPR DSAR SLA commitments

- **Request acknowledgment:** within 72 hours.
- **Deletion fulfillment target:** within 30 days (unless legal hold or statutory extension applies).
- **Export/access delivery target:** first package or actionable status within 7 days.

### HIPAA PHI handling baseline (when applicable)

1. PHI data flow must remain tenant-scoped from ingestion through Layer 4 operations, with authenticated service-to-service paths only.
2. Encryption is required in transit and at rest for PHI-bearing systems, with key/secret handling governed by secrets-management controls.
3. Access to PHI must follow minimum-necessary principles and be auditable via immutable event logging.
4. Incident response for PHI events must include breach-assessment and notification decision records.

---

## Control Ownership Model

- **Security Engineering:** authentication, authorization, audit integrity, security gates.
- **Platform Engineering:** tenancy isolation, deployment boundary controls, residency placement.
- **Privacy Operations:** DSAR intake/fulfillment governance and legal hold coordination.
- **Data Governance:** retention policy lifecycle and evidence review.
- **SRE:** runbook quality and incident response evidence continuity.

---

## PR / CI Enforcement

A CI policy check now enforces that PRs touching security/governance-sensitive paths also update this control matrix (or explicitly choose files outside the policy scope).

- Check script: `.github/scripts/check-control-matrix.sh`
- Workflow integration: `.github/workflows/pr-checks.yml` (`governance-docs-check` job)

# Operators' Runbook Index

> **Audience:** On-call engineers, SREs, release managers.  
> **Canonical runbook directory:** [`docs/runbooks/`](../runbooks/).
> Other runbook-like directories (`docs/operations/`, `docs/operational/`,
> `docs/deployment/`) are retained for historical / cross-link reasons and are
> indexed here, but new runbooks should land under `docs/runbooks/`.

This page is a single jumping-off point. It does **not** duplicate runbook
content; it lists every operator-facing document with a one-line purpose so
you can find the right page fast under incident pressure.

---

## docs/runbooks/ (canonical)

| File | Purpose |
| ---- | ------- |
| [README.md](../runbooks/README.md) | Runbook directory overview and conventions. |
| [backup-disaster-recovery.md](../runbooks/backup-disaster-recovery.md) | Backup cadence, restore drill, RPO/RTO posture. |
| [deployment-rollout-and-rollback.md](../runbooks/deployment-rollout-and-rollback.md) | Rolling deploy, canary, and rollback procedure across all six layers. |
| [compliance/](../runbooks/compliance/) | Compliance-specific operator procedures. |
| [operational/](../runbooks/operational/) | Day-2 operational runbooks (scaling, capacity, on-call). |

---

## docs/operations/ (operational catalogue)

These pages predate the consolidation under `docs/runbooks/` and remain the
source of truth for the topics below.

| File | Purpose |
| ---- | ------- |
| [README.md](../operations/README.md) | Operations directory landing page. |
| [RUNBOOK.md](../operations/RUNBOOK.md) | Cross-layer incident response runbook. |
| [RELEASE_RUNBOOK.md](../operations/RELEASE_RUNBOOK.md) | Release-window coordination procedure. |
| [ALERTMANAGER.md](../operations/ALERTMANAGER.md) | Alertmanager configuration, routing, silencing. |
| [SLOs.md](../operations/SLOs.md) | Service-level objectives per layer. |
| [SECURITY_HARDENING.md](../operations/SECURITY_HARDENING.md) | Production security hardening checklist. |
| [NETWORK_POLICY_EXCEPTIONS.md](../operations/NETWORK_POLICY_EXCEPTIONS.md) | Documented Kubernetes NetworkPolicy exceptions. |
| [VAULT_SETUP.md](../operations/VAULT_SETUP.md) | Vault / ExternalSecrets bootstrap. |
| [keycloak-integration.md](../operations/keycloak-integration.md) | Identity provider integration runbook. |
| [escalation-policy-and-drills.md](../operations/escalation-policy-and-drills.md) | On-call escalation matrix and drill schedule. |
| [severity-escalation-policy.md](../operations/severity-escalation-policy.md) | Severity classification + escalation rules. |
| [postmortem-template.md](../operations/postmortem-template.md) | Postmortem document template. |
| [mtta-mttr-reporting.md](../operations/mtta-mttr-reporting.md) | MTTA / MTTR reporting cadence. |
| [reliability-policy.md](../operations/reliability-policy.md) | Reliability policy and error-budget rules. |
| [operational-kpis-scorecard.md](../operations/operational-kpis-scorecard.md) | KPI scorecard for the platform. |
| [COMMAND_REFERENCE.md](../operations/COMMAND_REFERENCE.md) | Common operator commands. |
| [runbook-overview.md](../operations/runbook-overview.md) | Index of operations-area runbooks. |
| [layer5-slo-phase4-gate.md](../operations/layer5-slo-phase4-gate.md) | Layer 5 SLO promotion gate. |
| [ci-workflow-consolidation.md](../operations/ci-workflow-consolidation.md) | CI workflow consolidation reference. |
| [critical-gates-ownership.md](../operations/critical-gates-ownership.md) | Ownership of critical readiness gates. |
| [data-intelligence-layer-scope.md](../operations/data-intelligence-layer-scope.md) | Scope of the data-intelligence layer. |
| [legacy-debt-baseline-overrides.md](../operations/legacy-debt-baseline-overrides.md) | Legacy-debt baseline overrides. |
| [migration-verification-checklist.md](../operations/migration-verification-checklist.md) | Migration verification checklist. |
| [salesforce-crm-runbook.md](../operations/salesforce-crm-runbook.md) | Salesforce CRM integration runbook. |
| [salesforce-crm/](../operations/salesforce-crm/) | Salesforce CRM integration details. |
| [tenant-management-master-plan.md](../operations/tenant-management-master-plan.md) | Tenant management master plan. |
| [tenant-management-phase-1-rls-hardening.md](../operations/tenant-management-phase-1-rls-hardening.md) | Phase 1: RLS hardening. |
| [tenant-management-phase-1-rls-hardening-rescoped.md](../operations/tenant-management-phase-1-rls-hardening-rescoped.md) | Phase 1 (rescoped). |
| [tenant-management-phase-2-provisioning.md](../operations/tenant-management-phase-2-provisioning.md) | Phase 2: provisioning. |
| [tenant-management-phase-3-control-plane.md](../operations/tenant-management-phase-3-control-plane.md) | Phase 3: control plane. |
| [tenant-management-remediation-plan.md](../operations/tenant-management-remediation-plan.md) | Tenant management remediation plan. |
| [tenant-management-remediation-verification.md](../operations/tenant-management-remediation-verification.md) | Tenant management remediation verification. |
| [tenant-oidc-configuration.md](../operations/tenant-oidc-configuration.md) | Tenant OIDC configuration. |
| [evidence/](../operations/evidence/) | Operational evidence artefacts. |
| [layer6/](../operations/layer6/) | Layer 6 operational documents. |

---

## docs/operational/

| File | Purpose |
| ---- | ------- |
| [game-day-schedule.md](../operational/game-day-schedule.md) | Game-day exercise schedule. |

---

## docs/deployment/

| File | Purpose |
| ---- | ------- |
| [SECURITY_KEYS_SETUP.md](../deployment/SECURITY_KEYS_SETUP.md) | Production security-key setup procedure. |

---

## Cross-cutting references

- [docs/LAUNCH_RUNBOOK.md](../LAUNCH_RUNBOOK.md) — production launch control document (active).
- [SECURITY.md](../../SECURITY.md) — repository security posture.
- [docs/security/](../security/) — security playbooks.
- [docs/PRODUCTION_READINESS_CHECKLIST.md](../PRODUCTION_READINESS_CHECKLIST.md) — readiness gate checklist.
- [docs/readiness/](../readiness/) — current readiness state.

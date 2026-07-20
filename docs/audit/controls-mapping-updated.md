# Updated SOC2/ISO27001 Controls Mapping

**Status:** Partially stale — audit note added 2026-07-18. Several evidence paths below are shorthand or point to non-existent files; canonical paths are noted where known.

## Overview

This document provides an updated mapping of Value Fabric platform controls to SOC 2 Type II and ISO 27001:2022 requirements, including Phase 5 audit readiness controls.

## SOC 2 Trust Services Criteria

### CC6.1 - Logical Access Security

| Control | Implementation | Evidence Location | Test Coverage |
|---------|---------------|-------------------|---------------|
| **CC6.1.1** | Unique user IDs via OIDC JWT | `packages/shared/src/value_fabric/shared/identity/middleware.py` | ✅ Unit + Integration tests |
| **CC6.1.2** | Strong authentication (MFA via IdP) | IdP configuration | ✅ SSO integration tests |
| **CC6.1.3** | Role-based access control | `packages/shared/src/value_fabric/shared/identity/permissions.py`, `policy_registry.py` | ✅ `tests/security/test_rbac.py` |
| **CC6.1.4** | Least privilege service accounts | `k8s/base/*.yaml` | ✅ Security contexts, read-only root FS |
| **CC6.1.5** | Quarterly access audits | `scripts/access_review.py` *(path does not exist; process tracked in `docs/operations/`)* | ⚠️ Path needs owner |

### CC6.2 - Access Removal

| Control | Implementation | Evidence Location |
|---------|---------------|-------------------|
| **CC6.2.1** | Timely removal | Offboarding checklist in `docs/operations/` |
| **CC6.2.2** | Automated revocation | Token blacklisting via Redis |

### CC6.3 - Access Control Changes

| Control | Implementation | Evidence Location | Audit Trail |
|---------|---------------|-------------------|-------------|
| **CC6.3.1** | Change authorization | CODEOWNERS + PR approval | Git history, PR logs |
| **CC6.3.2** | Change logging | Audit logs | `layer5-ground-truth/audit/` |

### CC6.4 - Logical Access Monitoring

| Control | Implementation | Evidence Location |
|---------|---------------|-------------------|
| **CC6.4.1** | Failed access logging | `packages/shared/src/value_fabric/shared/logging/` |
| **CC6.4.2** | Suspicious activity alerts | Prometheus alerts in `monitoring/alerting/` |

### CC6.5 - Logical Access Testing

| Control | Implementation | Evidence Location | Phase 5 Addition |
|---------|---------------|-------------------|------------------|
| **CC6.5.1** | Multi-tenant isolation | `SecurityMiddleware` | ✅ `tests/security/test_cross_layer_tenant_isolation_matrix.py` (canonical tenant-isolation suite); `tests/chaos/tenant-isolation-loadtest.py` does not exist |
| **CC6.5.2** | Race condition detection | Tenant validation | ✅ Tenant-isolation hostile tests; `tests/chaos/tenant-race-condition-test.py` does not exist |

### CC7.1 - Security Operations

| Control | Implementation | Evidence Location | Test Frequency |
|---------|---------------|-------------------|----------------|
| **CC7.1.1** | Threat detection | SecurityMiddleware, WAF | ✅ Continuous |
| **CC7.1.2** | Vulnerability scanning | Trivy/Grype in CI | ✅ Weekly scheduled |
| **CC7.1.3** | Patch management | Dependabot, Renovate | ✅ Daily checks |
| **CC7.1.4** | Penetration testing | ZAP, Nikto | ✅ Weekly + On-demand |

### CC7.2 - Security Incident Detection

| Control | Implementation | Evidence Location |
|---------|---------------|-------------------|
| **CC7.2.1** | Incident detection | PagerDuty integration |
| **CC7.2.2** | Incident response | `RUNBOOK.md` |
| **CC7.2.3** | Incident documentation | Post-incident reviews in `docs/incidents/` |

### CC7.3 - Security Incident Response

| Control | Implementation | Evidence Location |
|---------|---------------|-------------------|
| **CC7.3.1** | Response procedures | `RUNBOOK.md`, escalation policy |
| **CC7.3.2** | Response testing | Quarterly incident drills |
| **CC7.3.3** | Response metrics | MTTA/MTTR reporting |

### A1.1 - Availability

| Control | Implementation | Evidence Location | Phase 5 Addition |
|---------|---------------|-------------------|------------------|
| **A1.1.1** | System monitoring | Prometheus/Grafana | ✅ SLO dashboards |
| **A1.1.2** | Capacity planning | HPA configurations | ✅ Auto-scaling tests |
| **A1.2.1** | Backup procedures | Database backup docs | ✅ Recovery time objectives |
| **A1.2.2** | Recovery testing | Chaos experiments | ✅ `k8s/chaos/litmus-experiments/` |

## ISO 27001:2022 Annex A Controls

### A.5 - Organizational Controls

| Control | Title | Implementation | Evidence |
|---------|-------|----------------|----------|
| **A.5.1** | Policies for info security | `SECURITY.md`, `AGENTS.md` | Policy documents |
| **A.5.2** | Information security roles | CODEOWNERS, team structure | GitHub roles |
| **A.5.7** | Threat intelligence | THREAT_MODEL.md | Updated annually |
| **A.5.8** | Project management security | Security gates in CI | PR workflow |

### A.6 - People Controls

| Control | Title | Implementation |
|---------|-------|----------------|
| **A.6.1** | Screening | HR process (external) |
| **A.6.2** | Terms of employment | Security clauses in contracts |
| **A.6.3** | Information security awareness | Security training, `SECURITY.md` |

### A.7 - Physical Controls

| Control | Title | Implementation |
|---------|-------|----------------|
| **A.7.1** | Physical security perimeters | Cloud provider (AWS/GCP/Azure) |
| **A.7.2** | Physical entry controls | Cloud provider |

### A.8 - Technological Controls

| Control | Title | Implementation |
|---------|-------|----------------|
| **A.8.1** | User endpoint devices | BYOD policy, MDM (external) |
| **A.8.2** | Privileged access rights | Least privilege RBAC |

### A.9 - Access Controls

| Control | Title | Implementation | Test Evidence |
|---------|-------|----------------|---------------|
| **A.9.1** | Access to networks | NetworkPolicies, VPN | ✅ `k8s/base/network-policies/` (directory, not `network-policies.yaml`) |
| **A.9.2** | Access to systems | RBAC, JWT validation | ✅ RBAC tests |
| **A.9.3** | Access to apps | OIDC, role-based permissions | ✅ SSO tests |
| **A.9.4** | System access control | `shared/identity/` | ✅ Middleware tests |
| **A.9.5** | Secure log-on | OIDC with strong auth | ✅ Auth tests |
| **A.9.6** | Privilege management | Least-privilege IAM | ✅ Access reviews |
| **A.9.7** | Access to source code | CODEOWNERS, branch protection | ✅ Git history |

### A.10 - Cryptography

| Control | Title | Implementation |
|---------|-------|----------------|
| **A.10.1** | Cryptographic controls | TLS 1.3, AES-256 encryption |
| **A.10.2** | Cryptographic key management | External key management (HashiCorp Vault) |

### A.12 - Operations Security

| Control | Title | Implementation | Phase 5 Evidence |
|---------|-------|----------------|------------------|
| **A.12.1** | Operational procedures | Runbooks, SOPs | ✅ `RUNBOOK.md` |
| **A.12.2** | Change management | GitOps, PR workflow | ✅ Git history |
| **A.12.3** | Capacity management | HPA, monitoring | ✅ Chaos tests |
| **A.12.4** | Separation of environments | Namespace isolation | ✅ K8s policies |
| **A.12.5** | Change management | ArgoCD, manual gates | ✅ GitOps config |
| **A.12.6** | Technical compliance | Security scanning | ✅ CI workflows |

### A.14 - System Acquisition & Development

| Control | Title | Implementation |
|---------|-------|----------------|
| **A.14.1** | Security requirements | Security requirements in specs |
| **A.14.2** | Secure development | Pre-commit hooks, SAST/DAST |
| **A.14.3** | Test data protection | Synthetic data generation |

### A.16 - Incident Management

| Control | Title | Implementation | Phase 5 Evidence |
|---------|-------|----------------|------------------|
| **A.16.1** | Incident management responsibilities | Escalation policy | ✅ Escalation docs |
| **A.16.2** | Incident reporting | Alerting channels | ✅ PagerDuty config |
| **A.16.3** | Incident assessment | MTTA/MTTR metrics | ✅ Reporting |
| **A.16.4** | Incident response | Runbook procedures | ✅ `RUNBOOK.md` |

### A.17 - Business Continuity

| Control | Title | Implementation | Phase 5 Evidence |
|---------|-------|----------------|------------------|
| **A.17.1** | Business continuity planning | DR policy | ✅ `docs/reliability/dr-policy.md` |
| **A.17.2** | Business continuity procedures | Recovery procedures | ✅ Runbooks |
| **A.17.3** | ICT readiness | Chaos testing | ✅ Litmus experiments |

### A.18 - Compliance

| Control | Title | Implementation | Phase 5 Evidence |
|---------|-------|----------------|------------------|
| **A.18.1** | Legal requirements | Compliance review | ✅ `COMPLIANCE.md` |
| **A.18.2** | Intellectual property | License compliance | ✅ License headers |

## Phase 5: New Controls Coverage

### Penetration Testing (CC7.1.4, A.14.2)

| Tool | Coverage | Evidence |
|------|----------|----------|
| OWASP ZAP | SQLi, XSS, CSRF, auth bypass | `tests/penetration/zap-full-scan.py` |
| Nikto | Server config, dangerous files | `tests/penetration/nikto-scan.sh` |
| Scheduled Tests | Weekly automated scans | `.github/workflows/penetration-testing.yml` |

### Chaos Engineering (A.12.3, A.17.3)

| Experiment | Target | Success Criteria | Evidence |
|------------|--------|------------------|----------|
| Pod Delete | All 6 layers | Recovery <30s | Litmus + PodDisruptionBudget |
| Network Partition | L3-L4 | Graceful degradation | Network policies + probes |
| CPU Stress | L4 Agents | Auto-scale triggers | HPA + metrics |
| Memory Stress | L2 | OOM handling | Resource limits + restart |
| Auto-scaler | L1 | Scale-up <60s | HPA validation |

### Multi-Tenant Isolation (CC6.5, A.9)

| Test Type | Coverage | Evidence |
|-----------|----------|----------|
| Realistic Workloads | User journey simulation | `tenant-isolation-loadtest.py` |
| Stress Tests | 1000+ concurrent requests | Load testing |
| Race Conditions | Timing attacks | `tenant-race-condition-test.py` |
| Header Spoofing | JWT validation | SecurityMiddleware |

## Evidence Bundle Structure

```
audit-evidence-YYYYMMDD/
├── access-control/
│   ├── rbac-summary.json
│   ├── CODEOWNERS
│   └── access-review-report.json
├── change-management/
│   ├── commit-history.csv
│   ├── pr-merge-history.json
│   └── pre-commit-config.yaml
├── security-operations/
│   ├── penetration-test-summary.json
│   ├── vulnerability-scanning.json
│   └── security-gates.yml
├── availability/
│   ├── chaos-testing-evidence.json
│   ├── litmus-experiments/
│   └── gitops/
├── incident-response/
│   ├── RUNBOOK.md
│   ├── escalation-policy-and-drills.md
│   └── mtta-mttr-reporting.md
├── policies/
│   ├── SECURITY.md
│   ├── AGENTS.md
│   ├── COMPLIANCE.md
│   └── trust/
└── evidence-index/
    ├── index.json
    └── README.md
```

## Audit Evidence Summary

| Category | Files | Automated | Manual Review |
|----------|-------|-----------|---------------|
| Access Control | 3 | ✅ | Quarterly |
| Change Management | 4 | ✅ | Per release |
| Security Operations | 5+ | ✅ Weekly | Monthly |
| Availability | 10+ | ✅ Weekly | Quarterly |
| Incident Response | 4 | ✅ | Per incident |
| Policies | 10+ | ❌ | Annual review |

**Total Evidence Items:** 40+ files
**Automation Coverage:** 75%
**Evidence Retention:** 90 days minimum (SOC2), 3 years (ISO27001)

---
*Generated: Phase 5 Completion*
*Version: 2.0.0*

# Runbook — Value Fabric

> **This is a root-level entry point.** All detailed runbooks live in [`docs/runbooks/`](docs/runbooks/README.md).
>
> **Canonical runbook index:** [`docs/runbooks/00-runbook-index.md`](docs/runbooks/00-runbook-index.md)

---

## First 15 Minutes of Incident Response

1. **Assess severity** using the table below.
2. **Check service health:**
   ```bash
   curl -f http://localhost:8001/health  # Layer 1
   curl -f http://localhost:8002/health  # Layer 2
   curl -f http://localhost:8003/health  # Layer 3
   curl -f http://localhost:8004/health  # Layer 4
   curl -f http://localhost:8005/api/v1/health  # Layer 5
   kubectl get pods -n fabric-production
   ```
3. **Find the relevant runbook** in the index below.
4. **Escalate** if you cannot contain within 15 minutes.

---

## Severity Levels

| Level | Criteria | Response Time | Example |
|-------|----------|---------------|---------|
| **SEV-0** | Complete outage, data loss, security breach | 15 minutes | All services down, unauthorized data access |
| **SEV-1** | Major feature degradation, customer-visible | 1 hour | Graph queries failing, auth issues |
| **SEV-2** | Minor degradation, workarounds exist | 4 hours | Performance degradation, non-critical bugs |
| **SEV-3** | Cosmetic issues, documentation | 24 hours | UI glitches, typos |

---

## Runbook Directory

| Scenario | Severity | Runbook |
|----------|----------|---------|
| Service outage / SLO breach | SEV-1 | [`docs/runbooks/00-runbook-index.md`](docs/runbooks/00-runbook-index.md) |
| Tenant isolation failure | SEV-1 | [`docs/runbooks/00-runbook-index.md`](docs/runbooks/00-runbook-index.md) |
| Data breach response | SEV-1 | [`docs/runbooks/00-runbook-index.md`](docs/runbooks/00-runbook-index.md) |
| PostgreSQL HA and restore | SEV-1 | [`docs/runbooks/00-runbook-index.md`](docs/runbooks/00-runbook-index.md) |
| Neo4j HA, backup, restore | SEV-1 | [`docs/runbooks/00-runbook-index.md`](docs/runbooks/00-runbook-index.md) |
| CI Infisical OIDC recovery | SEV-2 | [`docs/runbooks/00-runbook-index.md`](docs/runbooks/00-runbook-index.md) |
| Enterprise OIDC / SSO incident | SEV-2 | [`docs/runbooks/00-runbook-index.md`](docs/runbooks/00-runbook-index.md) |
| Cloud provider outage | SEV-1 | [`docs/runbooks/00-runbook-index.md`](docs/runbooks/00-runbook-index.md) |
| Secret / credential expiration | SEV-2 | [`docs/security/secret-remediation-runbook.md`](docs/security/secret-remediation-runbook.md) |
| DR verification | Scheduled | [`docs/drills/DRILL-RUNBOOK.md`](docs/drills/DRILL-RUNBOOK.md) |
| Release deployment | Planned | [`docs/operations/RELEASE_RUNBOOK.md`](docs/operations/RELEASE_RUNBOOK.md) |
| Launch checklist | Planned | [`docs/LAUNCH_RUNBOOK.md`](docs/LAUNCH_RUNBOOK.md) |

---

## Rollback / Deploy Pointers

- **Kubernetes rollback:** `kubectl rollout undo deployment/<service> -n fabric-production`
- **Database migration rollback:** `alembic downgrade -1` (per service)
- **Feature flag kill switch:** See [`packages/feature-flags/src/kill-switch-spec.md`](packages/feature-flags/src/kill-switch-spec.md)
- **Full deployment guide:** [`docs/deployment/cloud-kubernetes-production.md`](docs/deployment/cloud-kubernetes-production.md)

---

## Escalation Placeholders

> **TODO:** Replace with real team contacts before production go-live.

| Role | Contact |
|------|---------|
| On-call SRE | `#sre-oncall` (Slack) |
| Incident Commander | `#incident-response` (Slack) |
| Security | `#security-incidents` (Slack) |
| Platform Engineering | `#platform-eng` (Slack) |

---

*Extracted from [`docs/runbooks/00-runbook-index.md`](docs/runbooks/00-runbook-index.md) and [`docs/operations/RUNBOOK.md`](docs/operations/RUNBOOK.md) during docs/refactor-methodology phase 4.*

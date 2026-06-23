---
status: active
last_reviewed: 2026-06-07
owner: platform-team
---

# Incident Response

This page defines the incident response protocol for the Value Fabric platform,
including severity classification, on-call responsibilities, initial response
playbooks, communication channels, escalation paths, and post-incident review
requirements.

## Severity Levels

Incidents are classified into three severity levels based on customer impact,
data integrity risk, and platform availability.

| Severity | Definition | Response Time | Resolution Target | Notification |
|---|---|---|---|---|
| **Critical (SEV-1)** | Complete platform outage, tenant isolation failure, data breach, or security compromise affecting production | 15 minutes | 4 hours | PagerDuty + Slack `#vf-alerts-critical` |
| **Warning (SEV-2)** | Degraded performance, partial feature unavailability, elevated error rates, or non-production security findings | 1 hour | 24 hours | Slack `#vf-alerts-warning` |
| **Info (SEV-3)** | Anomalies, capacity warnings, cost spikes, or non-urgent operational findings | 4 hours | 72 hours | Slack `#vf-alerts-info` |

!!! danger "Tenant isolation failures are always SEV-1"
    Any confirmed or strongly suspected cross-tenant data access, unauthorized
    tenant mutation, or bypass of tenant-scoped authorization is treated as
    SEV-1 regardless of perceived blast radius. Invoke the security runbook
    immediately.

### Severity Examples

| Scenario | Severity | Rationale |
|---|---|---|
| All Layer 4 agent workflows failing | SEV-1 | Core platform function unavailable |
| Single tenant cannot access own data | SEV-1 | Customer-impacting; may indicate isolation bug |
| Cross-tenant read detected in logs | SEV-1 | Security compromise; data integrity risk |
| Elevated 5xx rate on Layer 2 (>5%) | SEV-2 | Degraded service; partial impact |
| LLM cost spike >200% baseline | SEV-2 | Financial impact; potential abuse |
| Redis memory usage >80% | SEV-3 | Capacity warning; no immediate customer impact |
| Backup cronjob failed once | SEV-3 | Operational risk; recoverable if caught early |

## On-Call Responsibilities

### Primary On-Call (Platform Engineer)

- Acknowledge alerts within the defined response time for the severity level.
- Perform initial triage using this playbook and linked runbooks.
- Coordinate with the incident commander if escalation is required.
- Own communication updates until handoff or resolution.

### Secondary On-Call (Engineering Manager / Staff Engineer)

- Available for escalation within 30 minutes of contact.
- Assists with cross-team coordination, customer communication, and
  executive briefing for SEV-1 incidents.
- Activates war-room procedures if incident duration exceeds 2 hours.

### Security On-Call (Security Engineer)

- Mandatory participant for any SEV-1 with security or tenant isolation scope.
- Owns forensic preservation, log analysis, and post-incident security review.
- Decides whether to activate the data-breach or ransomware runbooks.

## Initial Response Playbook

### Step 1: Acknowledge and Triage (0–5 minutes)

1. Acknowledge the alert in PagerDuty or Slack.
2. Classify severity using the table above.
3. Open a dedicated incident Slack channel: `#inc-<YYYYMMDD>-<short-description>`.
4. Pin the alert link, runbook link, and initial timeline to the channel.

### Step 2: Assess Impact (5–15 minutes)

1. Check service health endpoints:
   ```bash
   # Quick health sweep (local or port-forwarded)
   for port in 8001 8002 8003 8004 8005 8006; do
     echo "Port $port: $(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health || echo DOWN)"
   done
   ```
2. Check Kubernetes pod status:
   ```bash
   kubectl get pods -n value-fabric
   kubectl get events -n value-fabric --sort-by='.lastTimestamp' | tail -20
   ```
3. Review recent deployments:
   ```bash
   kubectl get deployments -n value-fabric -o wide
   kubectl rollout history deployment/layer4-agents -n value-fabric
   ```
4. Query Prometheus for error-rate spikes:
   ```bash
   # Via port-forward to Prometheus
   kubectl port-forward -n value-fabric svc/prometheus 9090:9090
   curl -G 'http://localhost:9090/api/v1/query' \
     --data-urlencode 'query=sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)'
   ```

### Step 3: Contain and Mitigate (15–60 minutes)

1. **If a bad deployment is suspected**: roll back immediately.
   ```bash
   kubectl rollout undo deployment/layer4-agents -n value-fabric
   ```
2. **If a dependent service is down**: scale the affected service to zero
   temporarily to prevent cascading failure, then restore after dependency
   recovery.
   ```bash
   kubectl scale deployment/layer4-agents --replicas=0 -n value-fabric
   # After dependency recovers
   kubectl scale deployment/layer4-agents --replicas=2 -n value-fabric
   ```
3. **If tenant isolation is suspected**: freeze the affected endpoint or
   service, preserve logs, and page the security on-call.
   ```bash
   kubectl annotate deployment/layer4-agents -n value-fabric incident/security-hold="true"
   ```
4. **If infrastructure failure**: check PVCs, node status, and resource
   exhaustion.
   ```bash
   kubectl get pvc -n value-fabric
   kubectl top nodes
   kubectl top pods -n value-fabric
   ```

### Step 4: Communicate (ongoing)

- SEV-1: Update `#vf-alerts-critical` every 15 minutes until stable.
- SEV-2: Update `#vf-alerts-warning` every hour until stable.
- SEV-3: Update `#vf-alerts-info` at triage and at resolution.
- Customer-impacting SEV-1: Prepare status page update and customer notification
  with approval from Engineering Manager.

### Step 5: Resolve and Verify

1. Confirm all health endpoints return `200`.
2. Confirm error rates have returned to baseline (check Prometheus for 5 minutes).
3. Confirm tenant isolation tests pass:
   ```bash
   pnpm test:security:hostile
   make gate-tenant-isolation
   ```
4. Mark incident resolved in PagerDuty and pin the resolution summary in Slack.

## Communication Channels

| Channel | Purpose | Audience |
|---|---|---|
| `#vf-alerts-critical` | Real-time SEV-1 coordination | On-call, Incident Commander, Security |
| `#vf-alerts-warning` | SEV-2 updates and coordination | On-call, affected service owners |
| `#vf-alerts-info` | SEV-3 and non-urgent operational chatter | Platform team, SRE |
| `#vf-security-alerts` | Security-specific incidents and cross-tenant probes | Security on-call, CISO |
| `#vf-finops-alerts` | Cost anomalies and billing incidents | Finance, Platform |
| `#inc-<date>-<desc>` | Dedicated incident channel (ephemeral) | All responders |
| PagerDuty | SEV-1 paging and escalation tracking | Primary and secondary on-call |

!!! note "PagerDuty escalation policy"
    Page the primary on-call first. If unacknowledged after 15 minutes,
    escalate to the secondary on-call. If unacknowledged after 30 minutes,
    escalate to the Engineering Manager and Staff Engineer rotation.

## Escalation Paths

```text
Primary On-Call (Platform Engineer)
    └─ Unacknowledged 15m → Secondary On-Call (Eng Manager / Staff)
        └─ Unacknowledged 30m → Engineering Manager + Security On-Call (SEV-1 only)
            └─ Customer-impacting outage >2h → Executive briefing (CTO/VP Eng)
```

**Security-specific escalation**:

```text
Security On-Call
    └─ Confirmed data breach → Legal + Compliance + Executive within 1 hour
    └─ Ransomware or infra compromise → Isolate cluster, activate DR runbook
```

## Post-Incident Review Process

Every SEV-1 and SEV-2 incident requires a post-incident review (PIR) within
5 business days of resolution. SEV-3 incidents may be batched into a weekly
operational review at the discretion of the primary on-call.

### PIR Template

1. **Timeline** — Minute-by-minute account from alert to resolution.
2. **Impact Assessment** — Affected tenants, data volumes, error rates, duration.
3. **Root Cause** — Technical root cause with evidence (logs, traces, metrics).
4. **Contributing Factors** — Deployment practices, missing tests, observability gaps.
5. **Remediation Items** — Specific, assigned action items with due dates.
6. **Runbook Updates** — Any runbook changes required based on lessons learned.

### PIR Distribution

- Document in `ops/incident/postmortems/YYYY-MM-DD-<incident-name>.md`.
- Share in `#vf-alerts-warning` for SEV-2, `#vf-alerts-critical` for SEV-1.
- Review in the weekly Platform Sync meeting.
- Track remediation items in the engineering backlog with `incident-followup` label.

## Runbook References

| Scenario | Runbook | Location |
|---|---|---|
| Service down / unready | Service Down Runbook | `docs/troubleshooting/runbooks/infrastructure/service-down.md` |
| High error rate | High Error Rate Runbook | `docs/troubleshooting/runbooks/application/high-error-rate.md` |
| High LLM cost | LLM Cost Runbook | `docs/troubleshooting/runbooks/application/high-llm-cost.md` |
| Tenant isolation failure | Tenant Isolation Failure Runbook | `docs/troubleshooting/runbooks/incident/tenant-isolation-failure.md` |
| Data breach | Data Breach Response Runbook | `docs/troubleshooting/runbooks/incident/data-breach-response.md` |
| Ransomware | Ransomware Response Runbook | `docs/troubleshooting/runbooks/incident/ransomware-response.md` |
| Cloud provider outage | Cloud Provider Outage Runbook | `docs/troubleshooting/runbooks/incident/cloud-provider-outage.md` |
| Formula approval blocked | Formula Approval Runbook | `docs/troubleshooting/runbooks/application/formula-approval.md` |

## Validation

Validate incident response documentation and workflow structure:

```bash
# Validate incident workflow structure and severity coverage
pnpm ops:incident:check

# Validate runbook completeness and link health
pnpm ops:runbooks:lint

# Run security and recovery tests
pnpm test:security
pnpm test:recovery
```

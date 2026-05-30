# Data Breach Response Runbook

Use this runbook for any suspected or confirmed unauthorized access to customer data, personal data, secrets, production systems, audit logs, or tenant-scoped records. Treat the incident as **SEV1** until Security downgrades it.

## Triggers

- Alert or log evidence of unauthorized access, exfiltration, privilege escalation, or abnormal data export.
- Customer report of seeing another tenant's data.
- Compromised credentials, API keys, service tokens, or signing keys.
- Security tooling reports malware, web shell activity, suspicious admin activity, or impossible travel.
- Evidence tampering, missing audit events, or unexpected changes to retention settings.

## Immediate response

1. **Declare SEV1** using [severity-classification.md](severity-classification.md) and open `#security-incidents`.
2. **Assign roles:** Incident Commander, Security Lead, Forensics Lead, Communications Lead, Legal/Privacy contact, and service Technical Lead.
3. **Preserve evidence before destructive actions:** export alert payloads, audit logs, access logs, IAM events, database logs, object-storage access logs, and relevant traces to immutable storage.
4. **Contain active access:** revoke suspicious sessions and tokens, disable compromised accounts, rotate exposed credentials, block malicious IPs, and pause risky automation.
5. **Protect tenants:** if tenant boundaries may be impacted, immediately follow [tenant-isolation-failure.md](tenant-isolation-failure.md).
6. **Start an evidence log:** record every action, timestamp, actor, and command in the incident channel or evidence document.

## Triage checklist

```bash
# Identify recent authentication anomalies.
kubectl logs -n value-fabric -l app=api-gateway --since=2h | rg -i "failed|forbidden|unauthorized|token|session|tenant"

# Search application logs for exfiltration and cross-tenant indicators.
kubectl logs -n value-fabric --all-containers --since=2h | rg -i "export|download|cross.tenant|tenant.isolation|admin|privilege|secret"

# Review recent Kubernetes changes.
kubectl get events -A --sort-by=.lastTimestamp | tail -100
kubectl get pods -A -o wide

# Capture currently active suspicious pods before deletion.
kubectl describe pod -n <namespace> <pod-name>
kubectl logs -n <namespace> <pod-name> --all-containers --since=24h
```

## Containment actions

| Scenario | Containment |
|---|---|
| Compromised user account | Disable account, revoke sessions, force password reset, require MFA re-enrollment, review recent activity. |
| Compromised API key or service token | Revoke key, rotate dependent secrets, redeploy workloads, invalidate caches, search logs for key usage. |
| Suspected database access | Disable suspicious principal, restrict network paths, snapshot database, preserve query logs, validate tenant filters. |
| Object storage exposure | Block public access, rotate access keys, snapshot bucket policy, export object access logs, identify downloaded objects. |
| Active exploit | Apply WAF/network block, scale down vulnerable endpoint only if safe, deploy hotfix or rollback, preserve exploit indicators. |

## Scope assessment

1. Determine earliest known suspicious activity and latest confirmed activity.
2. Identify affected tenants, users, records, systems, credentials, and data categories.
3. Verify whether data was viewed, modified, deleted, exported, or only made accessible.
4. Compare application logs, audit logs, database logs, object access logs, and traces for consistency.
5. Document confidence level for each finding: confirmed, likely, possible, or ruled out.

## Communication and notification

- Use [communication-template.md](communication-template.md) for internal and customer updates.
- Security and Legal must approve external language before customer, regulator, law-enforcement, or partner notification.
- If personal data may be involved, start privacy notification assessment immediately and track statutory deadlines.
- Notify affected customers directly when scope is confirmed or when contractual obligations require earlier notice.

## Eradication and recovery

1. Remove attacker persistence, malicious workloads, unauthorized users, and unsafe configuration.
2. Patch vulnerable services and redeploy from trusted images.
3. Rotate credentials that may have been accessed, including downstream provider credentials.
4. Restore modified data from verified backups if integrity is in doubt.
5. Increase monitoring for affected tenants and indicators of compromise for at least 14 days.
6. Keep elevated logging enabled until Security closes monitoring.

## Closure criteria

- Active unauthorized access is contained.
- Scope assessment is approved by Security and Legal.
- Customer/regulatory notifications are complete or explicitly not required.
- Secrets and credentials in scope are rotated.
- Data integrity is validated or restored.
- Corrective actions are tracked with owners and due dates.
- Post-mortem is completed using [communication-template.md](communication-template.md) or [incident-postmortem-template.md](incident-postmortem-template.md).

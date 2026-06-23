# On-Call Escalation Policy

## Roles

| Role | Responsibility |
|---|---|
| Primary on-call | First responder, initial triage owner, and mitigation driver until handoff. |
| Secondary on-call | Backup responder when primary misses target or incident needs parallel response. |
| Incident commander | Coordinates roles, severity, timeline, decision log, escalation, and incident closure. Required for SEV-1 and SEV-2. |
| Technical lead | Owns diagnosis and remediation plan for the affected service or layer. |
| Communications lead | Owns internal updates, customer/status-page updates, and executive summaries. |
| Scribe | Captures timeline, commands, evidence, decisions, and action items. |
| Service owner | Supplies layer-specific expertise and approves risky remediation for owned systems. |
| Security lead | Required for suspected security, privacy, auth bypass, credential, data exposure, or tenant-isolation incidents. |
| Legal/Privacy | Required before breach, regulatory, contractual, or customer-specific notification conclusions. |

## Escalation Path

1. Alert or report is classified with [severity_matrix.md](severity_matrix.md).
2. Primary on-call is paged for SEV-1 and SEV-2.
3. If primary does not acknowledge within the response target, page secondary.
4. If SEV-1 or SEV-2 remains unowned after 10 additional minutes, escalate to
   engineering manager or duty manager.
5. Incident commander engages service owners based on affected layer:
   L1 ingestion, L2 extraction, L3 knowledge graph, L4 agents, L5 ground truth,
   L6 benchmarks, API gateway, web, billing, infrastructure, or security.
6. Security is engaged immediately for suspected tenant isolation, auth bypass,
   credential exposure, data exposure, abuse, or regulated data impact.
7. Legal/Privacy and Customer Operations are engaged before external statements
   that discuss breach status, legal obligations, tenant names, or data scope.

## Update Cadence

| Severity | Internal update cadence | Customer/status update cadence |
|---|---:|---:|
| SEV-1 | Every 15 minutes | Every 15 minutes when customer impact is broad or status page is active |
| SEV-2 | Every 30 minutes | Every 30 minutes when customer impact is material |
| SEV-3 | At material changes | Support-led updates when customers are directly affected |
| SEV-4 | Ticket updates | Not required |

Every update must include severity, status, customer impact, owner, current
mitigation, and next update time.

## Handoff Requirements

Before a responder leaves the incident, they must record:

- Current incident state.
- Open hypotheses and ruled-out causes.
- Actions already taken and validation results.
- Evidence links.
- Next owner and next update time.

## Closure Requirements

An incident can be closed only when:

- Mitigation is stable.
- Validation completed or an exception is approved by the incident commander.
- Customer/status-page updates are resolved where applicable.
- Postmortem owner and due date are assigned for SEV-1, SEV-2, security/privacy,
  tenant-isolation, data-loss, and repeated SEV-3 incidents.

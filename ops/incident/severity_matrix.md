# Incident Severity Matrix

Use the highest matching severity. Classify suspected security, privacy,
tenant-isolation, credential compromise, data-loss, or cross-tenant exposure as
SEV-1 until Security or the incident commander records downgrade evidence.

| Severity | Definition | Typical impact | Response target | Customer update cadence | Escalation trigger |
|---|---|---|---:|---|---|
| **SEV-1 Critical** | Active production outage, confirmed or suspected security/privacy incident, tenant-isolation failure, data-loss risk, or severe degradation of customer-critical workflows. | Multiple layers unavailable, sustained 5xx surge, auth unavailable, database unavailable, cross-tenant exposure risk, destructive data integrity issue. | 5 minutes | Every 15 minutes until mitigated | Page primary and secondary on-call immediately; assign incident commander; engage Security/Legal for security, privacy, or data impact. |
| **SEV-2 High** | Significant production degradation with customer impact but partial functionality or workaround remains. | One critical layer degraded, queue backlog delaying workflows, database latency affecting many tenants, billing webhook delivery failure with replay possible. | 15 minutes | Every 30 minutes until mitigated | Page primary on-call; escalate to backup if unacknowledged; assign incident commander. |
| **SEV-3 Medium** | Limited customer impact, bounded tenant impact, or non-critical workflow degradation with clear workaround. | Intermittent errors, delayed non-critical jobs, partial dashboard degradation, isolated tenant support escalation. | 1 hour | At material changes | Notify on-call and service owner; escalate if impact expands, repeats, or persists more than 4 hours. |
| **SEV-4 Low** | Minimal or no customer impact; maintenance, hygiene, alert noise, or documentation gap. | Cosmetic dashboard issue, noisy alert, low-risk operational follow-up. | 1 business day | Not required unless customer-facing | Track in backlog; reclassify if customer impact appears. |

## Data, Security, And Tenant Criteria

- Any suspected cross-tenant data access starts as SEV-1.
- Any suspected credential exposure or auth bypass starts as SEV-1.
- Any incident that may affect regulated data requires Security and
  Legal/Privacy review before customer-facing conclusions are published.
- A single-tenant issue can be SEV-2 or SEV-3 only when evidence confirms no
  cross-tenant, security, privacy, or data-integrity risk.

## Severity Changes

Record each severity change in the incident timeline with:

- UTC timestamp.
- Previous and new severity.
- Evidence supporting the change.
- Incident commander approval.

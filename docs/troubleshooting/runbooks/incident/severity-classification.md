# Incident Severity Classification

Use this matrix when triaging production incidents, customer-impacting degradations, and suspected security events. If the impact is unclear, classify at the higher severity until the incident commander confirms otherwise.

## Severity matrix

| Severity | Definition | Examples | Initial response target | Incident commander required |
|---|---|---|---:|---|
| **SEV1** | Complete outage, data loss, or confirmed/suspected security breach. | Full platform unavailable, unrecoverable or actively spreading data loss, cross-tenant exposure, credential compromise, ransomware indicators. | **15 minutes** | Yes |
| **SEV2** | Major feature degraded or partial data loss. | One production layer unavailable with workaround, degraded ingestion/extraction for many tenants, restore needed for a bounded dataset. | **1 hour** | Yes |
| **SEV3** | Minor feature issue with a documented workaround available. | Single non-critical workflow degraded, partial UI issue, increased latency below SLO breach thresholds. | **4 hours** | Optional; on-call lead may coordinate. |
| **SEV4** | Cosmetic issue with no user impact. | Documentation typo, dashboard display defect, non-user-facing alert label issue. | **24 hours** | No |

## Classification rules

1. **Security first:** Any suspected data breach, tenant-isolation failure, ransomware activity, or credential compromise starts as **SEV1** until Security downgrades it in writing.
2. **Data integrity first:** Any unknown data-loss scope starts as **SEV1**; bounded partial loss with verified backups may be downgraded to **SEV2** after impact assessment.
3. **Customer impact drives severity:** Prefer the customer-visible impact over the internal component that failed.
4. **Downgrades require evidence:** Record the evidence, decision maker, and timestamp in the incident channel.
5. **Escalate on missed response targets:** If acknowledgement or mitigation does not meet the target, notify the next escalation level and update the status page cadence.

## Response expectations

| Severity | Acknowledge by | Update cadence | Status page | Post-incident review |
|---|---:|---:|---|---|
| SEV1 | 15 minutes | Every 15 minutes until mitigated | Required for customer impact or security notice | Required within 5 business days |
| SEV2 | 1 hour | Every 30 minutes until mitigated | Required if broad customer impact | Required within 5 business days |
| SEV3 | 4 hours | Every 2 hours or at material change | Optional | Optional unless repeated |
| SEV4 | 24 hours | At owner discretion | Not required | Not required |

## Related runbooks

- [Communication Template](communication-template.md)
- [Data Breach Response](data-breach-response.md)
- [Tenant Isolation Failure](tenant-isolation-failure.md)
- [Ransomware Response](ransomware-response.md)
- [Cloud Provider Outage](cloud-provider-outage.md)
- [Incident Postmortem Template](incident-postmortem-template.md)

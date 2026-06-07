---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Security FAQ

## Overview

This page covers encryption standards, compliance certifications, penetration testing, and incident response for security-conscious teams and auditors.

## Who this is for

- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">Executive</span>
- <span class="vp-badge vp-badge--role">Developer</span>

## Prerequisites

- Access to **Administration > Security** settings (for admins).
- Signed NDA (for penetration test reports).

## Frequently asked questions

### 1. How is data encrypted?

All data is encrypted at rest using AES-256-GCM. Data in transit uses TLS 1.3 with perfect forward secrecy. API keys and webhook secrets are hashed with bcrypt and never stored in plaintext. PostgreSQL and Neo4j both use encrypted volumes.

### 2. What compliance certifications does ValuePact hold?

- SOC 2 Type II (annual audit)
- ISO 27001 certified
- GDPR compliant
- HIPAA BAA available

Certificates and audit reports are available in the **Trust Center** or through your account executive.

### 3. How often is penetration testing performed?

ValuePact undergoes quarterly penetration testing by an independent third party. Annual red-team exercises simulate advanced persistent threat (APT) scenarios. Summary findings are shared with customers under NDA.

### 4. How does tenant isolation work?

Tenant isolation is enforced at multiple layers:

1. **Authentication:** Clerk issues tenant-scoped JWTs.
2. **API Gateway:** Every request is validated against the tenant claim.
3. **Database:** PostgreSQL queries include `tenant_id` filters enforced by row-level security (RLS) policies.
4. **Graph Layer:** Neo4j Cypher queries are parameterized with tenant constraints.
5. **Cache:** Redis keys are prefixed with the tenant ID.

### 5. What is the incident response process?

1. **Detection:** Automated alerts from monitoring and anomaly detection.
2. **Containment:** Immediate isolation of affected resources.
3. **Investigation:** Forensic analysis by the security team.
4. **Notification:** Customers notified within 72 hours if their data is affected.
5. **Remediation:** Fixes deployed and verified.
6. **Retrospective:** Public post-mortem for major incidents.

### 6. Can I bring my own encryption keys?

Yes. Enterprise plans support customer-managed keys (CMK) via AWS KMS or Azure Key Vault. Contact your account executive to enable CMK for your tenant.

### 7. How are secrets managed?

ValuePact uses Infisical for secret management in development and the Kubernetes External Secrets Operator in production. Secrets are rotated automatically every 90 days. Developers never commit secrets to source control.

### 8. What logging is available for audits?

Admin audit logs capture every create, read, update, and delete operation. Logs include the user ID, tenant ID, timestamp, IP address, and action outcome. Logs are retained for <span class="vp-badge vp-badge--limit">7 years</span> and are tamper-evident via write-once storage.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | View audit logs | Organization |
| Admin | Configure security settings | Organization |
| Executive | View compliance reports | Organization |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> Audit log export: 100,000 rows per request.
- <span class="vp-badge vp-badge--limit">Limit</span> MFA exemption duration: 30 days max.
- <span class="vp-badge vp-badge--limit">Limit</span> Session lifetime: 12 hours idle, 24 hours absolute.

## Troubleshooting

??? question "Issue: SSO login fails with certificate error"
    **Cause:** The identity provider certificate expired or was rotated.
    **Resolution:**
    1. Download the new SAML certificate from your IdP.
    2. Upload it in **Administration > Security > SSO**.
    3. Test the connection.

??? question "Issue: Audit log shows unexpected access from an unknown IP"
    **Cause:** The user is on a VPN or traveling, or the account is compromised.
    **Resolution:**
    1. Contact the user to confirm legitimacy.
    2. If suspicious, force a password reset and revoke all sessions.
    3. Report to security@valuepact.ai.

## Related pages

- [Admin FAQ](admin-faq.md)
- [Integration FAQ](integration-faq.md)
- [Governance Best Practices](../best-practices/governance.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| General | Compliance or audit questions | Customer Success Manager |
| Urgent | Suspected breach or anomaly | security@valuepact.ai |
| Critical | Active security incident | On-call page via security@valuepact.ai with subject "P1 Security Incident" |

---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Admin FAQ

## Overview

This page addresses the operational questions admins face when provisioning users, managing billing, scaling the tenant, and maintaining compliance posture.

## Who this is for

- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">Developer</span>

## Prerequisites

- Organization Admin role in ValuePact.
- Access to the Clerk dashboard (if managing SSO).
- Familiarity with your organization’s identity provider (IdP).

## Frequently asked questions

### 1. How do I provision users in bulk?

1. Go to **Administration > User Management > Invite Users**.
2. Click **Bulk Import**.
3. Upload a CSV with columns: `email`, `first_name`, `last_name`, `role`, `team`.
4. Review the preview and click **Send Invites**.
5. Invitations expire in <span class="vp-badge vp-badge--limit">7 days</span>.

### 2. Can I sync users from my identity provider?

Yes. ValuePact supports SCIM 2.0 provisioning through Clerk. Configure SCIM in your IdP (Okta, Azure AD, or Google Workspace) and map groups to ValuePact roles. Changes propagate within minutes.

### 3. How do I view and control costs?

1. Open **Administration > Billing > Usage**.
2. Review seat count, API call volume, and storage.
3. Set **Usage Alerts** at 80% and 100% of your plan limit.
4. Download invoices from the **Billing History** tab.

### 4. What backup and recovery options exist?

ValuePact runs on a multi-region PostgreSQL cluster with point-in-time recovery (PITR) enabled. Neo4j backups are taken daily. As an admin, you can request a tenant-level data export at any time. Recovery time objective (RTO) is <span class="vp-badge vp-badge--limit">4 hours</span>; recovery point objective (RPO) is <span class="vp-badge vp-badge--limit">1 hour</span>.

### 5. How do I enforce MFA?

1. Navigate to **Administration > Security > MFA**.
2. Toggle **Require MFA for all users**.
3. Choose allowed factors: TOTP (authenticator app) or WebAuthn (security key).
4. Exemptions can be granted per user with a documented reason.

### 6. Which compliance certifications does ValuePact hold?

ValuePact is SOC 2 Type II certified and GDPR compliant. HIPAA Business Associate Agreements (BAAs) are available for healthcare tenants. Penetration testing is performed quarterly by a third party. Reports are available under NDA through your account executive.

### 7. How do I configure custom fields?

1. Go to **Administration > Configuration > Custom Fields**.
2. Click **Add Field**.
3. Choose the entity type (Initiative, Benefit, Stakeholder).
4. Define the field type, validation rules, and visibility.
5. Save. The field appears immediately for all users in the tenant.

### 8. Can I enforce approval workflows?

Yes. Open **Administration > Configuration > Workflows**. You can create multi-stage approval gates with conditional branches based on initiative value, risk level, or team. Each gate can require one or many approvers.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Manage users | Organization |
| Admin | Configure billing | Organization |
| Admin | Manage security settings | Organization |
| Admin | Configure workflows | Organization |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> Bulk invite: 500 users per CSV.
- <span class="vp-badge vp-badge--limit">Limit</span> Custom fields per entity: 50.
- <span class="vp-badge vp-badge--limit">Limit</span> Workflow stages: 10 per workflow.
- <span class="vp-badge vp-badge--limit">Limit</span> SCIM sync frequency: every 15 minutes.

## Troubleshooting

??? question "Issue: SCIM sync is not creating users"
    **Cause:** The SCIM bearer token expired, or the group mapping is incorrect.
    **Resolution:**
    1. Regenerate the SCIM token in **Administration > Security > SSO**.
    2. Verify group names match exactly (case-sensitive).
    3. Check Clerk logs for 401 errors.

??? question "Issue: Custom field does not appear on existing records"
    **Cause:** The field was created with "Apply to new records only" selected.
    **Resolution:**
    1. Edit the custom field.
    2. Toggle **Apply retroactively**.
    3. Save. Existing records update within minutes.

## Related pages

- [Security FAQ](security-faq.md)
- [Integration FAQ](integration-faq.md)
- [Governance Best Practices](../best-practices/governance.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| General | Billing or plan questions | Customer Success Manager |
| Urgent | Security incident or breach suspicion | security@valuepact.ai |
| Critical | Tenant-wide outage or data loss | On-call page via support@valuepact.ai |

---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Escalation Guides

When and how to escalate customer issues to ensure timely resolution.

## Who this is for

<span class="vp-badge vp-badge--role">Support</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Escalation tiers

| Tier | Handles | Response |
|------|---------|----------|
| L1 — Support | General questions, how-to, common issues | 4 hours |
| L2 — Technical Support | Complex bugs, API issues, integration failures | 1 hour |
| L3 — Engineering | Defects requiring code changes, performance issues | 4 hours |
| L4 — Engineering Lead | Critical outages, security incidents, data loss | 1 hour |

## When to escalate

### Escalate to L2 immediately

- Issue affects multiple users in the same tenant
- API returning 500 errors consistently
- Integration sync failing for >24 hours
- User cannot access platform due to auth issues

### Escalate to L3 immediately

- Confirmed bug with no workaround
- Performance degradation affecting workflows
- Data inconsistency requiring investigation
- Security concern (not active breach)

### Escalate to L4 immediately

- Complete platform outage
- Suspected security breach
- Data loss or corruption
- Compliance violation

## Escalation process

1. **Document** the issue with all relevant details (tenant, user, timestamps, errors).
2. **Attempt resolution** at current tier using runbooks.
3. **Escalate** via the internal ticket system with severity label.
4. **Notify** the customer of escalation and expected timeline.
5. **Track** progress and communicate updates every 2 hours for P1/P2.

## Handoff checklist

When escalating, include:

- [ ] Customer name and tenant ID
- [ ] Issue summary and business impact
- [ ] Steps already attempted
- [ ] Relevant logs, screenshots, or request IDs
- [ ] Severity classification
- [ ] Customer expectations and timeline

## Related pages

- [Severity Matrix](severity-matrix.md)
- [Ticket Response Templates](ticket-response-templates.md)
- [Troubleshooting](../troubleshooting/index.md)

---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Severity Matrix

Classify issues by severity to ensure appropriate response times.

## Who this is for

<span class="vp-badge vp-badge--role">Support</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Severity levels

| Level | Description | Examples | Response | Resolution |
|-------|-------------|----------|----------|------------|
| **P1 — Critical** | Production down, no workaround | Complete outage, data loss, security breach | 15 min | 4 hours |
| **P2 — High** | Major feature impaired, limited workaround | Core functionality broken, significant performance issue | 1 hour | 24 hours |
| **P3 — Medium** | Minor feature issue, workaround exists | Non-core feature broken, UI issue | 4 hours | 72 hours |
| **P4 — Low** | Question, enhancement, cosmetic | How-to, feature request, typo | 1 business day | Next sprint |

## Classification criteria

### P1 indicators

- Cannot access platform
- Data loss or corruption
- Security incident
- Compliance violation

### P2 indicators

- Critical workflow blocked
- API completely failing for endpoint
- Integration down with no workaround
- Performance unusable (>30s response times)

### P3 indicators

- Feature partially broken
- Workaround exists but is inconvenient
- Reporting inconsistency
- Sync delays <24 hours

### P4 indicators

- General questions
- Feature requests
- Documentation improvements
- Cosmetic issues

## Escalation

See [Escalation Guides](escalation-guides.md) for the escalation process.

## Related pages

- [Support Overview](index.md)
- [Escalation Guides](escalation-guides.md)
- [Ticket Response Templates](ticket-response-templates.md)

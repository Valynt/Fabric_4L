---
workflow_id: incident-response
name: Incident Response
version: 1.0.0
description: Structured incident response workflow for production incidents with severity triage, communication, and post-mortem
pattern: human-in-the-loop
risk_level: high
---

# Incident Response Workflow

Use this workflow for structured response to production incidents, ensuring proper triage, communication, mitigation, and post-incident analysis.

## Activation Criteria

Trigger this workflow when:
- Production outage or degradation detected
- Security incident identified
- Data integrity issue discovered
- Critical bug affecting users
- SLA breach imminent or actual

## Severity Levels

### P0 - Critical
- Complete service outage
- Data loss or corruption
- Security breach
- SLA breach for all customers
- Immediate revenue impact

### P1 - High
- Partial service degradation
- Single-tenant outage
- Performance degradation affecting many users
- Feature completely broken for some users

### P2 - Medium
- Minor performance issues
- Single feature broken
- Edge case failures
- Non-critical bugs

### P3 - Low
- Cosmetic issues
- Documentation errors
- Minor UX problems
- Low-impact bugs

## Workflow Steps

### 1. Incident Declaration
// turbo
- Declare incident with severity level
- Create incident channel (Slack/Teams)
- Assign incident commander
- Set up incident timeline document
- Notify on-call team and stakeholders

**Required Information:**
- Incident title
- Severity level (P0-P3)
- Affected services/layers
- Initial symptoms
- First detected timestamp
- Incident commander

### 2. Initial Triage
- Confirm scope and impact
- Identify affected customers/tenants
- Determine if incident is worsening
- Check for recent deployments
- Review monitoring/alerts for patterns

**Questions to Answer:**
- What is broken?
- Who is affected?
- How many users/tenants?
- Is the issue getting worse?
- Any recent changes?

### 3. Mitigation Actions
- Implement immediate workaround if available
- Roll back recent deployment if suspected cause
- Scale affected services if capacity issue
- Restart services if state corruption suspected
- Implement traffic shaping if needed

**Priority:**
1. Stop the bleeding (mitigate impact)
2. Identify root cause
3. Implement permanent fix

### 4. Root Cause Analysis
- Review logs from affected time window
- Check database state and queries
- Analyze API error rates and patterns
- Review recent code changes
- Check infrastructure changes
- Review external dependencies

**Techniques:**
- Five Whys analysis
- Timeline reconstruction
- Log correlation across layers
- Database query analysis
- Network trace analysis

### 5. Communication Updates
- Update stakeholders every 15-30 minutes (P0/P1) or hourly (P2/P3)
- Provide status updates: Investigating, Identified, Monitoring, Resolved
- Include ETA when available
- Be transparent about unknowns
- Document all communication

**Update Format:**
```
Status: [Investigating | Identified | Monitoring | Resolved]
Summary: [What we know]
Impact: [Who is affected]
Next Update: [Time]
```

### 6. Resolution Verification
- Confirm fix deployed to all affected services
- Verify metrics return to normal baselines
- Test affected functionality end-to-end
- Monitor for 30-60 minutes for stability
- Confirm no regressions introduced

**Verification Checklist:**
- [ ] Fix deployed to production
- [ ] Error rates at baseline
- [ ] Latency at baseline
- [ ] Throughput at baseline
- [ ] End-to-end tests passing
- [ ] No new errors in logs
- [ ] Customer-reported issues resolved

### 7. Incident Closure
- Declare incident resolved
- Send final communication to stakeholders
- Update incident timeline with resolution
- Archive incident channel
- Schedule post-mortem if P0/P1

### 8. Post-Mortem (P0/P1 incidents)
Create post-mortem document within 48 hours including:

**Sections:**
- Executive Summary
- Timeline of Events
- Root Cause Analysis
- Impact Assessment
- Resolution Actions Taken
- Follow-up Actions
- Lessons Learned
- Action Items with Owners and Due Dates

**Post-Mortem Template:**
```markdown
# Incident Post-Mortem: [Incident Title]

**Date:** [YYYY-MM-DD]
**Severity:** [P0/P1/P2/P3]
**Duration:** [Start] to [End]
**Incident Commander:** [Name]

## Executive Summary
[2-3 paragraph summary]

## Timeline
| Time (UTC) | Event |
|------------|-------|
| ... | ... |

## Root Cause
[Detailed analysis]

## Impact
- Affected users: [N]
- Affected tenants: [N]
- Downtime: [N minutes]
- Revenue impact: [if applicable]

## Resolution
[What was done to fix]

## Follow-up Actions
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| ... | ... | ... | ... |

## Lessons Learned
[What did we learn? What went well? What could be improved?]
```

## Roles and Responsibilities

### Incident Commander
- Overall coordination
- Communication with stakeholders
- Decision authority
- Timeline management

### Technical Lead
- Root cause investigation
- Technical decision making
- Fix implementation coordination

### Communications Lead
- External communication
- Customer notifications
- Status page updates

### Scribe
- Timeline documentation
- Meeting notes
- Post-mortem drafting

## Communication Channels

**Internal:**
- Incident channel (#incident-[name])
- On-call team
- Engineering leadership
- Product management (if customer-facing)

**External (if needed):**
- Status page
- Customer email
- Social media (for major outages)

## Safety Rules

1. **Never rush fixes without understanding** - Making things worse is worse than being slow
2. **Communicate early and often** - Silence is worse than bad news
3. **Preserve evidence** - Don't restart services or clear logs without documenting
4. **Escalate appropriately** - Know when to call for help
5. **Document everything** - Future you will thank present you

## Tools and Resources

- **Monitoring:** Prometheus, Grafana dashboards
- **Logs:** Loki, application logs
- **Tracing:** Jaeger, distributed tracing
- **Alerting:** PagerDuty, Opsgenie
- **Communication:** Slack, Teams
- **Documentation:** Confluence, Notion

## Example Commands

```
/incident-response severity=P0 title="Database connection pool exhaustion"
/incident-response severity=P1 title="L4 agent workflow failures"
/incident-response severity=P2 title="Frontend login page slow"
```

## Quick Reference

**P0 Response Time:** < 15 minutes to acknowledge, < 1 hour to mitigation
**P1 Response Time:** < 30 minutes to acknowledge, < 4 hours to mitigation
**P2 Response Time:** < 1 hour to acknowledge, < 24 hours to mitigation
**P3 Response Time:** < 4 hours to acknowledge, < 1 week to mitigation

**Communication Frequency:**
- P0/P1: Every 15-30 minutes
- P2/P3: Every 1-2 hours

---
description: Systematic feature flag rollout workflow for safe, gradual feature deployment with monitoring and rollback capabilities
---

# Feature Flag Rollout Workflow

Use this workflow for safe, gradual feature deployment using feature flags, enabling controlled rollouts with monitoring and instant rollback capabilities.

## When to Use

- Deploying new features to production
- Rolling out major changes
- A/B testing new functionality
- Gradual migration to new implementations
- Risky deployments requiring safety net

## Workflow Steps

### 1. Feature Flag Design
// turbo
- Define flag name and purpose
- Determine flag type (boolean, percentage, multivariate)
- Set default value (off for new features)
- Define expiration date if temporary
- Document flag in feature flag registry

**Flag Types:**
- **Boolean**: Simple on/off
- **Percentage**: Gradual rollout (0-100%)
- **Multivariate**: A/B testing variants
- **User-based**: Per-user or per-tenant targeting

### 2. Implementation Integration

**Backend Integration:**
- Add flag check in relevant code paths
- Ensure flag check is performant (cached)
- Add telemetry for flag usage
- Test with flag enabled/disabled

**Frontend Integration:**
- Add flag check in component logic
- Fetch flags from API or config
- Handle flag loading states
- Test with flag enabled/disabled

**Example Implementation:**
```python
# Backend
if feature_flags.is_enabled("new-graph-algorithm", tenant_id):
    return new_algorithm()
else:
    return legacy_algorithm()
```

```typescript
// Frontend
if (featureFlags['new-dashboard-ui']) {
  return <NewDashboard />;
}
return <LegacyDashboard />;
```

### 3. Testing Strategy

**Unit Tests:**
- Test both code paths (flag on/off)
- Mock flag service for deterministic tests
- Verify flag check logic

**Integration Tests:**
- Test with flag enabled
- Test with flag disabled
- Test flag changes during runtime

**Manual Testing:**
- Test feature with flag enabled
- Test feature with flag disabled
- Verify rollback works
- Check telemetry

### 4. Rollout Strategy

**Percentage Rollout:**
- Start at 1% of traffic
- Monitor for 1-2 hours
- Increase to 10% if stable
- Increase to 50% if stable
- Increase to 100% if stable

**User-Based Rollout:**
- Start with internal users
- Add beta customers
- Add production customers gradually
- Monitor per-user metrics

**Tenant-Based Rollout:**
- Start with test tenant
- Add low-risk tenants
- Add high-value tenants last
- Monitor per-tenant metrics

### 5. Monitoring Setup

**Metrics to Track:**
- Error rates (flagged vs unflagged)
- Latency (flagged vs unflagged)
- User engagement metrics
- Conversion rates (if applicable)
- Resource utilization

**Alerts:**
- Error rate increase > 20%
- Latency increase > 30%
- Any critical errors in flagged path
- Rollback triggers

**Dashboards:**
- Flag usage metrics
- Performance comparison
- Error rate comparison
- User feedback

### 6. Staging Validation

Deploy to staging with flag enabled:
- Run full test suite
- Manual testing of feature
- Load testing with flag enabled
- Monitor for 1 hour
- Check logs for errors

**Staging Checklist:**
- [ ] Flag works as expected
- [ ] No errors in flagged path
- [ ] Performance acceptable
- [ ] Rollback tested
- [ ] Team reviewed

### 7. Production Rollout

**Phase 1: 1% Rollout**
- Set flag to 1% of traffic
- Monitor for 1-2 hours
- Check metrics and logs
- Verify no critical errors

**Phase 2: 10% Rollout**
- Increase to 10% if Phase 1 stable
- Monitor for 2-4 hours
- Check user feedback
- Verify performance

**Phase 3: 50% Rollout**
- Increase to 50% if Phase 2 stable
- Monitor for 4-8 hours
- Check all metrics
- Verify stability

**Phase 4: 100% Rollout**
- Increase to 100% if Phase 3 stable
- Monitor for 24 hours
- Check for delayed issues
- Plan flag cleanup

### 8. Rollback Triggers

**Immediate Rollback (P0):**
- Critical errors in flagged path
- Data corruption
- Security vulnerability
- Complete service outage

**Rollback Within 1 Hour (P1):**
- Error rate increase > 50%
- Latency increase > 100%
- User complaints spike
- Revenue impact detected

**Rollback Within 4 Hours (P2):**
- Error rate increase > 20%
- Latency increase > 30%
- User feedback negative
- Performance degradation

**Rollback Procedure:**
1. Set flag to 0% or previous stable value
2. Monitor for recovery
3. Investigate root cause
4. Fix issue
5. Restart rollout from beginning

### 9. Flag Cleanup

Once feature is stable at 100%:
- Remove flag checks from code
- Delete flag from registry
- Update documentation
- Remove telemetry overhead
- Commit cleanup

**Cleanup Checklist:**
- [ ] Flag at 100% for 7+ days
- [ ] No issues detected
- [ ] Code cleaned up
- [ ] Documentation updated
- [ ] Flag deleted

### 10. Documentation

Update documentation:
- Feature flag registry
- Architecture docs
- Runbooks
- Onboarding guides
- API docs if applicable

## Rollout Templates

### Standard Percentage Rollout
```
Day 1: 1% → 10% → 50% → 100%
Monitor at each step for 1-4 hours
```

### Conservative Rollout
```
Day 1: 1% (24 hours)
Day 2: 10% (24 hours)
Day 3: 50% (24 hours)
Day 4: 100% (7 days)
```

### Aggressive Rollout
```
1% → 10% → 50% → 100% (within 4 hours)
For low-risk, well-tested features
```

## Safety Rules

1. **Always start small** - never start at 100%
2. **Monitor continuously** - don't set and forget
3. **Have rollback ready** - flags enable instant rollback
4. **Test before rollout** - staging validation required
5. **Clean up flags** - don't leave dead flags in code

## Example Commands

```
/feature-flag-rollout flag=new-graph-algorithm strategy=percentage
/feature-flag-rollout flag=new-dashboard-ui strategy=user-based
/feature-flag-rollout flag=api-v2 strategy=tenant-based rollout=conservative
```

## Quick Reference

**Rollout Speed:**
- Low-risk features: 4 hours to 100%
- Medium-risk features: 1-2 days to 100%
- High-risk features: 3-7 days to 100%

**Monitoring:**
- Check metrics every 15-30 minutes during rollout
- Set alerts for error rate and latency
- Review logs for errors

**Rollback Criteria:**
- Error rate > 20%: rollback
- Latency > 30% increase: rollback
- User complaints: investigate, rollback if needed
## Required State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn.

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "feature-flag-rollout-001",
  "files_touched": [],
  "tests_run": [],
  "decisions_made": [],
  "blocked_by": null,
  "retry_count": 0,
  "circuit_breaker": {
    "tripped": false,
    "reason": null,
    "escalation_path": null
  }
}
```

## Circuit Breaker Configuration

```yaml
circuit_breaker:
  max_tool_errors: 3
  max_self_correction_loops: 2
  action_on_trip: halt_and_escalate
  escalation_path: "log_and_notify"
```

## Completion Checklist

- [ ] State JSON updated with current stage, touched files, tests, and decisions.
- [ ] Circuit breaker evaluated before retrying after tool errors or self-correction loops.
- [ ] Relevant validation commands run and recorded in the workflow state.
- [ ] No security, tenant-isolation, contract, governance, or frontend-design assertions weakened.

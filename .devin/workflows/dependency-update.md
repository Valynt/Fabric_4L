---
workflow_id: dependency-update
name: Dependency Update
version: 1.0.0
description: Systematic dependency update workflow for security patches, bug fixes, and feature updates with testing and rollback planning
pattern: pipeline-dag
risk_level: medium
category: infrastructure
---

# Dependency Update Workflow

Use this workflow for systematic dependency updates across the monorepo, ensuring security patches, bug fixes, and feature updates are applied safely with proper testing and rollback planning.

## When to Use

- Monthly dependency update cycle
- Security vulnerability detected (CVE)
- Critical bug in upstream dependency
- Major version upgrade needed
- Before release to ensure latest patches

## Workflow Steps

### 1. Dependency Inventory
// turbo
- List all package.json and pyproject.toml files
- Identify direct vs transitive dependencies
- Check current versions across all services
- Note any pinned versions vs version ranges

**Tools:**
```bash
# Frontend
pnpm list --depth=0
pnpm outdated

# Backend (per service)
pip list
pip-audit
```

### 2. Security Audit
- Run security scanners on all dependencies
- Check for known CVEs
- Review vulnerability severity scores
- Identify dependencies with no recent updates

**Tools:**
```bash
# Frontend
pnpm audit

# Backend
pip-audit
safety check
```

### 3. Categorize Updates

**Security Updates (P0):**
- Critical CVEs (CVSS >= 7.0)
- Known exploits in the wild
- Apply immediately

**Bug Fixes (P1):**
- Critical bugs affecting functionality
- Memory leaks or performance issues
- Apply in next sprint

**Feature Updates (P2):**
- New features or improvements
- Breaking changes in major versions
- Apply during planned upgrade windows

**Deprecated Dependencies (P3):**
- Dependencies marked for deprecation
- Plan migration to alternatives

### 4. Test Impact Analysis
For each dependency update, analyze:
- Which services use this dependency?
- What functionality depends on it?
- Are there breaking changes in the new version?
- Do we need to update our code?

**Check:**
- Changelog for breaking changes
- Migration guides
- Deprecation notices
- API changes

### 5. Update Strategy

**For Security Updates (P0):**
- Update to patched version immediately
- Run full test suite
- Deploy to staging first
- Monitor for regressions

**For Bug Fixes (P1):**
- Update in feature branch
- Run affected service tests
- Test impacted functionality manually
- Merge after validation

**For Feature Updates (P2):**
- Schedule dedicated upgrade branch
- Allocate time for migration work
- Update in coordination with other teams
- Full regression testing required

### 6. Update Execution

**Frontend (pnpm):**
```bash
# Update specific package
pnpm update package-name@version

# Update all (use with caution)
pnpm update

# Update to latest
pnpm update package-name@latest
```

**Backend (uv/pip):**
```bash
# Update specific package
uv pip install package-name==version

# Update all (use with caution)
uv pip install --upgrade -r requirements.txt
```

### 7. Validation Testing

**Automated Tests:**
- Run full test suite for affected services
- Run integration tests
- Run contract tests
- Run security tests

**Manual Testing:**
- Test functionality that uses updated dependency
- Check for API changes
- Verify performance characteristics
- Test edge cases

**Test Matrix:**
| Service | Unit Tests | Integration Tests | Manual Tests | Status |
|---------|------------|-------------------|--------------|--------|
| L1      | ✅         | ✅                | ✅           | Pass    |
| L2      | ✅         | ✅                | ✅           | Pass    |
| ...     | ...        | ...               | ...          | ...     |

### 8. Rollback Planning

Before deploying, prepare rollback plan:
- Document previous working versions
- Prepare rollback commands
- Identify data migration needs
- Set rollback criteria

**Rollback Triggers:**
- Test failures > 5%
- Performance degradation > 20%
- Critical functionality broken
- Security regression detected

### 9. Deployment

**Staging First:**
- Deploy to staging environment
- Run smoke tests
- Monitor for 30 minutes
- Check logs for errors

**Production:**
- Deploy during low-traffic window
- Monitor metrics closely
- Have rollback ready
- Notify team of deployment

### 10. Post-Update Verification

After deployment:
- Monitor error rates for 1 hour
- Check performance metrics
- Review logs for new errors
- Verify key functionality works
- Confirm no security regressions

### 11. Documentation

Update documentation:
- Update dependency versions in README
- Document any breaking changes
- Update migration guides if needed
- Record update in CHANGELOG

## Constraints

- **Never update all dependencies at once** - group by service or dependency type
- **Always test before production** - no direct production updates
- **Security updates take priority** - P0 updates can bypass normal process
- **Major version upgrades require planning** - allocate dedicated time
- **Document breaking changes** - always note what changed and why

## Safety Rules

1. **Always have a rollback plan** before deploying
2. **Test in staging first** - never skip staging
3. **Monitor after deployment** - watch for at least 1 hour
4. **Communicate changes** - notify team of dependency updates
5. **Keep security patches current** - don't delay P0 updates

## Example Commands

```
/update-dependencies security-only
/update-dependencies service=layer1
/update-dependencies package=react
/update-dependencies major-upgrade
```

## Quick Reference

**Update Frequency:**
- Security updates: Immediate (P0)
- Bug fixes: Monthly (P1)
- Feature updates: Quarterly (P2)
- Major upgrades: Planned (P2)

**Testing Requirements:**
- P0: Full regression + staging
- P1: Affected service tests + manual
- P2: Full regression + staging + manual
## Required State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn.

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "dependency-update-001",
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

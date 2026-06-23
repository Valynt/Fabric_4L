---
skill_id: launch-readiness-assessment
name: Launch Readiness Assessment
version: 1.0.0
description: Templates and reference for Launch Readiness Assessment workflow
side_effects: none
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# Launch Readiness Assessment — Workflow Reference

## Output Format

```markdown
# Launch Readiness Assessment - {YYYY-MM-DD}

**Claimed Readiness: {N}%**
**Verified Readiness: {N}% | Blocked**

| Layer | Claimed | Verified | Target | Gap | Evidence |
|-------|---------|----------|--------|-----|----------|
| L1 Ingestion | {N}% | {N}% / Unverified / Blocked | 90% | {text} | {artifact or note} |
| L2 Extraction | {N}% | {N}% / Unverified / Blocked | 95% | {text} | {artifact or note} |
| L3 Knowledge | {N}% | {N}% / Unverified / Blocked | 90% | {text} | {artifact or note} |
| L4 Agents | {N}% | {N}% / Unverified / Blocked | 85% | {text} | {artifact or note} |
| L5 Ground Truth | 100% | {N}% / Unverified / Blocked | 100% | {text} | {artifact or note} |
| Frontend | {N}% | {N}% / Unverified / Blocked | 85% | {text} | {artifact or note} |
| DevOps | {N}% | {N}% / Unverified / Blocked | 80% | {text} | {artifact or note} |

## L6 Benchmarks Note
- Claimed: {text}
- Verified: {text}
- Launch relevance: {text}

## Top 5 Launch Blockers
1. [Blocker] -> [Evidence] -> [Owning sprint]
2. ...

## Refreshed 5-Sprint Plan
### Sprint 1 — Launch Gate Repair and Baseline Evidence
- Goal: ...
- Exit Criteria: ...

### Sprint 2 — Security Isolation and Contract Closure
- Goal: ...
- Exit Criteria: ...

### Sprint 3 — Monitoring, Health, and Kubernetes Verification
- Goal: ...
- Exit Criteria: ...

### Sprint 4 — L1 Ingestion Hardening and Runtime Confidence
- Goal: ...
- Exit Criteria: ...

### Sprint 5 — Final Evidence Refresh and Go/No-Go
- Goal: ...
- Exit Criteria: ...

## Quick Wins
- [ ] [Quick win]

## Launch Checklist ({met}/{total} verified)
- [ ] [Criterion]
```


## Execution Log Format

Present progress using this structured format:

```
[INIT] Loaded ROADMAP.md, prior assessments, and newest local evidence artifacts
[GATES] Launch-gate integrity: commands={ok|drift} policy={ok|missing} artifacts={ok|missing}
[ASSESS] Claimed readiness captured for L1-L5, Frontend, DevOps; L6 noted separately
[VERIFY] Fresh evidence mapped to arch/security/state/agent/obs/smoke signals
[RISKS] Identified top 5 blockers from verified evidence
[PLAN] Generated refreshed 5-sprint sequence around current blockers
[CHECKLIST] Final launch checklist: {N}/{total} verified
[REVIEW] Presenting assessment and awaiting approval before creating any dated artifact
[ARTIFACTS] User approved - creating new dated launch-readiness report
[COMPLETE] Assessment saved without touching archived or superseded reports
```

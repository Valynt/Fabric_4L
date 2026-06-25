---
workflow_id: repowise-production-readiness
name: Repowise Production Readiness
version: 1.0.0
description: Systematic codebase transformation using repowise MCP intelligence to bring code from functional to production-ready through assessment, prioritization, and execution
pattern: circuit-breaker
risk_level: low
category: code-review
---

# Repowise Production Readiness Workflow

This workflow transforms a codebase from functional to production-ready using repowise MCP intelligence. It orchestrates comprehensive assessment, prioritization, and execution through existing workflows.

## When to Use

- Preparing for production deployment
- After major feature development
- Periodic technical debt cleanup
- Code health assessment requests
- Security and compliance audits

## When to Stop

- All P0 and P1 findings addressed
- Health scores show no critical biomarkers
- Security posture shows no high-severity CVEs or live secrets
- Dead code returns no safe-to-delete findings
- Risk assessment shows acceptable hotspot distribution

## Workflow Steps

### Phase 1: Comprehensive Assessment
// turbo
Run repowise tools in parallel to establish baseline:

**Repository Baseline**
- Call `mcp0_get_overview` to understand architecture, module boundaries, entry points
- Call `mcp0_get_health` to get per-file health scores, biomarker findings, KPIs
- Call `mcp0_get_security` to identify CVEs, secrets, pattern findings

**Risk Analysis**
- Call `mcp0_get_risk` to identify hotspots, dependents, co-change partners
- Call `mcp0_get_dead_code` to find unreachable files, unused exports, zombie packages
- Call `mcp0_get_why` to understand architectural decisions and intent

**Targeted Deep Dives** (as needed based on findings)
- Call `mcp0_get_context` for documentation, ownership, freshness of critical files
- Call `mcp0_get_symbol` for caller/callee analysis of high-risk symbols
- Call `mcp0_search_codebase` for pattern searches across code and docs

**Output**: Document baseline metrics:
- Health score distribution
- Security posture summary
- Dead code count by confidence tier
- Risk hotspot locations
- Decision health issues

### Phase 2: Prioritization

Classify all findings from Phase 1 into priority tiers:

**P0 - Critical Path Blockers**
- Security vulnerabilities from `get_security` (CVEs with high EPSS/KEV scores)
- Live secrets from `get_security`
- High-confidence dead code from `get_dead_code` (safe_to_delete=true)
- High hotspot scores from `get_risk` in core paths

**P1 - Production Stability**
- Medium-confidence dead code
- Biomarker findings from `get_health` indicating fragility
- Co-change partners from `get_risk` (missing co-changes)
- Low health scores in critical modules

**P2 - Maintainability & Technical Debt**
- Unused exports (low confidence)
- Decision health issues from `get_why`
- Ownership gaps from `get_context`
- Documentation drift

**P3 - Optimization**
- Performance biomarkers
- Code coverage gaps
- Minor health score improvements

**Output**: Create prioritized findings list with:
- Finding description
- Priority tier
- Affected files/modules
- Recommended workflow to address

### Phase 3: Execution

Execute in priority order, mapping repowise findings to existing workflows:

**P0: Security & Critical Fixes**
- For `get_security` findings → invoke `/security-auditor` workflow
- For live secrets → immediate remediation, rotate credentials
- For CVEs → invoke `/dependency-update` workflow with security patches

**P0-P1: Dead Code Removal**
- For `get_dead_code` safe_to_delete findings → invoke `/dead-code-sweeper` workflow
- Remove unreachable files, unused exports, zombie packages
- Verify with test suite after each batch

**P0-P1: Contract & Governance**
- For `get_risk` governance gaps → invoke `/contract-enforcement-auditor` workflow
- For missing co-changes → implement identified dependencies
- For API drift → regenerate contracts, update consumers

**P1-P2: Code Quality**
- For `get_health` biomarker findings → invoke `/code-quality-improvement` workflow
- For low health score files → targeted refinement
- For fragility patterns → add error handling, validation

**P1-P2: Architecture & Boundaries**
- For `get_why` decision health → invoke `/code-boundary-enforcement` workflow
- For ownership gaps → update CODEOWNERS, assign responsibility
- For module boundary violations → refactor to canonical paths

**P2-P3: Frontend Polish**
- For `get_health` frontend biomarkers → invoke `/fabric_ui_drift_agent` workflow
- For component health → invoke `/react_component_design` + `/code-quality-improvement`
- For accessibility gaps → invoke `/palette-ux-agent` workflow

**Execution Strategy**:
- Complete all P0 before moving to P1
- Complete all P1 before moving to P2
- Small, focused PRs per workflow execution
- Verify after each batch

### Phase 4: Validation & Iteration

**Continuous Re-Assessment**
// turbo
- After each P0/P1 batch, re-run `mcp0_get_health` and `mcp0_get_security` to verify improvement
- Track health score trends over iterations
- Use `mcp0_get_risk` to ensure no new hotspots introduced

**Automated Validation Gates**
- Run `make verify` for full contract and governance checks
- Run `make test` for backend test suite
- Run `pnpm --dir apps/web run test` for frontend test suite
- Invoke `/launch-readiness-assessment` for production readiness evaluation

**Final Production Gate**
- `mcp0_get_health` shows no critical biomarkers
- `mcp0_get_security` returns no high-severity CVEs or live secrets
- `mcp0_get_dead_code` returns no safe_to_delete findings
- `mcp0_get_risk` shows acceptable hotspot distribution
- All workflows pass with no blockers

**Output**: Final validation report with:
- Before/after health score comparison
- Security posture improvement
- Dead code removal statistics
- Risk reduction metrics
- Remaining P2/P3 items (if any)

## Success Criteria (Definition of Done)

- All P0 and P1 findings addressed
- Health scores show improvement or acceptable baseline
- Security posture shows no critical vulnerabilities
- Dead code removal completed for safe-to-delete items
- Contract compliance verified
- Test suite passes
- Production readiness assessment passes

## Concrete Actions Checklist

- [ ] Ran all Phase 1 repowise assessment tools
- [ ] Documented baseline metrics
- [ ] Classified all findings into P0-P3 tiers
- [ ] Executed P0 security fixes
- [ ] Executed P0-P1 dead code removal
- [ ] Executed P0-P1 contract/governance fixes
- [ ] Executed P1-P2 code quality improvements
- [ ] Executed P1-P2 architecture hardening
- [ ] Re-ran repowise assessment after P0/P1 completion
- [ ] Ran automated validation gates
- [ ] Verified final production gate criteria
- [ ] Documented before/after metrics

## Anti-Patterns to Avoid

- Skipping P0 security fixes for "quick wins"
- Removing dead code without running tests
- Addressing P2/P3 before P0/P1
- Making large, monolithic PRs instead of batched changes
- Not re-running repowise assessment after changes
- Ignoring health score trends
- Executing workflows without mapping to specific repowise findings

## Example Commands

```
"Execute repowise production readiness workflow on the entire codebase"
"Run production readiness assessment focusing on security and dead code"
"Bring the layer4-agents service to production-ready state"
"Polish the frontend codebase for production deployment"
"Assess and improve code health across all backend layers"
```

## Repowise → Workflow Mapping Reference

| Repowise Tool | Key Output | Target Workflow |
|---|---|---|
| `get_security` | CVEs, secrets, patterns | `/security-auditor`, `/dependency-update` |
| `get_dead_code` | Unused exports, unreachable files | `/dead-code-sweeper` |
| `get_health` | Biomarker findings, health scores | `/code-quality-improvement` |
| `get_risk` | Hotspots, co-change gaps | `/contract-enforcement-auditor` |
| `get_why` | Decision health, intent | `/code-boundary-enforcement` |
| `get_overview` | Architecture baseline | `/launch-readiness-assessment` |

## Required State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn.

```json
{
  "stage": "assessment|prioritization|execution|validation|reporting",
  "agent_id": "repowise-production-readiness-001",
  "baseline_metrics": {
    "health_scores": {},
    "security_posture": {},
    "dead_code_count": {},
    "risk_hotspots": []
  },
  "findings": {
    "P0": [],
    "P1": [],
    "P2": [],
    "P3": []
  },
  "executed_workflows": [],
  "current_priority_tier": "P0|P1|P2|P3",
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

- [ ] State JSON updated with current stage, baseline metrics, findings, and executed workflows
- [ ] Circuit breaker evaluated before retrying after tool errors or self-correction loops
- [ ] All repowise assessment tools called in Phase 1
- [ ] Findings classified into priority tiers in Phase 2
- [ ] Workflows executed in priority order in Phase 3
- [ ] Validation gates run in Phase 4
- [ ] Before/after metrics documented
- [ ] No security, tenant-isolation, contract, governance, or frontend-design assertions weakened

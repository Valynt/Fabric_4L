---
skill_id: repowise-production-readiness
name: repowise-production-readiness
version: 1.0.0
description: Systematic codebase transformation using repowise MCP intelligence to bring code from functional to production-ready through assessment, prioritization, and execution
side_effects: read, write
timeout_ms: 300000
required_context:
  - project_graph
allowed_agents:
  - "*"
related_workflow:
  - repowise-production-readiness
---

# Repowise Production Readiness — systematic codebase transformation

Transform a codebase from functional to production-ready using repowise MCP intelligence. This skill orchestrates assessment, prioritization, and execution through existing workflows.

## When to use
- Preparing for production deployment
- After major feature development
- Periodic technical debt cleanup
- Code health assessment requests
- Security and compliance audits

## The systematic procedure

### Phase 1: Comprehensive Assessment
Run these repowise tools in parallel to establish baseline:

1. **Repository baseline**
   - `mcp0_get_overview` - Architecture, module boundaries, entry points
   - `mcp0_get_health` - Per-file health scores, biomarker findings, KPIs
   - `mcp0_get_security` - CVEs, secrets, pattern findings

2. **Risk analysis**
   - `mcp0_get_risk` - Hotspots, dependents, co-change partners
   - `mcp0_get_dead_code` - Unreachable files, unused exports, zombie packages
   - `mcp0_get_why` - Architectural decisions and intent

3. **Targeted deep dives** (as needed)
   - `mcp0_get_context` - Documentation, ownership, freshness for critical files
   - `mcp0_get_symbol` - Caller/callee analysis for high-risk symbols
   - `mcp0_search_codebase` - Pattern searches across code and docs

### Phase 2: Prioritization Framework

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

### Phase 3: Execution with Workflow Mapping

Execute in priority order, mapping repowise findings to existing workflows:

**Security & Critical Fixes (P0)**
- `get_security` findings → `/security-auditor` workflow
- Live secrets → Immediate remediation, rotate credentials
- CVEs → `/dependency-update` workflow with security patches

**Dead Code Removal (P0-P1)**
- `get_dead_code` safe_to_delete → `/dead-code-sweeper` workflow
- Remove unreachable files, unused exports, zombie packages
- Verify with test suite after each batch

**Contract & Governance (P0-P1)**
- `get_risk` governance gaps → `/contract-enforcement-auditor` workflow
- Missing co-changes → Implement identified dependencies
- API drift → Regenerate contracts, update consumers

**Code Quality (P1-P2)**
- `get_health` biomarker findings → `/code-quality-improvement` workflow
- Low health score files → Targeted refinement
- Fragility patterns → Add error handling, validation

**Architecture & Boundaries (P1-P2)**
- `get_why` decision health → `/code-boundary-enforcement` workflow
- Ownership gaps → Update CODEOWNERS, assign responsibility
- Module boundary violations → Refactor to canonical paths

**Frontend Polish (P2-P3)**
- `get_health` frontend biomarkers → `/fabric_ui_drift_agent` workflow
- Component health → `/react_component_design` + `/code-quality-improvement`
- Accessibility gaps → `/palette-ux-agent` workflow

### Phase 4: Validation & Iteration

**Continuous Re-Assessment**
- After each P0/P1 batch, re-run `get_health` and `get_security` to verify improvement
- Track health score trends over iterations
- Use `get_risk` to ensure no new hotspots introduced

**Automated Validation Gates**
- `make verify` - Full contract and governance checks
- `make test` - Backend test suite
- `pnpm --dir apps/web run test` - Frontend test suite
- `/launch-readiness-assessment` - Production readiness evaluation

**Iteration Strategy**
1. Batch by priority - Complete all P0 before P1
2. Small, focused PRs - Each workflow produces reviewable changes
3. Rollback safety - Dead code removal batches are reversible
4. Health score tracking - Quantify improvement per iteration

**Final Production Gate**
- `get_health` shows no critical biomarkers
- `get_security` returns no high-severity CVEs or live secrets
- `get_dead_code` returns no safe-to-delete findings
- `get_risk` shows acceptable hotspot distribution
- All workflows pass with no blockers

## What to log
- Initial health scores and security posture (baseline)
- Priority classification for each finding
- Which workflow addressed which finding
- Health score improvements per iteration
- Any blockers or escalation decisions

## Anti-patterns
- Skipping P0 security fixes for "quick wins"
- Removing dead code without running tests
- Addressing P2/P3 before P0/P1
- Making large, monolithic PRs instead of batched changes
- Not re-running repowise assessment after changes
- Ignoring health score trends

## Repowise → Workflow Mapping Reference

| Repowise Tool | Key Output | Target Workflow |
|---|---|---|
| `get_security` | CVEs, secrets, patterns | `/security-auditor`, `/dependency-update` |
| `get_dead_code` | Unused exports, unreachable files | `/dead-code-sweeper` |
| `get_health` | Biomarker findings, health scores | `/code-quality-improvement` |
| `get_risk` | Hotspots, co-change gaps | `/contract-enforcement-auditor` |
| `get_why` | Decision health, intent | `/code-boundary-enforcement` |
| `get_overview` | Architecture baseline | `/launch-readiness-assessment` |

## Self-rewrite hook
If the same class of findings appears repeatedly (e.g., specific biomarker patterns, recurring security issues), update this skill with domain-specific sub-procedures for those patterns.

---
workflow_id: roadmap-management
name: Roadmap Management
version: 1.0.0
description: Comprehensive roadmap management workflow for auditing task status, identifying gaps, proposing additions, and generating work packages
pattern: circuit-breaker
risk_level: low
---

# Roadmap Management Workflow

Use this workflow to systematically manage the ROADMAP.md through two complementary modes:
- **Audit Mode**: Verify current task completion status, detect false completes, and generate next work package
- **Planning Mode**: Assess gaps, identify production blockers, and propose new task additions

## Activation Criteria

**Audit Mode:**
- Daily/weekly execution sync
- Before sprint planning
- Before marking major tasks "Complete"
- After cross-layer refactors

**Planning Mode:**
- Sprint planning sessions
- Pre-release readiness reviews
- Quarterly roadmap updates
- When adding new layers or major features

## Workflow Steps

### 1. Initialize Context
// turbo
- Read `ROADMAP.md` from repository root
- Read any existing gap analysis reports from `.windsurf/plans/`
- Extract production-ready criteria from "Definition of Production Ready" section
- Identify layer structure (L1-L5, FRONTEND, DEVOPS) and current completion state
- Map task dependencies based on "Unblocks" or "Depends on" fields

### 2. Load Task Inventory
- Enumerate tasks (Task N blocks) and extract: title, status text, dependencies, acceptance criteria
- Normalize each task to one layer label: `L1`, `L2`, `L3`, `L4`, `L5`, `Frontend`, `DevOps`
- Count completed vs pending tasks per layer
- Identify tasks with missing acceptance criteria
- Flag placeholder implementations (stubs, TODOs, empty functions)
- Calculate completion percentage per layer and overall

### 3. Collect Ground Truth Evidence (Audit Mode)
For each in-scope task, verify completion strictly using:
- Code exists in referenced files/modules
- Tests exist for the behavior
- Tests execute and pass (or explicitly fail)
- Integration path is wired (not isolated/local only)
Record evidence paths and command output snippets used for each conclusion

### 4. Assign Task-Level Execution Status (Audit Mode)
Assign one status per task:
- `Complete`: Code exists, relevant tests exist and pass, cross-layer integration executes successfully
- `Blocked`: Clear dependency/integration failure prevents completion
- `In Progress`: Meaningful implementation exists but strict completion criteria not fully met
- `Not Started`: No meaningful code path or contract implementation exists

Assign `owner` if explicitly known in roadmap/docs; otherwise use `Unassigned`.
Do not mark `Complete` unless all strict checks pass.

### 5. Run System Integrity Check (Audit Mode)
Validate real execution flows:
- `L2 -> L3` ingestion
- `L4` LangGraph workflow execution/resume path
- `Frontend <-> API` connectivity and route contract alignment

Flag:
- Broken integrations (API mismatch, import/runtime errors, schema drift)
- Missing dependencies (upstream not ready)
- Boundary violations (cross-layer coupling, import side effects)
- Hidden work (retry logic, error handling, persistence, operational hardening)

### 6. Detect False Completes (Audit Mode)
For every task currently labeled complete in roadmap text, attempt real validation.
If runtime/contract checks fail, downgrade to `Blocked` or `In Progress` with rationale.

### 7. Identify Production Blockers (Planning Mode)
Check each criterion in production-ready table:
- End-to-end workflow complete
- All APIs responding (not stubs)
- Frontend showing real data
- Tests passing (>80% coverage)
- Docker deployment working
- Monitoring configured

Map blockers to specific roadmap gaps.

### 8. Generate Concrete Proposals (Planning Mode)
For each identified gap, create:
- **Task Title**: Clear, actionable description
- **Layer**: L1-L5, FRONTEND, or DEVOPS
- **Priority**: P0 (critical path), P1 (important), P2 (nice-to-have)
- **Effort**: Estimated days
- **Unblocks**: What downstream work this enables
- **Acceptance Criteria**: 3-5 bullet points
- **Implementation Hints**: Key files to modify/create

### 9. Sequence by Dependencies (Planning Mode)
- Order proposals using dependency graph
- Ensure upstream blockers are addressed first
- Group parallelizable work into tracks

### 10. Select Next Execution Slice (Audit Mode)
Choose the highest-leverage slice that:
- unblocks downstream tasks
- delivers a real end-to-end capability
- is shippable and testable within 1-3 days

Provide explicit rationale for why this slice wins over alternatives.

### 11. Generate Assignment-Ready Work Package (Audit Mode)
Output:
- Objective (single clear outcome)
- Atomic tasks
- Affected files/modules
- Dependencies
- Risks/edge cases
- Acceptance criteria including real execution checks (not build-only)

### 12. Present for Approval (Planning Mode)
- Display proposed additions formatted for review
- Show before/after completion percentages per layer
- Highlight critical path items with rationale
- Explicitly ask user: "Approve these additions to ROADMAP.md?"
- Await explicit "yes" before proceeding

### 13. Apply Updates (Planning Mode, on explicit approval only)
// turbo
- Insert approved tasks into `ROADMAP.md` using `edit` or `multi_edit`
- Update completion percentages in roadmap headers
- Refresh "Definition of Production Ready" status table
- Run `git add ROADMAP.md` to stage changes
- Confirm to user: "Changes staged. Run `git commit` to finalize."

### 14. Persist Outputs (Audit Mode)
// turbo
- Create/update a timestamped report in `.windsurf/plans/` (e.g., `roadmap-audit-YYYYMMDD-HHMM.md`)
- Include:
  - Task table with status, owner, layer
  - Critical blockers / broken integrations
  - Selected execution slice with rationale
  - Assignment-ready work package
- If user approves, update `ROADMAP.md` to reflect validated status labels and notes

## Constraints

- **Maximum 5 P0 tasks**: Prevent over-prioritization
- **Time-boxed**: Proposals must fit within 4-week horizon by default
- **Dependency-aware**: Never propose downstream work before upstream blockers
- **Measurable**: Every proposal must have verifiable acceptance criteria
- **Evidence-first**: Never mark a task complete without execution evidence

## Output Format

### Audit Mode Output
```markdown
# Roadmap Audit Report - {YYYY-MM-DD}

## Task Status Table
| Task | Status | Owner | Layer | Evidence |
|------|--------|-------|-------|----------|

## Critical Blockers
- [Blocker] -> [Evidence] -> [Impact]

## Selected Execution Slice
**Slice**: [description]
**Rationale**: [why this slice]
**Duration**: 1-3 days

## Work Package
- Objective: [single outcome]
- Tasks: [atomic list]
- Affected modules: [list]
- Dependencies: [list]
- Acceptance criteria: [verifiable checks]
```

### Planning Mode Output
```markdown
## Proposed Roadmap Additions

Generated: {YYYY-MM-DD} | Target: Production Complete ({target}%)

### Track A: Backend Core (2 weeks)

#### Task N: [Title] (P0)
- **Layer**: L2
- **Effort**: 2 days
- **Unblocks**: GraphRAG queries
- **Acceptance Criteria**:
  - [ ] Criterion 1
  - [ ] Criterion 2
- **Implementation**:
  - Modify: `file.py`
  - Create: `new_file.py`
```

## Execution Log Format

Present progress using this structured format:

```
[INIT] Reading ROADMAP.md - Current overall: ~{N}% complete
[INVENTORY] {N} tasks enumerated across {N} layers
[EVIDENCE] Ground truth collected for {N} tasks
[STATUS] Assigned strict status: {N} Complete, {N} In Progress, {N} Blocked, {N} Not Started
[INTEGRITY] System integrity check: {N} broken integrations found
[BLOCKERS] Identified {N} production blockers
[PROPOSALS] Generated {N} P0 tasks, {N} P1 tasks, {N} P2 tasks
[SEQUENCE] Ordered by dependency graph - {N} parallel tracks identified
[SLICE] Selected 1-3 day execution slice: [description]
[PACKAGE] Generated assignment-ready work package
[REVIEW] Presenting to user for approval...
[APPLY] User approved {N}/{total} tasks - Updating ROADMAP.md
[COMPLETE] Roadmap updated, {N} new tasks added, staged for commit
```

## Concrete Actions Checklist

### Audit Mode
- [ ] Parsed all roadmap tasks in scope
- [ ] Assigned normalized layer to each task
- [ ] Gathered evidence from code + tests + runtime checks
- [ ] Produced strict status assignment per task
- [ ] Identified broken integrations and dependency blockers
- [ ] Flagged any false-complete tasks
- [ ] Selected one 1-3 day execution slice
- [ ] Produced assignment-ready package
- [ ] Saved report in `.windsurf/plans/`

### Planning Mode
- [ ] Read and analyzed current `ROADMAP.md` state
- [ ] Identified at least one existing gap analysis report or created one
- [ ] Calculated completion percentages per layer
- [ ] Generated minimum 3 concrete, prioritized tasks
- [ ] Every P0 task has 3-5 verifiable acceptance criteria
- [ ] Identified unblocks/dependencies for each proposed task
- [ ] Presented proposals to user and awaited explicit approval
- [ ] Only after approval: modified `ROADMAP.md`
- [ ] Verified formatting matches existing roadmap style
- [ ] Staged changes for user commit

## Safety Rules

1. **Never mark a task `Complete` without execution evidence**
2. **Prefer runtime/integration truth over narrative summary docs**
3. **Never modify ROADMAP.md without explicit user approval** (Planning Mode)
4. **Preserve existing task structure and formatting**
5. **Do not delete existing tasks** - only add new ones (Planning Mode)
6. **Maintain dependency graph accuracy** when adding tasks
7. **Keep scope to highest-leverage slice; avoid parallel overcommitment** (Audit Mode)
8. **Capture assumptions explicitly when evidence is unavailable**

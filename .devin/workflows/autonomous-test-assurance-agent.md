---
workflow_id: autonomous-test-assurance-agent
name: Autonomous Test Assurance Agent
version: 1.0.0
description: Autonomous Level 4 agent for end-to-end test assurance with self-directed discovery, automatic remediation, and PR-ready delivery without human checkpoints
pattern: manager-worker
risk_level: high
category: testing
---

# Autonomous Test Assurance Agent (Level 4)

A fully autonomous Level 4 agent that independently discovers test gaps, engineers comprehensive test coverage (positive, negative, adversarial), validates fixes, and delivers PR-ready remediation without phase-by-phase human approval.

## Level 4 Autonomy Manifest

- **Self-direction**: Chooses execution path based on discovered state
- **Automatic recovery**: Handles blockers and failures without human intervention
- **Cross-phase optimization**: Uses findings to prioritize and adapt strategy
- **Proactive tool selection**: Determines appropriate tools without explicit direction
- **PR-ready delivery**: Produces commit-ready artifacts with full context and verification

## Mission

Transform this repository's test suite from functional confirmation into production assurance.

## Primary Objective

Create and refactor tests so that every critical security, isolation, authorization, validation, reliability, and governance boundary is verified by executable tests. The suite must prove both that valid behavior works and that invalid, unauthorized, malformed, cross-tenant, and adversarial behavior fails safely.

## Operating Mode

Act as a **Level 4 autonomous agent**:
- **Discover**: Dynamically map repository structure and boundaries
- **Analyze**: Identify invariants, gaps, and risks using code inspection
- **Decide**: Prioritize gaps based on security impact, coverage density, and remediation effort
- **Execute**: Write tests, apply minimal production fixes, run verification autonomously
- **Recover**: Handle failures by adapting strategy
- **Deliver**: Produce signed-off, evidence-backed PR artifacts without human gate

## Core Rule

Every important production invariant must have at least:
1. **One positive test** proving intended behavior works
2. **One negative/adversarial test** proving forbidden behavior is blocked
3. **A regression test** for every discovered violation

---

## Phase 1: Autonomous Repository Discovery

**Agent directive**: Dynamically discover repository structure. Do not wait for human approval between substeps.

```bash
# Map project layout and auth patterns
find . -maxdepth 3 -type f -name "*.py" | head -50 | xargs dirname | sort -u
grep -rE "(@router|@app|\.get\(|\.post\()" services/*/src/ --include="*.py" 2>/dev/null | head -30
grep -rE "(middleware|auth|token|jwt|tenant_id)" services/*/src/ --include="*.py" 2>/dev/null | head -20
find . -name "test_*.py" -o -name "*.test.ts" -o -name "*.spec.ts" 2>/dev/null | head -30
```

Auto-generate `artifacts/testing/test-inventory.md` with discovered structure.

---

## Phase 2: Autonomous Invariant Extraction

**Agent directive**: Dynamically discover and document invariants without waiting for human input.

Extract invariants for: Tenant Isolation, Authentication, Authorization, Input Validation, Secrets Protection, Destructive Operations, Idempotency, Agent/LLM Safety.

Auto-discover boundary enforcement:
```bash
grep -rE "(raise.*Forbidden|HTTPException.*403|Depends.*auth|require_auth)" services/*/src/ --include="*.py" 2>/dev/null | head -20
```

---

## Phase 3: Autonomous Gap Matrix Generation

**Agent directive**: Cross-reference discovered invariants against existing tests. Auto-generate prioritized gap matrix.

Create `artifacts/testing/test-gap-matrix.md` comparing invariants to coverage.

Severity:
- **P0**: Data/security boundary untested or bypassable — BLOCKS RELEASE
- **P1**: Core production workflow lacks failure/negative coverage
- **P2**: Brittle, incomplete, or overly mocked coverage
- **P3**: Cleanup or maintainability improvement

---

## Phase 4: Autonomous Test Engineering

**Agent directive**: Self-direct test implementation based on gap priority. Handle failures without human intervention.

Autonomous workflow per P0/P1 gap: IDENTIFY → LOCATE → POSITIVE → NEGATIVE → VALIDATE → RECOVER → FIX → VERIFY → GATE → RECORD

Required test style: deterministic, self-contained, explicit preconditions, exact expected values, atomic assertions, stable selectors, bounded scope.

See `.devin/skills/autonomous-test-assurance/SKILL.md` for the full security test checklist and example patterns.

---

## Phase 5: Autonomous Test Refactoring

**Agent directive**: Proactively identify and strengthen weak tests.

Anti-patterns to scan for: happy-path-only, vague assertions, compound assertions, over-mocked tests, flaky timing, missing negative cases.

Refactoring rules: preserve intent, strengthen assertions, split compounds, prefer stable selectors, add negatives, do not mock security boundaries.

See `.devin/skills/autonomous-test-assurance/SKILL.md` for before/after refactoring examples.

---

## Phase 6: Autonomous Verification & Recovery

**Agent directive**: Execute full verification pipeline with automatic retry.

```bash
# Narrow tests
pytest tests/security/test_tenant_isolation.py -v

# Broader gates
make test-security
make test-integration
pnpm e2e:smoke
```

Auto-recovery: fix syntax/import errors, document pre-existing failures, add determinism for flaky tests, skip after 3 failures on same boundary.

---

## Phase 7: Autonomous Evidence & Delivery

**Agent directive**: Generate comprehensive, PR-ready remediation report.

Create `artifacts/testing/assurance-remediation-report.md` using the template in `.devin/skills/autonomous-test-assurance/SKILL.md`.

---

## Phase 8: Autonomous Execution (One-Shot)

**Level 4 Master Directive**: Execute all phases without human checkpoints.

Execution flow:
```
START → Phase 1 (Discovery) → Analyze → Adapt
         → Phase 2 (Invariants) + Phase 3 (Gap Matrix)
         → Prioritize gaps → Phase 4 (Test Engineering)
         → Phase 5 (Refactoring) → Phase 6 (Verification)
         → Phase 7 (Reporting) → DELIVER
```

Self-direction rules:
- **Continue automatically**: Single test fixes, clear patterns, stable verification
- **Pause with context**: Architectural blockers, >3 failures on same boundary
- **Auto-commit evidence**: After each phase, save state to `artifacts/testing/progress.log`

---

## High-Value First Targets

Target areas in priority order:
1. **Tenant Isolation** — cross-tenant read/write, spoofed headers, missing context
2. **Authorization** — 401/403 boundaries, role checks, resource ownership
3. **Input Validation** — malformed payloads, unknown fields, unsafe strings
4. **Database/RLS** — USING/WITH CHECK enforcement
5. **Webhook/Job Idempotency** — duplicate events, retries, DLQ
6. **Frontend Route Guards** — auth redirects, tenant switch, error states

See `.devin/skills/autonomous-test-assurance/SKILL.md` for grep commands and full test templates per priority.

---

## CI Gate Definition

Required before merge:
```yaml
- pnpm lint
- pnpm typecheck
- pnpm test:unit
- pnpm test:integration
- pnpm test:security
- pnpm test:contracts
- pnpm test:e2e:smoke
- pnpm audit
- secret scan
- migration validation
```

Merge must fail if any P0/P1 security regression, tenant isolation, or auth negative test fails.

---

## Required State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn.

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "autonomous-test-assurance-agent-001",
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

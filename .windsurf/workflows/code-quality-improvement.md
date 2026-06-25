---
workflow_id: code-quality-improvement
name: Code Quality Improvement
version: 1.0.0
description: Systematic code quality improvement workflow for transforming functional code into production-grade output through inspection, analysis, and targeted fixes
pattern: circuit-breaker
risk_level: low
category: code-review
---

# Code Quality Improvement Workflow

This workflow transforms functional code into production-grade code through focused inspection, risk ranking, targeted fixes, and validation. It is the Windsurf counterpart to `.devin/workflows/code-quality-improvement.md` so repowise and other orchestration workflows can route code-health findings consistently across harnesses.

## When to Use

- Code is functional but rough, fragile, or incomplete.
- A code review identifies quality gaps.
- Repowise or another health tool reports maintainability, fragility, or biomarker findings.
- A generated React component needs a production-readiness pass.
- A narrow technical-debt cleanup has clear files and acceptance criteria.

## When to Stop

- Remaining issues are cosmetic or outside the requested scope.
- Further refactoring would increase behavioral risk.
- The targeted P0/P1 quality issues are fixed and validated.
- The relevant tests and checks have been run or the validation blocker is documented.

## Workflow Steps

### 1. Inspect the Implementation

- Identify the canonical source-of-truth files and layer boundary.
- Read the touched files and nearby tests before editing.
- Check for contract, tenant-isolation, schema, and frontend design-system impact.
- For `apps/web/`, read `DESIGN.md` before changing UI code.
- Use Windows-safe searches:
  - Prefer `rg`.
  - Exclude generated/cache directories with globs such as `--glob '!.pytest_cache/**' --glob '!node_modules/**' --glob '!__pycache__/**'`.
  - If a grep fallback is required, search explicit source roots rather than the repository root.

### 2. Identify Weaknesses

Classify findings by production risk:

- **P0 Incorrectness:** failing tests, broken validation, unsafe behavior, missing assertions.
- **P0 Incompleteness:** missing edge cases, partial error handling, absent null/None checks.
- **P1 Fragility:** hardcoded external assumptions, direct dependency construction, missing retries, weak error boundaries.
- **P2 Maintainability:** confusing names, duplicated logic, oversized functions, magic constants.
- **P3 Performance:** unbounded queries, unnecessary re-renders, repeated I/O, missing caching.

For React components, also check accessibility, loading/error/empty states, TanStack Query usage, and consistency with shared UI primitives.

### 3. Prioritize Fixes

- Fix P0 before P1, and P1 before P2/P3.
- Prefer tests or contract checks that prove intended and denied behavior.
- Keep the diff small enough to review safely.
- Do not weaken auth, RBAC, tenant isolation, governance middleware, contracts, or production gates.

### 4. Make Targeted Fixes

- Add validation and explicit failure modes for missing edge cases.
- Improve error handling without exposing secrets, stack traces, provider internals, or cross-tenant data.
- Extract or simplify repeated or deeply nested code only when it reduces real complexity.
- Replace magic values with local constants where that improves clarity.
- Strengthen tests for the changed behavior, especially hostile tenant/security cases when relevant.

### 5. Verify Improvements

Run the narrowest relevant checks first, then broaden as needed:

- Python: `python -m pytest path/to/relevant/tests`
- Frontend: `pnpm --dir apps/web run test`
- Frontend build: `pnpm --dir apps/web run build`
- Contracts: `python -m pytest tests/contract`
- Repo gate when appropriate: `make verify`

Record commands exactly. Do not claim tests passed unless they actually ran.

## Required State JSON

Every workflow execution maintains this state:

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "code-quality-improvement-001",
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

## Circuit Breaker

```yaml
circuit_breaker:
  max_tool_errors: 3
  max_self_correction_loops: 2
  action_on_trip: halt_and_escalate
  escalation_path: "log_and_notify"
```

## Completion Checklist

- [ ] Canonical files and layer boundary identified.
- [ ] P0/P1 findings addressed before lower-priority polish.
- [ ] Tests or checks updated where behavior changed.
- [ ] Relevant validation commands run and recorded.
- [ ] Search commands avoided cache/generated directory permission traps.
- [ ] No architecture, tenant-isolation, contract, governance, security, or frontend-design assertions weakened.


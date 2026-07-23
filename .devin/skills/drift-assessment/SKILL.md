---
description: Multi-layer drift detection for API contracts, schemas, and behavior drift
---

# Drift Assessment Workflow

Use this workflow to detect and report drift across all system boundaries: API contracts between layers, frontend/backend alignment, and schema evolution.

## Activation Criteria

Manual activation:
- After code changes that touch API routes or schemas
- Before releases to catch breaking changes
- Weekly automated drift report
- When integration tests fail unexpectedly

## Drift Types Detected

1. **OpenAPI Contract Drift**: Implementation routes/schemas vs OpenAPI specs
2. **Frontend/Backend Drift**: Hook expectations vs actual API responses
3. **Schema Drift**: Database schema vs model definitions
4. **Cross-Layer Drift**: L2→L3→L4 data flow contract violations

## Workflow Steps

### 1. Collect Contract Evidence

Run contract tests to detect drift:
```bash
python -m pytest tests/contract/ -v --tb=short
```

Capture:
- Failing schema validations
- Missing routes in OpenAPI specs
- Enum mismatches
- Required field violations

### 2. Verify OpenAPI Generation

Regenerate contracts and check for diffs:
```bash
python scripts/export_openapi.py
git diff contracts/openapi/
```

Flag:
- Undocumented new endpoints
- Removed/renamed routes without version bump
- Schema field changes (added/removed/retyped)

### 3. Check Frontend API Hook Alignment

Validate TypeScript hook expectations against OpenAPI:
- Compare `apps/web/src/hooks/*.ts` types to OpenAPI schemas
- Flag mismatches in request/response shapes
- Detect missing error handling for new error codes

### 4. Cross-Layer Integration Check

Verify end-to-end data flow contracts:
- L2 extraction output → L3 ingestion input
- L3 graph API → L4 agent tools
- L4 workflows → Frontend SSE events

Run integration tests:
```bash
python -m pytest tests/integration/ -v
```

### 5. Schema Evolution Audit

Check database schema alignment:
- Alembic migrations vs SQLAlchemy models
- Neo4j graph schema vs Pydantic models
- pgvector table schemas vs TypeScript interfaces

### 6. Generate Drift Report

Output structured findings:
- **Critical**: Breaking changes requiring immediate fix
- **Warning**: Non-breaking additions (missing docs)
- **Info**: Detected but acceptable drift

## Required Output Format

```markdown
# Drift Assessment Report YYYY-MM-DD

## Summary
- Total drift instances: N
- Critical: N | Warning: N | Info: N

## OpenAPI Contract Drift
| Route | Issue | Severity | Fix Required |
|-------|-------|----------|--------------|

## Frontend/Backend Drift
| Hook | Expected | Actual | Impact |
|------|----------|--------|--------|

## Cross-Layer Integration
| Flow | Status | Evidence |
|------|--------|----------|

## Recommended Actions
1. [Priority] Fix critical drift items
2. [Priority] Update documentation for warnings
3. [Priority] Add regression tests
```

## Concrete Checklist

- [ ] Contract tests executed with results captured
- [ ] OpenAPI regenerated and diff reviewed
- [ ] Frontend hooks compared to backend schemas
- [ ] Cross-layer integration tests pass/fail recorded
- [ ] Schema evolution checked (migrations vs models)
- [ ] Drift report generated with severity classification
- [ ] Critical drift items have assigned owners

## Safety Rules

1. Never ignore Critical drift before production deploy
2. Document all drift findings with evidence (command output, diffs)
3. Prefer fixing upstream (OpenAPI/implementation) over downstream workarounds
4. Run this workflow before any release candidate
5. If drift is intentional (major version bump), document the breaking change

## Integration with CI

Add to `.github/workflows/pr-checks.yml`:
```yaml
drift-check:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: python -m pytest tests/contract/ -v --tb=short
    - run: python scripts/export_openapi.py
    - run: git diff --exit-code contracts/openapi/ || echo "::warning::OpenAPI drift detected"
```
## Required State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn.

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "drift-assessment-001",
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

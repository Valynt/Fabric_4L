---
description: Step-by-step operational workflow for auditing tests, applying targeted rewrites, executing suites, diagnosing failures, and resolving them safely
---

# Test Quality Remediation Workflow

A step-by-step operational workflow for auditing tests, applying targeted rewrites, executing suites, diagnosing failures, and resolving them safely.

## Overview

This workflow guides systematic test quality improvement across the Value Fabric repository. It applies to both Python/pytest (backend layers) and TypeScript/Vitest (frontend).

**Prerequisites**:
- Review `.devin/skills/test-quality-auditor/SKILL.md` for evaluation criteria
- Access to repository with all layers present
- Python 3.11+ and Node.js/pnpm installed

---

## Phase 1: Discovery

**Goal**: Map the complete testing landscape.

### 1.1 Identify Repository Structure
```bash
# Check for monorepo structure
ls -la services/
ls -la apps/web/
```

### 1.2 Detect Test Frameworks
```bash
# Python layers
find value-fabric -name "pyproject.toml" -exec grep -l pytest {} \;
find value-fabric -name "pytest.ini" -o -name "setup.cfg"

# Frontend
cat apps/web/package.json | grep -A5 "devDependencies"
```

### 1.3 Locate Test Files
```bash
# Python tests
find value-fabric -name "test_*.py" -o -name "*_test.py"

# TypeScript tests
find apps/web -name "*.test.ts" -o -name "*.test.tsx" -o -name "*.spec.ts"
```

### 1.4 Identify CI/Test Scripts
```bash
# Check for GitHub Actions
ls -la .github/workflows/

# Check for Makefile, justfile, scripts
ls -la scripts/
cat package.json | grep -A10 '"scripts"'
```

### 1.5 Document Coverage Tools
```bash
# Check for coverage configuration
grep -r "pytest-cov\|coverage" services/*/pyproject.toml
grep -r "coverage\|istanbul" apps/web/package.json
```

### Discovery Output
Create a concise testing map documenting:
- Frameworks per layer (pytest, Vitest, Playwright)
- Test file locations and counts
- Coverage tooling presence
- CI integration status
- Known gaps (no tests, missing coverage)

---

## Phase 2: Audit

**Goal**: Evaluate all tests against quality principles.

### 2.1 Review Skill Documentation
Read `.devin/skills/test-quality-auditor/SKILL.md` before starting evaluation.

### 2.2 Evaluate Each Test File

For each test file, assess:

```markdown
## File: path/to/test_file.py

### Overview
- Test count: N
- Lines of code: N
- Fixtures used: list
- External mocks: list

### Principle Scores (1-5)
| Principle | Score | Evidence |
|-----------|-------|----------|
| Behavior-Focused | X | Notes |
| Clear/Readable | X | Notes |
| Focused | X | Notes |
| Deterministic | X | Notes |
| Isolated | X | Notes |
| Meaningful | X | Notes |
| Maintainable | X | Notes |
| **Total** | XX/35 | |

### Issues Found
- **P0**: Critical issues
- **P1**: Material issues
- **P2**: Improvement opportunities

### Recommended Action
- [ ] Leave as-is
- [ ] Rewrite (specify which tests)
- [ ] Add missing coverage
- [ ] Delete (with rationale)
```

### 2.3 Categorize Issues

**By Severity**:
- P0: Block release, fix immediately
- P1: Fix in this sprint
- P2: Fix opportunistically

**By Type**:
- behavior_not_implementation
- weak_naming
- mixed_concerns
- flaky_timing
- shared_state_leakage
- poor_isolation
- over_mocking
- under_asserting
- missing_edge_cases
- unreadable_setup

### 2.4 Prioritize Rewrites

Sort rewrites by:
1. P0 issues first
2. Pre-existing failures
3. Core/critical path tests
4. Most impactful P1 issues
5. P2 improvements (deferred)

### Audit Output
`artifacts/testing/test-quality-audit.md` with:
- Per-file assessments
- Categorized issues by severity
- Prioritized rewrite list
- Rationale for each recommendation

---

## Phase 3: Prioritization

**Goal**: Determine rewrite order for maximum impact.

### 3.1 Create Rewrite Queue

```markdown
## Rewrite Priority Queue

### P0 - Critical
1. [ ] test_file_x.py - Flaky state machine tests
2. [ ] test_file_y.py - Race condition in async tests

### P1 - Material
1. [ ] test_api.py - Implementation coupling in assertions
2. [ ] test_models.py - Weak naming, unclear intent

### P2 - Improvement
1. [ ] test_utils.py - Could extract common setup
```

### 3.2 Estimate Effort

For each rewrite:
- Small: < 30 min (rename, restructure)
- Medium: 30-60 min (rewrite assertions, fix isolation)
- Large: > 60 min (architectural changes, new fixtures)

### 3.3 Sequence for Safety

1. Start with tests that have no dependents
2. Fix shared fixtures before dependent tests
3. Group by related functionality
4. Leave complex refactors for last

---

## Phase 4: Rewrite

**Goal**: Execute targeted rewrites safely.

### 4.1 Before Starting Each Rewrite

**Explicitly state**:
- Principle violation
- Risk it creates
- Why rewrite is justified
- Expected outcome

### 4.2 Rewrite Process

1. **Read original test** - Understand intended coverage
2. **Identify issues** - Match against anti-patterns
3. **Draft new structure** - Plan AAA organization
4. **Implement rewrite** - Make minimal, focused changes
5. **Preserve behavior** - Ensure same regressions caught
6. **Add documentation** - Comments for complex setup

### 4.3 Rewrite Patterns

**Renaming**:
```python
# Before
def test_case_1(self): ...

# After
def test_advances_to_supported_when_confidence_above_threshold(self): ...
```

**Restructuring**:
```python
# Before - mixed concerns
def test_full_flow(self):
    # Create
    x = create()
    assert x.id
    # Update
    y = update(x)
    assert y.status
    # Delete
    delete(y)
    assert deleted

# After - focused tests
def test_creates_with_valid_data(self): ...
def test_updates_status_successfully(self): ...
def test_soft_deletes_removing_access(self): ...
```

**Fixing Isolation**:
```python
# Before - shared state
COUNTER = 0

def test_increment(self):
    global COUNTER
    COUNTER += 1
    assert COUNTER == 1  # Fails on second run!

# After - fixture-based isolation
@pytest.fixture
def counter():
    return {"value": 0}

def test_increment(self, counter):
    counter["value"] += 1
    assert counter["value"] == 1
```

**Removing Timing Flakiness**:
```python
# Before - real timing
async def test_timeout(self):
    start = time.time()
    await process()
    assert time.time() - start < 5  # Flaky!

# After - deterministic
def test_timeout(self, mock_time):
    mock_time.return_value = [0, 10]  # Mock time passage
    result = await process()
    assert result.timed_out
```

### 4.4 Post-Rewrite Checklist

- [ ] Test passes (run 5x to verify determinism)
- [ ] Name describes behavior
- [ ] AAA structure clear
- [ ] No implementation coupling
- [ ] All meaningful outcomes asserted
- [ ] Would catch intended regressions

---

## Phase 5: Validation

**Goal**: Run tests and confirm quality improvements.

### 5.1 Run Targeted Tests First

```bash
# Single file
cd services/layer5-ground-truth
pytest tests/test_state_machine.py -v

# Run 5x to verify determinism
for i in {1..5}; do pytest tests/test_state_machine.py -q; done
```

### 5.2 Run Layer-Specific Suites

```bash
# Layer 5
cd services/layer5-ground-truth && pytest -v

# Layer 3
cd services/layer3-knowledge && pytest -v

# Layer 1
cd services/layer1-ingestion && pytest -v
```

### 5.3 Run Full Suite

```bash
# If there's a root-level test runner
pytest services/

# Or per-layer combined
for layer in layer{1..5}-*; do
  echo "=== Testing $layer ==="
  (cd "services/$layer" && pytest -q)
done
```

### 5.4 Failure Triage

**For each failure, determine**:

| Category | Cause | Action |
|----------|-------|--------|
| Rewrite Error | Bug introduced during rewrite | Fix rewrite |
| Pre-existing | Was failing before changes | Document separately |
| Flaky | Environmental/timing | Fix determinism |
| App Bug Exposed | Test correctly finds bug | Fix production code |

### 5.5 Cure Failures

**If rewrite is wrong**:
1. Re-read original test intent
2. Fix the rewrite
3. Re-run

**If production code is wrong**:
1. Verify test expresses correct intended behavior
2. Fix production code
3. Re-run

**If pre-existing failure**:
1. Document in `artifacts/testing/pre-existing-failures.md`
2. Mark with `@pytest.mark.skip(reason="pre-existing failure, ticket #X")`
3. Do not weaken assertions to "fix"

---

## Phase 6: Reporting

**Goal**: Document complete remediation effort.

### 6.1 Report Structure

```markdown
# Test Quality Remediation Report

## Executive Summary
- Tests audited: N files, N tests
- Rewrites completed: N
- New tests added: N
- Failures resolved: N
- Pre-existing failures documented: N
- Final status: PASS / PARTIAL / FAIL

## Repository Testing Landscape
[Summary from Discovery phase]

## Skill and Workflow Summary
- Created: .devin/skills/test-quality-auditor/SKILL.md
- Created: .devin/workflows/test-quality-remediation.md

## Audit Summary
- Total files reviewed: N
- Average quality score: X/35
- P0 issues found: N
- P1 issues found: N
- P2 issues found: N

## Rewrites Completed
### File: test_x.py
- **Issue**: [description]
- **Principle Violated**: [which principle]
- **Change**: [what was changed]
- **Rationale**: [why justified]

## New Tests Added
### File: test_y.py::test_new
- **Purpose**: [what behavior covered]
- **Gap Addressed**: [what was missing]

## Failures Encountered
| Test | Initial Status | Root Cause | Resolution |
|------|---------------|------------|------------|
| test_a | Rewrite error | Missing await | Added async fixture |
| test_b | Pre-existing | DB schema drift | Documented, ticket #123 |

## Final Test Status
- Layer 5: X/X passing
- Layer 3: X/X passing
- Layer 1: X/X passing
- Layer 2: X/X passing
- Layer 4: NO TESTS (gap documented)
- Frontend: NO TESTS (infrastructure exists)

## Remaining Risks
- [ ] Risk description

## Recommended Follow-up
1. [Next action]
2. [Next action]
```

---

## Rollback and Escalation Rules

### When to Rollback

1. **Cascade of failures**: Rewrites cause >3 unrelated tests to fail
2. **Production bug introduced**: Fix would require production changes >50 lines
3. **Uncertain intent**: Cannot determine original test's purpose
4. **Time exceeded**: Rewrite estimate was wrong by >2x

**Rollback process**:
```bash
git checkout -- path/to/test_file.py
git checkout -- path/to/conftest.py
pytest tests/related/  # Verify clean state
```

### When to Escalate

1. **Architecture problem**: Issue requires framework-level changes
2. **Test design disagreement**: Unclear if test should be rewritten
3. **Production bug found**: Rewrites exposed real bugs requiring team decision
4. **Policy violation**: Test patterns violate team conventions

**Escalation process**:
1. Document in `artifacts/testing/escalation-needed.md`
2. Include: test file, issue, attempted resolution, question for team
3. Skip test if needed: `@pytest.mark.skip(reason="escalated: see #ticket")`

---

## Final Checklist

Before completing remediation:

- [ ] Skill document created and reviewed
- [ ] Workflow document created and reviewed
- [ ] All test files audited
- [ ] Audit artifact produced
- [ ] P0 issues resolved
- [ ] P1 issues addressed or documented
- [ ] Rewrites pass consistently (5x runs)
- [ ] Layer-specific suites pass
- [ ] Pre-existing failures documented
- [ ] Final report produced
- [ ] No weakened assertions without explicit rationale
- [ ] Repository conventions preserved

---

## Quick Reference

### Running Tests by Layer
```bash
# Layer 5 (Ground Truth)
cd services/layer5-ground-truth && pytest -v --tb=short

# Layer 3 (Knowledge)
cd services/layer3-knowledge && pytest -v --tb=short

# Layer 1 (Ingestion)
cd services/layer1-ingestion && pytest tests/unit -v --tb=short

# Layer 2 (Extraction)
cd services/layer2-extraction && pytest -v --tb=short

# Frontend (Vitest)
cd frontend && pnpm test
```

### Test Markers
```python
@pytest.mark.unit        # No external deps
@pytest.mark.integration # Requires services
@pytest.mark.asyncio     # Async test
@pytest.mark.slow        # Long-running
@pytest.mark.skip        # Known issue
```

### Coverage Commands
```bash
# Python
pytest --cov=src --cov-report=term-missing --cov-report=html

# TypeScript/Vitest
pnpm test --coverage
```
## Required State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn.

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "test-quality-remediation-001",
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

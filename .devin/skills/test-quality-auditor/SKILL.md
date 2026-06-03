---
skill_id: test-quality-auditor
name: test-quality-auditor
version: 1.0.0
description: Evaluate test suites against quality principles and safely rewrite tests for Python/pytest and TypeScript/Vitest
side_effects: none
timeout_ms: 30000
required_context:
  - project_graph
  - test_inventory
allowed_agents:
  - "*"
---

# Test Quality Auditor Skill

A comprehensive guide for evaluating tests against high-quality testing principles, identifying issues, and safely rewriting tests for the Value Fabric repository.

## Overview

This skill enables systematic evaluation of test suites against seven core testing principles. It applies to both **Python/pytest** (backend layers 1-5) and **TypeScript/Vitest/Playwright** (frontend).

---

## Core Testing Principles

### 1. Behavior-Focused
- Verifies externally meaningful behavior, contract, or business rule
- Avoids asserting irrelevant internals unless the internal contract is itself under test
- **Anti-pattern**: Testing that a specific private method was called

### 2. Clear and Readable
- Test name clearly states expected behavior and condition
- Arrange / Act / Assert structure is obvious
- Minimal noise, magic numbers, unnecessary setup
- **Pattern**: `test_<action>_<condition>_<expected_result>`

### 3. Focused
- Tests one behavior at a time
- Avoids combining unrelated assertions into one brittle test
- **Rule**: One logical concept per test function

### 4. Deterministic
- No flaky timing assumptions
- No uncontrolled randomness
- No hidden dependency on environment, execution order, external services, or shared mutable state
- **Fix**: Use deterministic fixtures, freeze time, mock external services

### 5. Isolated
- Uses mocks, fakes, fixtures, factories, or test data appropriately
- Does not leak state across tests
- Cleans up resources properly
- **Pattern**: Fresh database transaction per test, rollback on teardown

### 6. Meaningful
- Covers business rules, edge cases, failure modes, and critical paths
- Not merely duplicating implementation line-by-line
- Not asserting trivialities that provide little confidence
- **Question**: Would this test catch a regression that matters?

### 7. Maintainable
- Resilient to harmless refactors
- Avoids over-coupling to implementation details
- Uses helpers and fixtures only when they improve clarity
- **Rule**: Test the contract, not the implementation

---

## Issue Severity Classification

### P0 - Critical (Fix Immediately)
- Dangerously misleading test (passes but behavior is wrong)
- Highly flaky test blocking reliable releases
- Test with false negatives (fails when it should pass)
- Race conditions or shared state leakage
- **Action**: Rewrite or delete immediately

### P1 - Material (Fix Soon)
- Tests implementation details instead of behavior
- Brittle assertions that break on harmless refactors
- Weak naming that obscures intent
- Missing critical edge case coverage
- Over-mocking that reduces confidence
- **Action**: Prioritize for targeted rewrite

### P2 - Improvement (Nice to Have)
- Test could be more readable with better structure
- Minor duplication that could be extracted
- Snapshots that could be more specific
- **Action**: Address when touching related code

---

## Common Anti-Patterns Catalog

### Python/pytest Anti-Patterns

| Anti-Pattern | Detection | Remediation |
|--------------|-----------|-------------|
| **Implementation Coupling** | Asserts on internal method calls, private attributes | Assert on outputs, behavior, or public API |
| **Weak Naming** | `test_function1`, `test_case_a` | Rename to `test_advances_to_supported_with_high_confidence` |
| **Mixed Concerns** | Multiple unrelated assertions in one test | Split into focused tests with single responsibility |
| **Hidden Async Issues** | Missing `await`, non-async fixtures for async code | Use `pytest-asyncio`, mark with `@pytest.mark.asyncio` |
| **Shared State Leakage** | Tests pass in isolation but fail together | Use function-scoped fixtures, transaction rollback |
| **Over-Mocking** | Mocks the system under test itself | Mock boundaries (DB, HTTP), not core logic |
| **Under-Asserting** | Single weak assertion on complex operation | Assert all meaningful outcomes |
| **Magic Numbers** | Hardcoded values without context | Use named constants or factory helpers |
| **Missing Edge Cases** | Only tests happy path | Add tests for null, empty, invalid, boundary values |
| **Slow Integration Tests** | Tests hitting real external services | Use mocks, testcontainers, or mark as `integration` |

### TypeScript/Vitest Anti-Patterns

| Anti-Pattern | Detection | Remediation |
|--------------|-----------|-------------|
| **Testing Implementation** | Asserts on internal state, private methods | Assert on rendered output, public API, user-visible behavior |
| **Shallow Rendering** | Tests component internals not user experience | Use `@testing-library/react`, query by role/text |
| ** Brittle Selectors** | Uses CSS classes, IDs, DOM structure | Use `screen.getByRole`, `getByText`, `getByTestId` |
| **Missing Async Handling** | Not awaiting user events or async operations | Use `await userEvent.click()`, `waitFor` |
| **Incomplete Act** | Calling functions without proper context | Wrap in `act()` or use testing-library utilities |
| **Snapshot Misuse** | Large snapshots capturing irrelevant details | Use specific assertions or targeted snapshots |
| **Mock Over-Stubbing** | Mocks return unrealistic data | Use factories that produce valid test data |
| **Race Conditions** | Tests pass/fail inconsistently | Use `waitFor`, avoid real timers, mock `setTimeout` |

---

## Stack-Specific Guidance

### Python / pytest

#### Test Structure Pattern
```python
class TestSpecificBehavior:
    """Docstring describing the behavior being tested."""

    @pytest.mark.asyncio
    async def test_<action>_<condition>_<expected_result>(self, db, fixture):
        """Should <expected behavior> when <condition>."""
        # Arrange
        entity = make_entity(status=Status.EXTRACTED)
        db.add(entity)
        await db.flush()

        # Act
        result = await service.process(entity)

        # Assert
        assert result.status == Status.SUPPORTED
        assert result.processed_at is not None
```

#### Fixture Best Practices
```python
# Use session-scoped for expensive setup (database engine)
@pytest.fixture(scope="session")
async def engine():
    ...

# Use function-scoped for isolation (transactions)
@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    async with factory() as session:
        await session.begin_nested()  # SAVEPOINT
        yield session
        await session.rollback()  # Clean isolation

# Factory functions over complex fixtures
def make_entity(**overrides) -> Entity:
    """Return a valid entity with defaults, allowing overrides."""
    base = {"field": "default", "status": Status.PENDING}
    base.update(overrides)
    return Entity(**base)
```

#### Markers to Use
```python
@pytest.mark.asyncio  # For async tests
@pytest.mark.unit     # Fast, no external deps
@pytest.mark.integration  # Requires services (Redis, DB, etc.)
@pytest.mark.slow     # Long-running tests
```

#### Running Tests by Layer
```bash
# Layer 5 (Ground Truth)
cd services/layer5-ground-truth
pytest -v

# Layer 3 (Knowledge)
cd services/layer3-knowledge
pytest -v

# Specific test file
pytest tests/test_state_machine.py -v

# With coverage
pytest --cov=src --cov-report=term-missing
```

### TypeScript / Vitest / Playwright

#### Test Structure Pattern
```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

describe('ComponentName', () => {
  describe('when specific condition', () => {
    it('should exhibit expected behavior', async () => {
      // Arrange
      const user = userEvent.setup();
      render(<Component prop={value} />);

      // Act
      await user.click(screen.getByRole('button', { name: /submit/i }));

      // Assert
      expect(screen.getByText(/success/i)).toBeInTheDocument();
    });
  });
});
```

#### Frontend Testing Hierarchy
1. **Unit tests** (Vitest): Pure functions, utilities, hooks
2. **Component tests** (Vitest + React Testing Library): Individual components
3. **Integration tests** (Vitest): Component combinations
4. **E2E tests** (Playwright): Critical user flows

#### Running Frontend Tests
```bash
# Unit tests
cd frontend
pnpm test

# With coverage
pnpm test --coverage

# Watch mode
pnpm test --watch

# E2E tests
pnpm playwright test
```

---

## Safe Rewrite Patterns

### When Rewriting is Justified

1. **P0 Issue Present**: Flaky, misleading, or blocking
2. **Pre-existing Failure**: Test is already failing
3. **Implementation Coupling**: Test will break on harmless refactor
4. **Unclear Intent**: Test name doesn't describe behavior
5. **Missing Coverage**: Rewrite adds missing edge case

### When NOT to Rewrite

1. Test passes and provides meaningful coverage
2. Style differs but doesn't violate principles
3. Minor readability improvement (P2)
4. Test is stable and focused

### Rewrite Guardrails

1. **Preserve Coverage**: Never silently delete valuable assertions
2. **Minimal Diff**: Change only what's necessary
3. **Document Rationale**: Comment why rewrite was needed
4. **Validate Behavior**: Ensure rewritten test catches the same regressions
5. **One Behavior**: Don't combine multiple behaviors into one test during rewrite

### Rewrite Checklist

Before submitting rewritten test:
- [ ] Test name describes behavior clearly
- [ ] AAA structure is obvious
- [ ] All meaningful outcomes asserted
- [ ] No implementation internals asserted (unless testing the internal)
- [ ] Deterministic (no timing, no randomness)
- [ ] Isolated (no shared state)
- [ ] Passes consistently (run 5x to verify)
- [ ] Would catch the regression it's meant to catch

---

## Evaluation Rubric

For each test file, score against principles:

| Principle | Score | Notes |
|-----------|-------|-------|
| Behavior-Focused | 1-5 | 5 = tests contract/behavior, 1 = tests implementation |
| Clear/Readable | 1-5 | 5 = obvious AAA, clear naming, minimal noise |
| Focused | 1-5 | 5 = single behavior, 1 = multiple unrelated assertions |
| Deterministic | 1-5 | 5 = always passes/fails same way |
| Isolated | 1-5 | 5 = no shared state, proper cleanup |
| Meaningful | 1-5 | 5 = covers critical paths, edge cases |
| Maintainable | 1-5 | 5 = resilient to harmless refactors |

**Scoring**:
- 30-35: Excellent (P2 improvements only)
- 25-29: Good (minor P1 issues)
- 20-24: Fair (P1 rewrites recommended)
- Below 20: Poor (P0/P1 rewrites required)

---

## Related Resources

- Repository Testing Map: See `artifacts/testing/test-quality-audit.md`
- Operational Workflow: See `docs/workflows/test-quality-remediation.md`
- pytest Documentation: https://docs.pytest.org/
- Vitest Documentation: https://vitest.dev/
- React Testing Library: https://testing-library.com/docs/react-testing-library/intro/
- Playwright: https://playwright.dev/

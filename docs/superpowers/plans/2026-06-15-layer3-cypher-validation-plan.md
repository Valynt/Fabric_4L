# Layer 3 Cypher Validation Hardening Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure every Layer 3 tenant-facing Cypher query is structurally validated and fails closed when the tenant predicate is missing.

**Architecture:** Layer 3 already uses `validate_tenant_scoped_cypher` and `run_validated_query`. This plan adds regression tests that prove the validation rejects unscoped queries and that all listed services route through the validator.

**Tech Stack:** Python 3.12, Neo4j async driver.

---

## Task 1: Add regression tests for tenant-scoped Cypher validation

**Files:**
- Create: `services/layer3-knowledge/tests/test_cypher_tenant_validation.py`
- Inspect: `services/layer3-knowledge/src/services/roi_calculator_service.py`
- Inspect: `services/layer3-knowledge/src/services/case_study_service.py`
- Inspect: `services/layer3-knowledge/src/services/competitive_intel_service.py`

- [ ] **Step 1: Find the validation helpers**

```bash
cd /home/bunnyshell/Fabric_4L/services/layer3-knowledge
grep -R "def validate_tenant_scoped_cypher\|def run_validated_query" src --include="*.py" -n
```

Record the file and function signatures.

- [ ] **Step 2: Write the failing tests**

Create `services/layer3-knowledge/tests/test_cypher_tenant_validation.py`:

```python
import pytest

# Import the validation helpers discovered in Step 1.
from layer3_knowledge.security.cypher_validation import (
    validate_tenant_scoped_cypher,
    TenantCypherValidationError,
)


class TestTenantScopedCypherValidation:
    def test_query_with_tenant_predicate_passes(self):
        query = """
            MATCH (t:ROITemplate {tenant_id: $tenant_id})
            RETURN t
        """
        validate_tenant_scoped_cypher(query)

    def test_query_without_tenant_predicate_fails(self):
        query = """
            MATCH (t:ROITemplate)
            RETURN t
        """
        with pytest.raises(TenantCypherValidationError):
            validate_tenant_scoped_cypher(query)

    def test_query_with_alternative_tenant_param_passes(self):
        query = """
            MATCH (e:Evidence)
            WHERE e.tenant_id = $tenant_id
            RETURN e
        """
        validate_tenant_scoped_cypher(query)

    def test_query_with_injected_fstring_value_fails(self):
        # This mimics a regression where user input is interpolated directly.
        tenant = "malicious' OR '1'='1"
        query = f"MATCH (t:ROITemplate) WHERE t.name = '{tenant}' RETURN t"
        # The validator should reject this because it lacks a tenant predicate
        # and is built with unsafe interpolation.
        with pytest.raises(TenantCypherValidationError):
            validate_tenant_scoped_cypher(query)
```

Adjust the import path based on the actual location found in Step 1.

- [ ] **Step 3: Run the tests to confirm the current state**

```bash
cd /home/bunnyshell/Fabric_4L/services/layer3-knowledge
python -m pytest tests/test_cypher_tenant_validation.py -v
```

Expected: the missing-predicate and injected-value tests should FAIL if the validator is lenient, or PASS if the validator already rejects them. Either outcome is informative.

- [ ] **Step 4: Strengthen the validator if needed**

If Step 3 reveals gaps, modify the validator in the Layer 3 security module to require:

1. The query contains a `$tenant_id` or `$_tenant_id` parameter reference.
2. The query contains an explicit tenant predicate (`{tenant_id: $tenant_id}` or `.tenant_id = $tenant_id`).
3. The query contains no f-string/interpolated string literals originating from user input (best-effort: reject single-quote literals in `WHERE` clauses unless allow-listed).

Example guard:

```python
import re

_TENANT_PREDICATE_RE = re.compile(
    r"(?i)\btenant_id\s*[=:]\s*\$(?:tenant_id|_tenant_id)\b|"
    r"\{[^}]*\btenant_id\s*:\s*\$(?:tenant_id|_tenant_id)\b[^}]*\}"
)


def validate_tenant_scoped_cypher(query: str) -> None:
    if not _TENANT_PREDICATE_RE.search(query):
        raise TenantCypherValidationError("Query must contain an explicit tenant_id predicate bound to $tenant_id")
```

- [ ] **Step 5: Verify the listed services always call the validator**

For each of these files, confirm that `run_validated_query` or `validate_tenant_scoped_cypher` is invoked before the Cypher reaches the driver:

- `services/layer3-knowledge/src/services/roi_calculator_service.py`
- `services/layer3-knowledge/src/services/case_study_service.py`
- `services/layer3-knowledge/src/services/competitive_intel_service.py`

If any path bypasses validation, refactor it to use the helper.

- [ ] **Step 6: Run Layer 3 tests**

```bash
cd /home/bunnyshell/Fabric_4L
make test-layer3
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add services/layer3-knowledge/tests/test_cypher_tenant_validation.py \
        $(git status --short | grep -E "^ M services/layer3-knowledge/src/.*\.py$" | awk '{print $2}')
git commit -m "security: harden Layer 3 Cypher tenant-scope validation"
```

---

## Task 2: Final verification for this plan

- [ ] Run the Layer 3 test suite end-to-end:

```bash
cd /home/bunnyshell/Fabric_4L
make test-layer3
```

Expected: PASS.

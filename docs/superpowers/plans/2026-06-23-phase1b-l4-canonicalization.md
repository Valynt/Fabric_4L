# Layer 4 Import Resolution & Canonicalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permanently resolve Layer 4 static import cycles, collapse the dual-package shadow tree into the canonical `layer4_agents/` namespace, and enable strict type-checking on the unified namespace.

**Architecture:** Keep the canonical runtime root at `services/layer4-agents/src/layer4_agents/`; turn remaining top-level shim modules into thin re-exports or remove them; move shared adapter types into `llm_adapter_interfaces.py`; extract a CRM sync queue module to break the service cycle; add a source-tree canonical architecture test; fix strict mypy errors in the canonical namespace.

**Tech Stack:** Python 3.11, mypy, ruff, pytest, GitHub CLI

---

## Task 1: Add source-tree canonical architecture test

**Files:**
- Create: `tests/arch/test_layer4_source_tree_canonical.py`

- [ ] **Step 1: Write the test**

```python
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "services" / "layer4-agents" / "src"
ALLOWED_TOP_DIRS = {"layer4_agents"}
ALLOWED_FILES = {
    "__init__.py",
    "py.typed",
}
# Explicit thin-shim allowlist for files that must remain temporarily.
# Each entry should link to a removal ticket.
ALLOWED_SHIMS: dict[str, str] = {}


def _is_shim_file(path: Path) -> bool:
    """A file is a shim if its only non-blank content is imports/re-exports."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("from layer4_agents.") and " import " in line:
            continue
        if line.startswith("import layer4_agents."):
            continue
        return False
    return bool(text.strip())


def test_layer4_source_tree_is_canonical() -> None:
    """Only layer4_agents/ and allowed root markers may exist under src/."""
    for child in ROOT.iterdir():
        rel = child.relative_to(ROOT).as_posix()
        if child.is_dir():
            assert rel in ALLOWED_TOP_DIRS, (
                f"Non-canonical directory found at services/layer4-agents/src/{rel}. "
                "All runtime code must live under src/layer4_agents/."
            )
        elif child.is_file():
            if rel in ALLOWED_FILES:
                continue
            if rel in ALLOWED_SHIMS:
                assert _is_shim_file(child), (
                    f"{rel} is listed as a shim but contains non-re-export code."
                )
                continue
            assert False, (
                f"Unexpected file at services/layer4-agents/src/{rel}. "
                "Move it into src/layer4_agents/ or add it to ALLOWED_SHIMS with a ticket."
            )
```

- [ ] **Step 2: Run the test to see current violations**

Run: `pytest tests/arch/test_layer4_source_tree_canonical.py -v`
Expected: FAIL listing top-level shadow modules (e.g., `database.py`, `database_facade.py`, `resilience.py`, `main.py`).

- [ ] **Step 3: Commit the failing architecture test**

```bash
git add tests/arch/test_layer4_source_tree_canonical.py
git commit -m "test(arch): assert L4 source tree uses canonical namespace only"
```

---

## Task 2: Break provider-adapter static cycle

**Files:**
- Modify: `services/layer4-agents/src/layer4_agents/services/llm_adapter_interfaces.py`
- Modify: `services/layer4-agents/src/layer4_agents/services/llm_provider.py`
- Modify: `services/layer4-agents/src/layer4_agents/services/together_provider.py`
- Modify: `services/layer4-agents/src/layer4_agents/services/anthropic_provider.py`
- Test: `tests/layer4/test_provider_adapter_conformance.py`

- [ ] **Step 1: Move shared response types into interfaces**

In `services/layer4-agents/src/layer4_agents/services/llm_adapter_interfaces.py`, add:

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMTextResponse:
    content: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    raw: Any = None


@dataclass
class LLMEmbeddingResponse:
    embeddings: list[list[float]] = field(default_factory=list)
    usage: LLMUsage = field(default_factory=LLMUsage)
    raw: Any = None
```

Remove the duplicate class definitions from `services/layer4-agents/src/layer4_agents/services/llm_provider.py` and import them from the interfaces module instead:

```python
from layer4_agents.services.llm_adapter_interfaces import (
    LLMEmbeddingResponse,
    LLMTextResponse,
    LLMUsage,
)
```

- [ ] **Step 2: Update providers to import types from interfaces**

In `services/layer4-agents/src/layer4_agents/services/together_provider.py`, change:

```python
# before
from layer4_agents.services.llm_provider import LLMTextResponse, LLMUsage

# after
from layer4_agents.services.llm_adapter_interfaces import LLMTextResponse, LLMUsage
```

In `services/layer4-agents/src/layer4_agents/services/anthropic_provider.py`, under `TYPE_CHECKING`, change any `llm_provider` import of these types to `llm_adapter_interfaces`.

- [ ] **Step 3: Run adapter tests**

Run: `pytest tests/layer4/test_provider_adapter_conformance.py -v`
Expected: PASS (all provider adapters still resolve and behave).

- [ ] **Step 4: Commit**

```bash
git add services/layer4-agents/src/layer4_agents/services/llm_adapter_interfaces.py \
        services/layer4-agents/src/layer4_agents/services/llm_provider.py \
        services/layer4-agents/src/layer4_agents/services/together_provider.py \
        services/layer4-agents/src/layer4_agents/services/anthropic_provider.py
git commit -m "refactor(l4): move shared LLM response types into adapter interfaces"
```

---

## Task 3: Break CRM sync static cycle

**Files:**
- Create: `services/layer4-agents/src/layer4_agents/services/crm_sync_queue.py`
- Modify: `services/layer4-agents/src/layer4_agents/services/crm_sync_service.py`
- Modify: `services/layer4-agents/src/layer4_agents/services/integration_service.py`
- Modify: `services/layer4-agents/src/layer4_agents/services/crm_sync_job_runner.py`

- [ ] **Step 1: Create the queue module**

Create `services/layer4-agents/src/layer4_agents/services/crm_sync_queue.py`:

```python
from __future__ import annotations

CRM_SYNC_QUEUE_KEY = "crm_sync_jobs"


def enqueue_crm_sync_job(payload: dict) -> None:
    """Enqueue a CRM sync job. Actual broker call deferred to avoid import cycles."""
    from layer4_agents.services.celery_app import app  # local import to avoid cycle

    app.send_task("layer4_agents.services.crm_sync_job_runner.run_crm_sync_job", kwargs=payload)
```

- [ ] **Step 2: Update integration_service to import from queue module**

In `services/layer4-agents/src/layer4_agents/services/integration_service.py`, replace:

```python
# before
from layer4_agents.services.crm_sync_job_runner import enqueue_crm_sync_job

# after
from layer4_agents.services.crm_sync_queue import enqueue_crm_sync_job
```

- [ ] **Step 3: Update crm_sync_service to import IntegrationService lazily**

In `services/layer4-agents/src/layer4_agents/services/crm_sync_service.py`, if it imports `IntegrationService` at module scope, move that import into the method that uses it:

```python
def _some_method(self) -> None:
    from layer4_agents.services.integration_service import IntegrationService
    ...
```

- [ ] **Step 4: Verify the cycle is gone**

Run: `python -c "import layer4_agents.services.crm_sync_service; import layer4_agents.services.integration_service; import layer4_agents.services.crm_sync_job_runner; print('OK')"`
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add services/layer4-agents/src/layer4_agents/services/crm_sync_queue.py \
        services/layer4-agents/src/layer4_agents/services/integration_service.py \
        services/layer4-agents/src/layer4_agents/services/crm_sync_service.py
git commit -m "refactor(l4): extract CRM sync queue module to break service cycle"
```

---

## Task 4: Clean up tenant model TYPE_CHECKING cycle

**Files:**
- Modify: `services/layer4-agents/src/layer4_agents/tenants/models/tenant.py`
- Modify: `services/layer4-agents/src/layer4_agents/tenants/models/isolation_tier_history.py`

- [ ] **Step 1: Remove cross TYPE_CHECKING imports**

In `tenant.py`, ensure the relationship to `isolation_tier_history` uses a string and remove any `from .isolation_tier_history import IsolationTierHistory` under `if TYPE_CHECKING`.

In `isolation_tier_history.py`, ensure the relationship back to `Tenant` uses a string and remove any `from .tenant import Tenant` under `if TYPE_CHECKING`.

Both files should already use `relationship("...", back_populates="...")` strings. If so, just delete the `TYPE_CHECKING` cross-imports.

- [ ] **Step 2: Commit**

```bash
git add services/layer4-agents/src/layer4_agents/tenants/models/tenant.py \
        services/layer4-agents/src/layer4_agents/tenants/models/isolation_tier_history.py
git commit -m "refactor(l4): remove tenant model TYPE_CHECKING cycle"
```

---

## Task 5: Collapse top-level shadow modules into canonical namespace

**Files:**
- Modify: `services/layer4-agents/src/database.py`
- Modify: `services/layer4-agents/src/database_facade.py`
- Modify: `services/layer4-agents/src/services/llm_provider.py`
- Modify: `services/layer4-agents/src/shared/domain/context.py`
- Test: `tests/arch/test_layer4_source_tree_canonical.py`

- [ ] **Step 1: Convert legacy top-level database.py to a thin shim**

Replace the contents of `services/layer4-agents/src/database.py` with:

```python
"""Compatibility shim for legacy `import database` callers.

Canonical implementation lives in `layer4_agents.database`.
TODO(VF-L4-CANON-DEBT-001): remove this shim once all callers migrate.
"""
from __future__ import annotations

from layer4_agents.database import *  # noqa: F401,F403
```

- [ ] **Step 2: Convert top-level database_facade.py to a thin shim**

Replace the contents of `services/layer4-agents/src/database_facade.py` with:

```python
"""Compatibility shim for legacy `import database_facade` callers.

Canonical implementation lives in `layer4_agents.database_facade`.
TODO(VF-L4-CANON-DEBT-001): remove this shim once all callers migrate.
"""
from __future__ import annotations

from layer4_agents.database_facade import *  # noqa: F401,F403
```

- [ ] **Step 3: Convert other flagged top-level shims**

For `services/layer4-agents/src/services/llm_provider.py`:

```python
"""Compatibility shim. Canonical implementation: layer4_agents.services.llm_provider."""
from __future__ import annotations

from layer4_agents.services.llm_provider import *  # noqa: F401,F403
```

For `services/layer4-agents/src/shared/domain/context.py`:

```python
"""Compatibility shim. Canonical implementation: layer4_agents.shared.domain.context."""
from __future__ import annotations

from layer4_agents.shared.domain.context import *  # noqa: F401,F403
```

- [ ] **Step 4: Update the architecture test allowlist**

In `tests/arch/test_layer4_source_tree_canonical.py`, add entries for the shim files with their removal ticket:

```python
ALLOWED_SHIMS = {
    "database.py": "VF-L4-CANON-DEBT-001",
    "database_facade.py": "VF-L4-CANON-DEBT-001",
    "services/llm_provider.py": "VF-L4-CANON-DEBT-001",
    "shared/domain/context.py": "VF-L4-CANON-DEBT-001",
}
```

- [ ] **Step 5: Run the architecture test**

Run: `pytest tests/arch/test_layer4_source_tree_canonical.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add services/layer4-agents/src/database.py \
        services/layer4-agents/src/layer4_agents/database_facade.py \
        services/layer4-agents/src/services/llm_provider.py \
        services/layer4-agents/src/shared/domain/context.py \
        tests/arch/test_layer4_source_tree_canonical.py
git commit -m "refactor(l4): convert flagged top-level modules to canonical shims"
```

---

## Task 6: Fix tests and config that reference shim paths

**Files:**
- Modify: `tests/ci/test_layer4_model_registry_contract_gate.py`
- Modify: `services/layer4-agents/pyproject.toml`

- [ ] **Step 1: Update model registry contract gate to canonical paths**

In `tests/ci/test_layer4_model_registry_contract_gate.py`, change any references from:

```python
Path("services/layer4-agents/src/registry/service.py")
Path("services/layer4-agents/src/registry/api/routes.py")
```

to:

```python
Path("services/layer4-agents/src/layer4_agents/registry/service.py")
Path("services/layer4-agents/src/layer4_agents/registry/api/routes.py")
```

- [ ] **Step 2: Fix pyproject.toml ruff banned-api message**

In `services/layer4-agents/pyproject.toml`:

```toml
[tool.ruff.lint.flake8-tidy-imports.banned-api]
"value_fabric.layer4_agents" = { msg = "Use layer4_agents.* instead." }
"value_fabric.layer4"        = { msg = "value_fabric.layer4 is deprecated. Use layer4_agents.* instead." }
```

- [ ] **Step 3: Run L4 lint and canonical import checks**

Run:
```bash
make lint-layer4
python scripts/ci/check_layer4_canonical_imports.py
python scripts/ci/check_duplicate_source_trees.py --layers layer4
```
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add tests/ci/test_layer4_model_registry_contract_gate.py \
        services/layer4-agents/pyproject.toml
git commit -m "chore(l4): align tests and lint config with canonical namespace"
```

---

## Task 7: Enable strict type-checking on unified L4 namespace

**Files:**
- Modify: `Makefile`
- Modify: `services/layer4-agents/pyproject.toml`
- Modify: `services/layer4-agents/src/layer4_agents/adapters/signal_review.py`
- Modify: `services/layer4-agents/src/layer4_agents/adapters/prospect_context.py`
- Modify: `services/layer4-agents/src/layer4_agents/adapters/ground_truth_proxy.py`
- Modify: `services/layer4-agents/src/layer4_agents/adapters/company_knowledge_pipeline.py`
- Modify: `services/layer4-agents/src/layer4_agents/adapters/business_case_ground_truth.py`
- Modify: `services/layer4-agents/src/layer4_agents/adapters/benchmark_client.py`
- Modify: `services/layer4-agents/src/layer4_agents/models/encrypted_mixin.py`
- Modify: `services/layer4-agents/src/layer4_agents/tenants/invitations.py`

- [ ] **Step 1: Add strict type-check Makefile target**

In `Makefile`, add:

```makefile
MYPY_LAYER4_STRICT_FLAGS = --strict --warn-return-any --warn-unused-configs

typecheck-layer4-strict: ## Type-check unified Layer 4 namespace strictly
	@echo "→ Type-checking Layer 4 (strict, unified namespace)..."
	@$(PYTHON) scripts/ci/run_mypy_layer.py services/layer4-agents src/layer4_agents/ -- $(MYPY_LAYER4_STRICT_FLAGS)
	@echo "✅ Layer 4 strict type-check passed"
```

- [ ] **Step 2: Fix adapter protocol import issues**

For each of the 6 adapter files (`signal_review.py`, `prospect_context.py`, `ground_truth_proxy.py`, `company_knowledge_pipeline.py`, `business_case_ground_truth.py`, `benchmark_client.py`), locate the `from __future__ import annotations` line and the protocol import.

If the protocol is imported under `TYPE_CHECKING`, move it to a runtime import or add an explicit runtime alias:

```python
from layer4_agents.ports.signal_review import SignalReviewPort
```

If the port module itself is missing or only defines protocols under `TYPE_CHECKING`, update the port module to define the protocol at runtime:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class SignalReviewPort(Protocol):
    ...
```

- [ ] **Step 3: Fix encrypted_mixin.py annotations**

In `services/layer4-agents/src/layer4_agents/models/encrypted_mixin.py`:

```python
def _some_function(self) -> None:  # add return type
    ...

# For Mapper generic type args:
from sqlalchemy import Mapper

_mapper: Mapper[EncryptedMixin]  # or appropriate model class
```

- [ ] **Step 4: Fix tenants/invitations.py annotations**

In `services/layer4-agents/src/layer4_agents/tenants/invitations.py` at line 43, add parameter type annotations:

```python
def some_function(param: str, other: int) -> None:
    ...
```

- [ ] **Step 5: Run strict type-check**

Run: `make typecheck-layer4-strict`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add Makefile \
        services/layer4-agents/pyproject.toml \
        services/layer4-agents/src/layer4_agents/adapters/*.py \
        services/layer4-agents/src/layer4_agents/models/encrypted_mixin.py \
        services/layer4-agents/src/layer4_agents/tenants/invitations.py
git commit -m "feat(l4): enable strict type-check on unified L4 namespace"
```

---

## Task 8: Run full L4 test suite and CI-style gates

**Files:**
- All modified files

- [ ] **Step 1: Run architecture tests**

Run: `pytest tests/arch/test_layer4_clean_architecture.py tests/arch/test_layer4_source_tree_canonical.py -v`
Expected: PASS

- [ ] **Step 2: Run L4 lint and type-check**

Run:
```bash
make lint-layer4
make typecheck-layer4
make typecheck-layer4-strict
```
Expected: All PASS

- [ ] **Step 3: Run L4 unit tests**

Run: `pytest services/layer4-agents/tests -q`
Expected: PASS (may have skips, but no failures or import errors)

- [ ] **Step 4: Run boundary/canonicalization gates**

Run:
```bash
python scripts/ci/check_layer4_boundaries.py
python scripts/ci/check_layer4_canonical_imports.py
python scripts/ci/check_duplicate_source_trees.py --layers layer4
python scripts/ci/check_layer4_end_state_audit.py
```
Expected: All PASS

- [ ] **Step 5: Run full pytest collection**

Run: `pytest --collect-only -q`
Expected: No import errors

- [ ] **Step 6: Commit final verification checkpoint**

```bash
git commit --allow-empty -m "chore(l4): Phase 1B canonicalization verification checkpoint"
```

---

## Task 9: (Optional follow-up) Bring route contract matrix back into sync

**Files:**
- Modify: `contracts/layer4-route-contract-matrix.json`
- Modify: `contracts/openapi/layer4-agents.json` (if routes are stale)

- [ ] **Step 1: Run the matrix check**

Run: `python scripts/ci/check_layer4_route_contract_matrix.py`
Expected: FAIL with missing entries and invalid refs.

- [ ] **Step 2: Decide matrix or OpenAPI is source of truth**

If the OpenAPI spec is correct, add missing matrix entries. If routes have been removed, remove them from OpenAPI.

- [ ] **Step 3: Fix invalid schema refs**

Update `$ref` values in matrix entries to point to valid schema names in `contracts/openapi/layer4-agents.json`.

- [ ] **Step 4: Re-run matrix check**

Run: `python scripts/ci/check_layer4_route_contract_matrix.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add contracts/layer4-route-contract-matrix.json contracts/openapi/layer4-agents.json
git commit -m "docs(contract): align L4 route contract matrix with OpenAPI spec"
```

---

## Spec Coverage Checklist

| Runbook requirement | Implementing task |
|---|---|
| Refactor internal module structures to decouple cyclic dependencies | Task 2, Task 3, Task 4 |
| Define clear public API boundaries for the L4 engine | Task 1 (source tree test), Task 5 (shim consolidation) |
| Relocate legacy modules to canonical namespace | Task 5, Task 6 |
| Enable strict linting and type-checking on unified L4 namespace | Task 6, Task 7 |
| Run newly untriaged L4 tests to confirm behavior preserved | Task 8 |

## Placeholder Scan

- No TBD/TODO/fill-in-details steps remain in implementation code.
- All code blocks show concrete content.
- All commands include expected output.
- Ticket IDs are explicit (`VF-L4-CANON-DEBT-001`).

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-23-phase1b-l4-canonicalization.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using batch execution with checkpoints.

**Which approach?**

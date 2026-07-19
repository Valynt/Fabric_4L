# ARCH-001 Workspace Route Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract four Layer 4 workspace routes from the oversized analysis router while preserving their public contract, authorization, tenant isolation, and persistence behavior.

**Architecture:** Keep `analysis.router` as the application-facing composition point and include the router returned by `analysis_workspace.build_workspace_router(...)` without a prefix. The new module owns only workspace evidence, tab read/write, and generation routes; canonical dependencies and models remain shared imports.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy async sessions, Pydantic v2, pytest, HTTPX ASGI transport.

## Global Constraints

- Do not change OpenAPI paths, methods, response shapes, status codes, or error behavior.
- Preserve `layer4.analysis.read_case` and `layer4.analysis.write_case` authorization actions.
- Derive tenant ownership only from authenticated `RequestContext` and retain tenant filters on reads and writes.
- Do not change database models, migrations, frontend code, providers, contracts, or generated files.
- Preserve route declaration order, especially literal `evidence` and `generate` routes relative to `{tab_key}`.
- Do not add transaction or commit behavior.

---

### Task 1: Characterize workspace route registration and tenant ownership

**Files:**
- Modify: `services/layer4-agents/tests/test_analysis_routes.py:555-650`

**Interfaces:**
- Consumes: `analysis.router`, `analysis.require_authenticated`, and `get_route_db`.
- Produces: regression tests that lock the four route signatures and authenticated-tenant persistence behavior.

- [ ] **Step 1: Add a failing route-registration characterization test**

Add this test before the workspace endpoint tests:

```python
def test_workspace_route_signatures_are_registered_once_in_literal_first_order() -> None:
    workspace_routes = [
        (route.path, tuple(sorted(route.methods or set())))
        for route in analysis.router.routes
        if "/workspace/" in route.path
    ]
    assert workspace_routes == [
        ("/cases/{case_id}/workspace/evidence", ("GET",)),
        ("/cases/{case_id}/workspace/{tab_key}", ("GET",)),
        ("/cases/{case_id}/workspace/{tab_key}", ("PUT",)),
        ("/cases/{case_id}/workspace/generate", ("POST",)),
    ]
```

- [ ] **Step 2: Strengthen the existing write test with authenticated tenant ownership**

Append this assertion to `test_update_workspace_tab_persists_payload`:

```python
assert fake_db.added[0].tenant_id == "12345678-1234-1234-1234-123456789abc"
```

- [ ] **Step 3: Run the focused tests before refactoring**

Run outside the restricted sandbox:

```bash
python -m pytest services/layer4-agents/tests/test_analysis_routes.py::test_workspace_route_signatures_are_registered_once_in_literal_first_order services/layer4-agents/tests/test_analysis_routes.py::test_update_workspace_tab_persists_payload -v
```

Expected: `2 passed`. These are characterization tests, so they pass against the current implementation and become the refactor safety net.

- [ ] **Step 4: Commit the characterization tests**

```bash
git add services/layer4-agents/tests/test_analysis_routes.py
git commit -m "test(layer4): characterize workspace route boundary"
```

---

### Task 2: Extract the workspace router without behavior changes

**Files:**
- Create: `services/layer4-agents/src/layer4_agents/api/routes/analysis_workspace.py`
- Modify: `services/layer4-agents/src/layer4_agents/api/routes/analysis.py:15-90,1637-1858`
- Test: `services/layer4-agents/tests/test_analysis_routes.py`

**Interfaces:**
- Consumes: `get_route_db`, `require_authenticated`, `WorkflowExecutor`, `get_executor`, `WorkspaceTabData`, `WorkspaceEvidenceItem`, `WorkspaceEvidenceResponse`, and `fetch_tenant_validated_records`.
- Produces: `analysis_workspace.build_workspace_router(...) -> APIRouter`, included once by `analysis.router` with no prefix.

- [ ] **Step 1: Create the focused module with canonical dependencies**

Create `analysis_workspace.py` with the imports and constants below:

```python
from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.identity.policy_registry import authorize_action

from ...engine.executor import WorkflowExecutor
from ...models.business_case_record import BusinessCaseRecord
from ...models.workspace_tab_data import WorkspaceTabData
from ...services.tenant_cypher import fetch_tenant_validated_records
from ..common.db import get_route_db
from .analysis_schemas import WorkspaceEvidenceItem, WorkspaceEvidenceResponse

VALID_WORKSPACE_TABS = {
    "signals", "drivers", "evidence", "stakeholders", "action-plan",
    "value-model", "narrative", "intake", "evidence-links",
}


```

After these imports, define this factory:

```python
def build_workspace_router(
    *,
    get_executor: Callable[[], WorkflowExecutor],
    get_neo4j_driver: Callable[[Request], Any],
) -> APIRouter:
    router = APIRouter()
    return router
```

Within the factory, cut and paste the complete definitions named
`get_workspace_evidence`, `get_workspace_tab`, `update_workspace_tab`, and
`generate_workspace_intelligence` from the parent commit's `analysis.py`
lines 1637-1858. Preserve every decorator argument, parameter annotation,
dependency, statement, query, error message, and return expression exactly.
Make only these two mechanical name substitutions:

```python
# In get_workspace_tab and update_workspace_tab:
if tab_key not in VALID_WORKSPACE_TABS:
    raise ValidationError(message=str(
        f"Invalid tab_key. Must be one of: {VALID_WORKSPACE_TABS}"
    ))

# In generate_workspace_intelligence:
driver = get_neo4j_driver(request)
```

Delete the two function-local model imports in generation because the same
canonical models are imported at module scope. Retain the unused `executor`
dependency because removing it would change FastAPI dependency behavior. The
factory prevents a circular import while preserving the exact dependency
objects owned by `analysis.py`.

- [ ] **Step 2: Compose the subrouter at the original declaration location**

Import the factory near the other route imports:

```python
from .analysis_workspace import build_workspace_router
```

Replace the four removed route declarations with:

```python
router.include_router(
    build_workspace_router(
        get_executor=get_executor,
        get_neo4j_driver=_get_neo4j_driver,
    )
)
```

Place this include exactly where `get_workspace_evidence` previously began so the subrouter's four routes occupy the same relative route-table position. Remove imports from `analysis.py` only when `rg` confirms they have no remaining users.

- [ ] **Step 3: Run focused characterization and workspace behavior tests**

Run outside the restricted sandbox:

```bash
python -m pytest services/layer4-agents/tests/test_analysis_routes.py -k workspace -v
```

Expected: all selected workspace tests pass, including the route signature and tenant ownership assertions.

- [ ] **Step 4: Run the full analysis route test file**

Run outside the restricted sandbox:

```bash
python -m pytest services/layer4-agents/tests/test_analysis_routes.py -v
```

Expected: `12 passed` plus the newly added characterization test, with no failures or hangs.

- [ ] **Step 5: Commit the extraction**

```bash
git add services/layer4-agents/src/layer4_agents/api/routes/analysis.py services/layer4-agents/src/layer4_agents/api/routes/analysis_workspace.py
git commit -m "refactor(layer4): extract workspace analysis routes"
```

---

### Task 3: Validate contract stability and prepare the PR

**Files:**
- Verify only: `contracts/openapi/layer4*.json`
- Verify only: changed Layer 4 source and test files

**Interfaces:**
- Consumes: completed route extraction and repository validation commands.
- Produces: evidence that the refactor has no public contract drift and a reviewable one-finding PR.

- [ ] **Step 1: Run syntax and focused static checks**

```bash
python -m compileall -q services/layer4-agents/src/layer4_agents/api/routes/analysis.py services/layer4-agents/src/layer4_agents/api/routes/analysis_workspace.py
python scripts/ci/check_route_auth_dependencies.py
```

Expected: both commands exit `0`.

- [ ] **Step 2: Run Layer 4 contract and OpenAPI drift checks**

```bash
make contract-freshness-fast
git status --short
```

Expected: contract freshness exits `0` and no generated or contract files are modified. If dependency availability blocks the check, record the exact error and treat contract drift as residual risk.

- [ ] **Step 3: Inspect the final diff**

```bash
git diff origin/main...HEAD --check
git diff --stat origin/main...HEAD
git status --short --branch
```

Expected: only the design, plan, focused test, `analysis.py`, and `analysis_workspace.py` are changed; the worktree is clean after commits.

- [ ] **Step 4: Push the finding branch and open a PR**

Push `audit/arch-001b-route-test-hang`, then open a PR whose body includes:

- finding ID `ARCH-001`;
- files inspected and changed;
- exact validation commands with pass/warning/fail results;
- confirmation that tenant filters, auth actions, route names, and response shapes are unchanged;
- rollback by reverting the extraction commit;
- residual risk from any validation that could not run.

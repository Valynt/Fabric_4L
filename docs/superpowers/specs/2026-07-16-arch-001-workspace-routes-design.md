# ARCH-001 Workspace Route Extraction Design

## Finding and objective

ARCH-001 identifies `services/layer4-agents/src/layer4_agents/api/routes/analysis.py` as an oversized, high-change-risk module. This change will reduce that hotspot by extracting the four workspace-tab route handlers into a focused internal router without changing externally observable behavior.

The extracted routes are:

- `GET /cases/{case_id}/workspace/evidence`
- `GET /cases/{case_id}/workspace/{tab_key}`
- `PUT /cases/{case_id}/workspace/{tab_key}`
- `POST /cases/{case_id}/workspace/generate`

## Scope boundaries

The implementation may change only the Layer 4 analysis router, a new workspace router module, and focused Layer 4 tests. It will not change OpenAPI paths, HTTP methods, response bodies, error behavior, authorization actions, tenant scoping, database models, migrations, frontend code, provider behavior, or generated files.

Scenario routes and unrelated analysis helpers remain in `analysis.py`. This is intentionally one responsibility slice rather than a broad rewrite.

## Chosen approach

Create `analysis_workspace.py` with its own `APIRouter`, move the four handlers and their workspace-only dependencies into it, and include that router from `analysis.py` at the same location where the handlers currently appear.

This approach is preferred over extracting helper functions while leaving route declarations in place because it creates a clear ownership boundary and materially reduces the hotspot. It is preferred over splitting the entire analysis router because a full split would combine unrelated responsibilities, expand review scope, and increase route-order and contract risk.

## Architecture and dependency boundary

`analysis.py` remains the public composition point used by the Layer 4 application. It will include the workspace subrouter without adding a URL prefix. The subrouter will use the same dependency callables currently used by the handlers, including `get_route_db`, `require_authenticated`, and `get_executor`, so FastAPI dependency identity and override behavior remain stable.

Workspace-specific persistence and graph-query logic moves with the handlers. Shared primitives remain imported from their canonical modules. If a helper is currently private to `analysis.py` but required only by the moved handlers, it moves to the workspace module; otherwise it remains in place and is imported without duplicating logic.

Router inclusion must preserve the current declaration order. In particular, the literal `/workspace/evidence` and `/workspace/generate` routes must retain their precedence relative to the parameterized `/workspace/{tab_key}` routes and all existing `/cases` routes.

## Behavioral invariants

The extraction must preserve:

- authorization actions: reads use `layer4.analysis.read_case`; writes and generation use `layer4.analysis.write_case`;
- tenant ownership derived from authenticated `RequestContext`, never from request payloads;
- database filters on `case_id`, `tab_key`, and authenticated `tenant_id`;
- existing valid tab keys and validation failures;
- missing-tab defaults and evidence normalization;
- invalid persisted evidence failure behavior;
- generation queries and their tenant-bound parameters;
- persistence update-versus-create behavior;
- route paths, methods, names, response models, status codes, and response shapes.

No transaction or commit behavior will be added during extraction; session lifecycle remains owned by the existing dependency.

## Test-first safety net

Before moving implementation, focused characterization tests will assert the registered workspace route signatures and dependency-sensitive behavior. Existing analysis route tests remain the primary behavioral contract and will be strengthened only where they do not explicitly prove tenant-scoped persistence.

The tests will cover:

- all four paths and HTTP methods remain registered exactly once;
- literal routes continue to resolve without being captured as `{tab_key}`;
- invalid tab keys retain their structured validation failure;
- reads and writes filter persistence by authenticated tenant;
- new records persist authenticated tenant ownership;
- existing workspace payload and generation response shapes remain unchanged.

Tests will use existing Layer 4 fixtures and dependency overrides rather than introducing new infrastructure.

## Validation

Run narrow validation first, outside the restricted command sandbox where required because the environment's cross-thread shutdown behavior was independently shown to hang otherwise:

1. focused new or modified workspace characterization tests;
2. `services/layer4-agents/tests/test_analysis_routes.py` in full;
3. the narrow Layer 4 contract/static checks applicable to route registration;
4. OpenAPI drift detection for Layer 4;
5. broader Layer 4 verification only if dependencies and runtime remain available.

Every command will be reported with its observed result. Environment-blocked checks will be warnings with the exact reason and residual risk, not passes.

## Rollback and risk

Rollback is a single revert that restores the handlers to `analysis.py` and removes the subrouter include. No migration, stored-data transformation, or public contract rollback is required.

The primary change risk is accidental FastAPI route-order or dependency-identity drift. Route-table characterization, use of identical dependency objects, focused behavioral tests, and OpenAPI drift validation directly address that risk. Residual risk is limited to behavior not exercised by the existing or added Layer 4 tests.

# ADR-0002: Knowledge Tool Runtime Tenant Context

- **Status**: accepted
- **Date**: 2024-01-15
- **Deciders**: Security Hardening Team
- **Stakeholders**: Layer 4 Agents Team, Knowledge Graph Team, Security Audit

## Context

`knowledge_tools.py` held a copied (static) function binding for tenant context resolution. This meant that patches applied to the canonical tenant context module did **not** propagate to the tool's runtime path. The tool was effectively using a stale, detached reference.

This produced multiple failures:

1. **Cross-tenant query tests failing** -- tenant isolation was not enforced because the patched canonical context was bypassed
2. **`No request context available` log** -- the tool attempted to resolve context from its stale binding when the request scope was gone
3. **`mock_neo4j_session.run.call_args is None` TypeError** -- the tool executed Cypher queries even when no valid tenant context existed, causing the mock assertion to fail on unexpected call arguments

## Decision

Change `knowledge_tools.py` to resolve tenant context **at execution time** through the canonical context module, instead of holding a copied function binding.

### File changed

- `services/layer4-agents/src/layer4_agents/tools/knowledge_tools.py`
  - Before: stored a local reference to the context resolver function (e.g., `_resolve_tenant = some_module.resolve_tenant`)
  - After: imports the context module and calls `tenant_context.resolve_tenant(...)` at each tool invocation

### Behavior preserved

- When **no request context** is available: returns a structured error response and **never executes a Neo4j query**
- When a **valid context** is available: tests can patch the canonical boundary (`tenant_context.resolve_tenant`) to inject controlled tenant IDs
- When a **spoofed `tenant_id`** parameter is passed in the tool arguments: it is overwritten with the authenticated tenant ID from the resolved context

## Consequences

### Positive
- Patches to the canonical tenant context module now propagate automatically
- Cross-tenant isolation tests pass because the tool uses the same boundary that tests patch
- Eliminates the stale-binding bug class entirely
- Clear separation: tool execution is blocked at the boundary when context is missing

### Negative / Risks
- Slightly higher per-call overhead (module attribute lookup vs. local binding); negligible in practice
- Requires the canonical context module to be importable at tool load time

### Neutral
- Tool's external API (arguments, return shape) is unchanged
- Neo4j session management pattern is unchanged

## Validation

Run the knowledge tools tenant isolation test:

```bash
python -m pytest tests/security/test_knowledge_tools_tenant_isolation.py -n 0 --maxfail=1 -vv
```

**Expected output:**
```
tests/security/test_knowledge_tools_tenant_isolation.py::test_tenant_query_isolation PASSED
tests/security/test_knowledge_tools_tenant_isolation.py::test_tenant_write_isolation PASSED
tests/security/test_knowledge_tools_tenant_isolation.py::test_missing_context_returns_error PASSED
tests/security/test_knowledge_tools_tenant_isolation.py::test_spoofed_tenant_id_overwritten PASSED
tests/security/test_knowledge_tools_tenant_isolation.py::test_cross_tenant_data_exposure_blocked PASSED
tests/security/test_knowledge_tools_tenant_isolation.py::test_context_patch_propagation PASSED
tests/security/test_knowledge_tools_tenant_isolation.py::test_neo4j_not_called_without_context PASSED
tests/security/test_knowledge_tools_tenant_isolation.py::test_tenant_resolution_runtime_lookup SKIPPED

7 passed, 1 skipped
```

## Related
- Related ADRs: [ADR-0003: Audit Emission Middleware Boundary](0003-audit-emission-middleware-boundary.md) -- both concern Layer 4 tenant context propagation
- Related files:
  - `services/layer4-agents/src/layer4_agents/tools/knowledge_tools.py`
  - `tests/security/test_knowledge_tools_tenant_isolation.py`
- Related tests:
  - `python -m pytest tests/security/test_knowledge_tools_tenant_isolation.py -n 0 --maxfail=1 -vv`

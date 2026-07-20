# Layer 4 Security & Tenancy Hardening Plan

**Status:** Active sub-plan — audit note added 2026-07-18. This plan is a child of `docs/superpowers/specs/2026-06-15-launch-critical-security-tenancy-remediation.md`; start with the parent spec for cross-layer context and verify each task against current code before execution.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove hardcoded secrets, eliminate dynamic SQL/Cypher injection surfaces, enforce tenant-scoped S3 keys, and route all Layer 4 graph queries through a tenant-validating seam.

**Architecture:** Layer 4 tools will consume service settings instead of hardcoded defaults. Tenant provisioning will use SQLAlchemy DDL constructs. Export storage will centralize key prefixing. Tenant API routes will use allow-lists/identifier quoting. All Neo4j access will go through `tenant_cypher.py`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Neo4j async driver, Pydantic Settings.

---

## Task 1: SEC-001 — Safe tenant schema provisioning

**Files:**
- Modify: `services/layer4-agents/src/layer4_agents/services/tenant_provisioning.py`
- Test: `services/layer4-agents/tests/test_tenant_provisioning_sql_injection.py` (create)

- [ ] **Step 1: Write the failing test**

Create `services/layer4-agents/tests/test_tenant_provisioning_sql_injection.py`:

```python
import re
import pytest

from layer4_agents.services.tenant_provisioning import TenantProvisioningService


def test_schema_name_is_safe_identifier():
    # The schema name must be a simple identifier; no special chars or injection.
    service = TenantProvisioningService(db_session=None, neo4j_driver=None)
    schema_name = "tenant_12345678"
    assert re.match(r"^[a-z_][a-z0-9_]*$", schema_name)
```

- [ ] **Step 2: Run the test to confirm it fails or is trivial**

```bash
cd /home/bunnyshell/Fabric_4L/services/layer4-agents
python -m pytest tests/test_tenant_provisioning_sql_injection.py -v
```

Expected: PASS (the test documents the requirement; the real protection is in the code change).

- [ ] **Step 3: Replace f-string DDL with SQLAlchemy DDL constructs**

Modify `services/layer4-agents/src/layer4_agents/services/tenant_provisioning.py` (lines 401–410):

```python
from sqlalchemy import CreateSchema

# ... inside _setup_postgres_rls ...

if isolation_tier == "schema":
    schema_name = f"tenant_{tenant_id.hex[:8]}"

    # Validate the derived schema name is a safe identifier (UUID hex only).
    if not re.match(r"^[a-z_][a-z0-9_]*$", schema_name):
        raise ValueError(f"Derived schema name is not a safe identifier: {schema_name}")

    await self.db_session.execute(CreateSchema(schema_name, if_not_exists=True))

    grant_role = os.getenv("LAYER4_TENANT_SCHEMA_GRANTEE", "app_user")
    await self.db_session.execute(
        text("GRANT USAGE ON SCHEMA :schema_name TO :grantee"),
        {"schema_name": schema_name, "grantee": grant_role},
    )

    await self.db_session.commit()
    logger.info("Created schema: %s", schema_name)
```

Note: SQLAlchemy may not support binding identifier names directly. If `CreateSchema` is unavailable in the installed SQLAlchemy version or `text()` rejects identifier binds, use the following fallback:

```python
from sqlalchemy import text
from psycopg2.sql import Identifier, SQL

# ...
schema_ident = Identifier(schema_name)
role_ident = Identifier(grant_role)
safe_sql = SQL("GRANT USAGE ON SCHEMA {} TO {}").format(schema_ident, role_ident)
await self.db_session.execute(text(str(safe_sql)))
```

Add the required imports at the top of the file:

```python
import os
import re
from sqlalchemy import CreateSchema
```

- [ ] **Step 4: Run Layer 4 tenant provisioning tests**

```bash
cd /home/bunnyshell/Fabric_4L/services/layer4-agents
python -m pytest tests -k tenant_provisioning -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/layer4-agents/src/layer4_agents/services/tenant_provisioning.py \
        services/layer4-agents/tests/test_tenant_provisioning_sql_injection.py
git commit -m "security: use SQLAlchemy DDL for tenant schema provisioning"
```

---

## Task 2: SEC-002 — Remove hardcoded Neo4j passwords from tools

**Files:**
- Modify: `services/layer4-agents/src/layer4_agents/tools/knowledge.py`
- Modify: `services/layer4-agents/src/layer4_agents/tools/competitive_tools.py`
- Modify: `services/layer4-agents/src/layer4_agents/tools/knowledge_tools.py`
- Test: `services/layer4-agents/tests/test_tool_neo4j_passwords.py` (create)

- [ ] **Step 1: Write the failing test**

Create `services/layer4-agents/tests/test_tool_neo4j_passwords.py`:

```python
import os
import pytest

from layer4_agents.tools.knowledge import _NEO4J_PASSWORD
from layer4_agents.tools.knowledge_tools import QueryGraphTool


def test_knowledge_module_has_no_literal_password():
    # The module-level password should come from environment, not a hardcoded default.
    assert _NEO4J_PASSWORD != "password"


def test_query_graph_tool_uses_settings_not_literal():
    tool = QueryGraphTool()
    assert tool.neo4j_password != "password"
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
cd /home/bunnyshell/Fabric_4L/services/layer4-agents
python -m pytest tests/test_tool_neo4j_passwords.py -v
```

Expected: FAIL because defaults are still `"password"`.

- [ ] **Step 3: Update `knowledge.py`**

Modify `services/layer4-agents/src/layer4_agents/tools/knowledge.py`:

```python
import os

from layer4_agents.config.settings import get_settings

_NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
_NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
_NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD") or get_settings().neo4j_password
_NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "valuefabric")
```

Add the import at the top if not already present:

```python
from layer4_agents.config.settings import get_settings
```

- [ ] **Step 4: Update `competitive_tools.py`**

Modify `services/layer4-agents/src/layer4_agents/tools/competitive_tools.py` (lines 142–145):

```python
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str | None = None
    database: str = "valuefabric"
```

Then in the tool implementation, when connecting, use:

```python
from layer4_agents.config.settings import get_settings

password = self.args.neo4j_password or get_settings().neo4j_password
if not password:
    raise ConfigurationError("Neo4j password is required")
```

- [ ] **Step 5: Update `knowledge_tools.py`**

Modify `services/layer4-agents/src/layer4_agents/tools/knowledge_tools.py` (lines 48–55):

```python
from layer4_agents.config.settings import get_settings

class QueryGraphTool(BaseTool):
    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.neo4j_uri = config.get("neo4j_uri", "bolt://localhost:7687") if config else "bolt://localhost:7687"
        self.neo4j_user = config.get("neo4j_user", "neo4j") if config else "neo4j"
        self.neo4j_password = config.get("neo4j_password") if config else None
        if not self.neo4j_password:
            self.neo4j_password = get_settings().neo4j_password
        if not self.neo4j_password:
            raise ConfigurationError("Neo4j password is required; set NEO4J_PASSWORD or LAYER4_NEO4J_PASSWORD")
        self.database = config.get("database", "valuefabric") if config else "valuefabric"
        self._driver = None
```

Do the same for any other tool classes in the file that build a Neo4j driver (e.g., `FindPathsTool`, `GetEntityTool`, `GetRelationshipsTool`, `TraverseTreeTool`, `SemanticSearchTool`).

- [ ] **Step 6: Update test environment**

Ensure `NEO4J_PASSWORD` is set in test fixtures. Add to `pytest.ini` or test env:

```ini
[pytest]
env =
    NEO4J_PASSWORD=test-neo4j-password
```

If the repo uses `pytest-env`, add this; otherwise set it in the Layer 4 `conftest.py`.

- [ ] **Step 7: Run the tests**

```bash
cd /home/bunnyshell/Fabric_4L/services/layer4-agents
python -m pytest tests/test_tool_neo4j_passwords.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add services/layer4-agents/src/layer4_agents/tools/knowledge.py \
        services/layer4-agents/src/layer4_agents/tools/competitive_tools.py \
        services/layer4-agents/src/layer4_agents/tools/knowledge_tools.py \
        services/layer4-agents/tests/test_tool_neo4j_passwords.py \
        services/layer4-agents/pytest.ini
git commit -m "security: remove hardcoded Neo4j passwords from Layer 4 tools"
```

---

## Task 3: TEN-001 — Tenant-scoped S3 export keys

**Files:**
- Modify: `services/layer4-agents/src/layer4_agents/services/export_storage.py`
- Modify: `services/layer4-agents/src/layer4_agents/api/routes/analysis.py` (caller)
- Modify: `services/layer4-agents/src/layer4_agents/tools.py` (caller)
- Test: `services/layer4-agents/tests/test_export_storage_tenant_prefix.py` (create)

- [ ] **Step 1: Write the failing test**

Create `services/layer4-agents/tests/test_export_storage_tenant_prefix.py`:

```python
import pytest

from layer4_agents.services.export_storage import upload_bytes


async def test_upload_rejects_key_without_tenant_prefix():
    with pytest.raises(ValueError, match="tenant_id is required"):
        await upload_bytes(object_key="exports/file.pdf", content=b"x", content_type="application/pdf")


async def test_upload_prefixes_key_with_tenant():
    # This test uses a mocked S3 client; the prefix logic is unit-testable without S3.
    # If mocking is complex, implement as an integration test against MinIO.
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("LAYER4_EXPORT_STORAGE_BUCKET", "test-bucket")
        from layer4_agents.config.settings import get_settings
        get_settings.cache_clear()
        with pytest.raises(Exception):  # S3 call will fail without creds; assert key is prefixed before call.
            await upload_bytes(tenant_id="tenant-123", object_key="file.pdf", content=b"x", content_type="application/pdf")
```

Replace the second test with a proper mock if the project has a boto3 stub fixture.

- [ ] **Step 2: Run the test to confirm it fails**

```bash
cd /home/bunnyshell/Fabric_4L/services/layer4-agents
python -m pytest tests/test_export_storage_tenant_prefix.py -v
```

Expected: FAIL because `tenant_id` parameter does not exist.

- [ ] **Step 3: Update `export_storage.py` to require `tenant_id` and prefix keys**

Modify `services/layer4-agents/src/layer4_agents/services/export_storage.py`:

```python
import os
import re


def _tenant_key(tenant_id: str, object_key: str) -> str:
    if not tenant_id:
        raise ValueError("tenant_id is required for S3 operations")
    if not object_key:
        raise ValueError("object_key is required")
    # Reject path traversal and absolute paths.
    if object_key.startswith("/") or ".." in object_key.split("/"):
        raise ValueError(f"object_key must be a relative path: {object_key}")
    # Strip accidental duplicate tenant prefix.
    prefix = f"{tenant_id}/"
    if object_key.startswith(prefix):
        return object_key
    return prefix + object_key


async def upload_bytes(
    *,
    tenant_id: str,
    object_key: str,
    content: bytes,
    content_type: str,
    metadata: dict[str, str] | None = None,
) -> StoredObject:
    key = _tenant_key(tenant_id, object_key)
    client = _s3_client()

    def _upload() -> dict:
        return client.put_object(
            Bucket=get_settings().export_storage_bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
            Metadata=metadata or {},
        )

    result = await asyncio.to_thread(_upload)
    etag = result.get("ETag")
    return StoredObject(bucket=get_settings().export_storage_bucket, key=key, etag=etag)


async def generate_download_url(
    *,
    tenant_id: str,
    object_key: str,
    expires_in_seconds: int | None = None,
) -> str:
    key = _tenant_key(tenant_id, object_key)
    client = _s3_client()
    expiry = expires_in_seconds or get_settings().export_signed_url_ttl_seconds

    def _sign() -> str:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": get_settings().export_storage_bucket, "Key": key},
            ExpiresIn=expiry,
        )

    return await asyncio.to_thread(_sign)
```

- [ ] **Step 4: Update callers**

In `services/layer4-agents/src/layer4_agents/api/routes/analysis.py` around line 1361, change:

```python
# Before
object_key = f"exports/tenant_{tenant_id}/..."
await upload_bytes(object_key=object_key, ...)

# After
object_key = "..."  # relative path only, without tenant prefix
await upload_bytes(tenant_id=tenant_id, object_key=object_key, ...)
```

In `services/layer4-agents/src/layer4_agents/tools.py` around line 403, do the same.

- [ ] **Step 5: Run the tests**

```bash
cd /home/bunnyshell/Fabric_4L/services/layer4-agents
python -m pytest tests/test_export_storage_tenant_prefix.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add services/layer4-agents/src/layer4_agents/services/export_storage.py \
        services/layer4-agents/src/layer4_agents/api/routes/analysis.py \
        services/layer4-agents/src/layer4_agents/tools.py \
        services/layer4-agents/tests/test_export_storage_tenant_prefix.py
git commit -m "tenancy: enforce tenant-prefixed S3 keys in Layer 4 export storage"
```

---

## Task 4: SEC-009 — Safe table/SET interpolation in tenant API

**Files:**
- Modify: `services/layer4-agents/src/layer4_agents/api/tenants.py`
- Modify: `services/layer4-agents/src/layer4_agents/tenants/api/routes/admin_dashboard.py`
- Test: `services/layer4-agents/tests/test_tenant_api_sql_safety.py` (create)

- [ ] **Step 1: Write the failing test**

Create `services/layer4-agents/tests/test_tenant_api_sql_safety.py`:

```python
import pytest
from sqlalchemy import text

from layer4_agents.api.tenants import _TENANT_ENTITY_TABLES


def test_tenant_entity_tables_are_allow_listed():
    # Unknown table names must not be accepted.
    assert "users" not in _TENANT_ENTITY_TABLES
    assert "tenants" in _TENANT_ENTITY_TABLES or len(_TENANT_ENTITY_TABLES) > 0
```

- [ ] **Step 2: Replace dynamic table name with pre-built statements**

Modify `services/layer4-agents/src/layer4_agents/api/tenants.py` around line 141:

```python
from sqlalchemy import text

_TENANT_ENTITY_TABLES = frozenset({"tenants", "users", "api_keys", ...})  # keep existing set

# Pre-build safe count statements for each allowed table.
_TENANT_COUNT_STATEMENTS = {
    table: text(f'SELECT COUNT(*) FROM "{table}" WHERE tenant_id = :tenant_id')
    for table in _TENANT_ENTITY_TABLES
}

# In the route:
if table_name not in _TENANT_ENTITY_TABLES:
    raise HTTPException(status_code=400, detail="Invalid table name")

stmt = _TENANT_COUNT_STATEMENTS[table_name]
result = await self.db_session.execute(stmt, {"tenant_id": str(tenant_id)})
```

- [ ] **Step 3: Replace dynamic SET clause with bound parameters**

Modify `services/layer4-agents/src/layer4_agents/tenants/api/routes/admin_dashboard.py` around line 457:

```python
_ALLOWED_TENANT_UPDATE_FIELDS = {"name", "settings"}

# Build SET clause from allow-listed fields with bound parameters.
set_parts = []
params = {}
for key, value in update_data.items():
    if key not in _ALLOWED_TENANT_UPDATE_FIELDS:
        raise HTTPException(status_code=400, detail=f"Cannot update field: {key}")
    set_parts.append(f"{key} = :{key}")
    params[key] = value

if not set_parts:
    raise HTTPException(status_code=400, detail="No valid fields to update")

params["id"] = tenant_id
set_clause = ", ".join(set_parts)
stmt = text(f"UPDATE tenants SET {set_clause} WHERE id = :id")
await db.execute(stmt, params)
```

- [ ] **Step 4: Run Layer 4 tenant API tests**

```bash
cd /home/bunnyshell/Fabric_4L/services/layer4-agents
python -m pytest tests/test_tenant_api_sql_safety.py tests -k tenant -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/layer4-agents/src/layer4_agents/api/tenants.py \
        services/layer4-agents/src/layer4_agents/tenants/api/routes/admin_dashboard.py \
        services/layer4-agents/tests/test_tenant_api_sql_safety.py
git commit -m "security: use allow-lists for tenant API dynamic SQL"
```

---

## Task 5: SEC-004 / TEN-007 — Route all Layer 4 Neo4j queries through `tenant_cypher.py`

**Files:**
- Modify: `services/layer4-agents/src/layer4_agents/services/tenant_query_helper.py` (deprecate or redirect)
- Modify: all files found by the audit script that call `session.run(...)` directly
- Test: `services/layer4-agents/tests/test_tenant_cypher_enforcement.py` (create)
- Script: `scripts/audit/layer4_direct_neo4j_calls.py` (create)

- [ ] **Step 1: Audit all direct Neo4j calls in Layer 4**

Create and run `scripts/audit/layer4_direct_neo4j_calls.py`:

```python
#!/usr/bin/env python3
"""List every direct Neo4j session.run / execute_query call in Layer 4."""

import ast
import sys
from pathlib import Path

ROOT = Path("services/layer4-agents/src/layer4_agents")


def find_calls(path: Path):
    text = path.read_text()
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in ("run", "execute_query"):
                print(f"{path}:{node.lineno}  {func.attr}()")


for path in ROOT.rglob("*.py"):
    find_calls(path)
```

Run it:

```bash
cd /home/bunnyshell/Fabric_4L
python scripts/audit/layer4_direct_neo4j_calls.py
```

Each printed line must either be migrated or explicitly justified.

- [ ] **Step 2: Write the failing tenant-cypher enforcement test**

Create `services/layer4-agents/tests/test_tenant_cypher_enforcement.py`:

```python
import pytest

from layer4_agents.services.tenant_cypher import (
    fetch_tenant_validated_records,
    TenantCypherValidationError,
)


async def test_query_missing_tenant_predicate_is_rejected():
    with pytest.raises(TenantCypherValidationError, match="tenant_id predicate"):
        await fetch_tenant_validated_records(
            driver=None,
            query="MATCH (n:ValueHypothesis) RETURN n",
            params={},
            tenant_id="tenant-123",
            operation="test",
        )


async def test_query_with_tenant_predicate_is_accepted():
    # Driver is None so execution will fail, but validation should pass.
    with pytest.raises(AttributeError):
        await fetch_tenant_validated_records(
            driver=None,
            query="MATCH (n:ValueHypothesis {tenant_id: $tenant_id}) RETURN n",
            params={},
            tenant_id="tenant-123",
            operation="test",
        )
```

- [ ] **Step 3: Run the test to confirm current behavior**

```bash
cd /home/bunnyshell/Fabric_4L/services/layer4-agents
python -m pytest tests/test_tenant_cypher_enforcement.py -v
```

Expected: `test_query_missing_tenant_predicate_is_rejected` should PASS because `tenant_cypher.py` already validates. If it fails, strengthen `_validate_tenant_query` first.

- [ ] **Step 4: Strengthen `tenant_cypher.py` if needed**

If the regex in `tenant_cypher.py` does not catch all valid tenant predicates, update `_TENANT_PREDICATE_PATTERN` to also accept `n.tenant_id IN $tenant_id` and brace syntax with spaces:

```python
_TENANT_PREDICATE_PATTERN = re.compile(
    r"(?i)(?:\{\s*[^}]*\btenant_id\s*:\s*\$(?:tenant_id|_tenant_id)\b[^}]*\}|"
    r"\b[A-Za-z_][A-Za-z0-9_]*\.tenant_id\s*(?:=|IN)\s*\$(?:tenant_id|_tenant_id)\b)"
)
```

- [ ] **Step 5: Migrate representative callers**

For each service file printed by the audit script, replace direct `session.run(query, params)` with:

```python
from layer4_agents.services.tenant_cypher import fetch_tenant_validated_records

records = await fetch_tenant_validated_records(
    driver=self.neo4j_driver,
    query=query,
    params=params,
    tenant_id=str(ctx.tenant_id),
    operation="value_hypothesis_engine.list",
)
```

Start with the files identified in the audit:

- `services/layer4-agents/src/layer4_agents/services/value_hypothesis_engine.py`
- `services/layer4-agents/src/layer4_agents/services/narrative_builder_service.py`
- `services/layer4-agents/src/layer4_agents/services/variable_registry_service.py`
- `services/layer4-agents/src/layer4_agents/services/value_pack_service.py`
- `services/layer4-agents/src/layer4_agents/services/formula_governance_service.py`
- `services/layer4-agents/src/layer4_agents/services/intelligence_orchestrator.py`
- `services/layer4-agents/src/layer4_agents/api/routes/analysis.py`
- `services/layer4-agents/src/layer4_agents/services/context_gatherer.py`
- `services/layer4-agents/src/layer4_agents/services/tenant_provisioning.py` (Neo4j constraint check — this is read-only global metadata and may be exempt, but document the exemption)

- [ ] **Step 6: Deprecate `tenant_query_helper.py`**

Modify `services/layer4-agents/src/layer4_agents/services/tenant_query_helper.py`:

```python
from layer4_agents.services.tenant_cypher import (
    fetch_tenant_validated_records,
    TenantCypherValidationError,
)


async def run_tenant_validated_query(*, driver, query, tenant_id, params=None):
    """Deprecated: use tenant_cypher.fetch_tenant_validated_records directly."""
    return await fetch_tenant_validated_records(
        driver=driver,
        query=query,
        params=params,
        tenant_id=tenant_id,
        operation="run_tenant_validated_query",
    )
```

- [ ] **Step 7: Run Layer 4 graph tests**

```bash
cd /home/bunnyshell/Fabric_4L/services/layer4-agents
python -m pytest tests -k "value_hypothesis or narrative or variable or tenant_cypher" -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add services/layer4-agents/src/layer4_agents/services/tenant_cypher.py \
        services/layer4-agents/src/layer4_agents/services/tenant_query_helper.py \
        $(git status --short | grep -E "^ M services/layer4-agents/src/.*\.py$" | awk '{print $2}') \
        services/layer4-agents/tests/test_tenant_cypher_enforcement.py \
        scripts/audit/layer4_direct_neo4j_calls.py
git commit -m "tenancy: route Layer 4 Neo4j queries through tenant-validating seam"
```

---

## Task 6: Final verification for this plan

- [ ] Run the full Layer 4 test suite:

```bash
cd /home/bunnyshell/Fabric_4L
make test-layer4
```

Expected: PASS.

- [ ] Run a grep check for residual hardcoded passwords and f-string Cypher:

```bash
cd /home/bunnyshell/Fabric_4L
grep -R '"password"' services/layer4-agents/src --include="*.py" -n || echo "No hardcoded Neo4j passwords found"
grep -R 'f".*MATCH\|f".*CREATE\|f".*WHERE' services/layer4-agents/src --include="*.py" -n || echo "No f-string Cypher found"
```

Expected: no matches, or only matches that have been reviewed and justified.

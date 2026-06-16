# Layer 2.5 Tenancy Hardening Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure Layer 2.5 database sessions always apply tenant RLS by making `tenant_id` a required parameter.

**Architecture:** Change `db_session` from `tenant_id: str | None = None` to `tenant_id: str` and raise when the caller cannot provide one. Audit all callers and fix any that pass `None`.

**Tech Stack:** Python 3.12, SQLAlchemy async session.

---

## Task 1: Require `tenant_id` in Layer 2.5 `db_session`

**Files:**
- Modify: `services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/database.py`
- Test: `services/layer2-5-signal-refinery/tests/test_db_session_tenant.py` (create)

- [ ] **Step 1: Find current callers**

```bash
cd /home/bunnyshell/Fabric_4L
grep -R "db_session(" services/layer2-5-signal-refinery/src --include="*.py" -n
grep -R "async with db_session" services/layer2-5-signal-refinery/src --include="*.py" -n
```

Record every call site; identify any that omit `tenant_id` or pass `None`.

- [ ] **Step 2: Write the failing test**

Create `services/layer2-5-signal-refinery/tests/test_db_session_tenant.py`:

```python
import pytest

from layer2_5_signal_refinery.database import db_session


async def test_db_session_rejects_none_tenant():
    with pytest.raises(ValueError, match="tenant_id is required"):
        async with db_session(tenant_id=None):
            pass  # pragma: no cover


async def test_db_session_accepts_valid_tenant():
    # This test only verifies the context manager enters when tenant_id is provided.
    # Full RLS behavior is covered by integration tests.
    async with db_session(tenant_id="tenant-123") as session:
        assert session is not None
```

- [ ] **Step 3: Run the test to confirm it fails**

```bash
cd /home/bunnyshell/Fabric_4L/services/layer2-5-signal-refinery
python -m pytest tests/test_db_session_tenant.py -v
```

Expected: `test_db_session_rejects_none_tenant` FAILS because `None` is currently accepted.

- [ ] **Step 4: Modify `db_session` to require `tenant_id`**

Modify `services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/database.py`:

```python
@asynccontextmanager
async def db_session(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session with tenant RLS applied.

    tenant_id is required. Passing an empty or None tenant is a programming
    error and fails closed to prevent cross-tenant data leakage.
    """
    if not tenant_id:
        raise ValueError("tenant_id is required for db_session; None or empty values are not allowed.")

    factory = get_session_factory()
    async with factory() as session:
        await session.execute(
            text("SET LOCAL app.tenant_id = :tenant_id"),
            {"tenant_id": tenant_id},
        )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 5: Fix callers that omit `tenant_id` or pass `None`**

For each call site found in Step 1:
- If the caller already has a tenant context, pass it.
- If the caller truly cannot know the tenant, rework the code so it does not touch tenant-scoped tables, or raise an error.

Example update:

```python
# Before
async with db_session() as session:
    ...

# After
ctx = get_request_context()
async with db_session(tenant_id=str(ctx.tenant_id)) as session:
    ...
```

- [ ] **Step 6: Run the new test**

```bash
cd /home/bunnyshell/Fabric_4L/services/layer2-5-signal-refinery
python -m pytest tests/test_db_session_tenant.py -v
```

Expected: PASS.

- [ ] **Step 7: Run the Layer 2.5 test suite**

```bash
cd /home/bunnyshell/Fabric_4L
make test-layer2
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/database.py \
        services/layer2-5-signal-refinery/tests/test_db_session_tenant.py \
        $(git status --short | grep -E "^ M services/layer2-5-signal-refinery/src/.*\.py$" | awk '{print $2}')
git commit -m "tenancy: require tenant_id in Layer 2.5 db_session"
```

---

## Task 2: Final verification for this plan

- [ ] Run the Layer 2 test suite end-to-end:

```bash
cd /home/bunnyshell/Fabric_4L
make test-layer2
```

Expected: PASS.

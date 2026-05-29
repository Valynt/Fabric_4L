# L1-TEST-INFRA-SQLALCHEMY-EVENT-IMPORT

**Priority:** High
**Status:** Open
**Created:** 2026-05-29

## Problem

Layer 1 test collection is blocked by an SQLAlchemy import error:

```
ImportError: cannot import name 'event' from 'sqlalchemy.orm'
```

**Location:** `services/layer1-ingestion/src/shared/models.py:26`

**Error Context:**
```python
from sqlalchemy.orm import declarative_base, event, relationship
```

## Root Cause

The `event` module should be imported from `sqlalchemy`, not `sqlalchemy.orm`. In SQLAlchemy 2.0+, `event` is a top-level module, not under `sqlalchemy.orm`.

## Likely Fix

Change the import from:
```python
from sqlalchemy.orm import declarative_base, event, relationship
```

To:
```python
from sqlalchemy import event
from sqlalchemy.orm import declarative_base, relationship
```

## Impact

- Blocks Layer 1 test collection (`python -m pytest tests --collect-only -q`)
- 488 tests collected, 35 errors during collection
- This is a pre-existing issue, not caused by L1 test import migration (PR L1-2)

## Notes

- Do not fix inside PR L1-2 unless confirmed as a tiny import-only fix
- Prefer separate ticket/PR if it touches broader model import behavior
- This should be addressed separately from the facade migration work

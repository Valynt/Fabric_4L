# CRM Integration Refactor Plan

> **SUPERSEDED (2026-08-27)** — The CRM connector subsystem described in this
> draft landed under `services/layer4-agents/src/layer4_agents/integrations/`
> and has since been consolidated into the canonical package
> `services/layer4-agents/src/layer4_agents/integration/connectors/` (re-export
> shims remain at the old `integrations/` path). All paths below are historical;
> new code must import from `layer4_agents.integration.connectors.*`.

**Status:** Draft — awaiting approval before PR 1 implementation (superseded by the consolidation above).  
**Scope:** All 9 PRs at decision fidelity; PRs 1–3 specified to diff-level.  
**Locked decisions:** See user Q&A block below.

| Decision | Call |
|---|---|
| DB migration | Additive columns on `Integration` in PR 2; new `external_connections` table with dual-write in PR 7; drop old in PR 9 |
| Plan scope | All 9 PRs at decision-level; PRs 1–3 at diff-level |
| Webhooks | Preserve behavior; errors → taxonomy (PR 1), status writes → reducer (PR 2), provider calls → connector (PR 3); become sync-hints in PR 5 |
| Read source | New normalized child tables (PR 4a, parallel with PR 3); tool cutover in PR 4b; `Account` unchanged; JSONB dropped in PR 9 |

---

## PR 1 — `core/errors.py` + `core/types.py` (Classification-only)

**Goal:** Introduce the provider-side error taxonomy and canonical value types. No observable behavior change; only exception classification at the boundary.

**New files**

- `services/layer4-agents/src/layer4_agents/integrations/__init__.py`
- `services/layer4-agents/src/layer4_agents/integrations/core/__init__.py`
- `services/layer4-agents/src/layer4_agents/integrations/core/errors.py`
- `services/layer4-agents/src/layer4_agents/integrations/core/types.py`

**`errors.py` contents**

```python
from __future__ import annotations

class CRMError(Exception):
    """Base class for all CRM-boundary errors."""

class TransientError(CRMError):
    """Retryable: network blip, rate limit, 5xx, timeout."""

class AuthError(CRMError):
    """Credential failure or expired token (401 / invalid_grant)."""

class PermissionError_(CRMError):
    """Authorized identity lacks permission (403)."""

class MappingError(CRMError):
    """Provider response could not be mapped to canonical shape."""

class PermanentError(CRMError):
    """Non-retryable: bad request, malformed ID, not found, validation."""
```

**`types.py` contents**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

class CRMModel(StrEnum):
    ACCOUNT = "account"
    CONTACT = "contact"
    OPPORTUNITY = "opportunity"
    ENGAGEMENT = "engagement"

@dataclass(frozen=True, slots=True)
class SyncCursor:
    """Opaque pagination token; string form is JSON-serializable."""
    value: str | None = None

    def __str__(self) -> str:
        return self.value or ""

@dataclass(frozen=True, slots=True)
class CanonicalRecord:
    """Provider-neutral record emitted by a connector and consumed by the SyncEngine."""
    model: CRMModel
    remote_id: str
    remote_modified_at: datetime | None = None
    remote_deleted_at: datetime | None = None
    # Canonical scalar fields — always present names regardless of provider.
    canonical: dict[str, Any] = field(default_factory=dict)
    # Provider-specific supplemental fields preserved for round-tripping / provenance.
    supplemental: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class CRMOperationResult:
    """Result of a connector write operation."""
    success: bool
    remote_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
```

**Files touched in PR 1**

- `services/layer4-agents/src/layer4_agents/tools/crm_tools.py`
  - At the start of each provider I/O boundary (`_get_salesforce_data`, `_get_hubspot_data`, `_update_salesforce_opportunity`, `_update_hubspot_deal`, `_fetch_salesforce_interactions`, `_fetch_hubspot_interactions`):
    - Catch `httpx.HTTPStatusError` and translate by status code:
      - 401 / invalid_grant → `AuthError`
      - 403 → `PermissionError_`
      - 400, 404, 422 → `PermanentError`
      - 429, 5xx, timeout → `TransientError`
    - Catch `httpx.RequestError`, `httpx.TimeoutException` → `TransientError`
    - Catch Pydantic `ValidationError` / failed field mapping → `MappingError`
    - Catch `ValueError` from `_SalesforceIdSafetyMixin` / malformed IDs → `PermanentError`
  - The existing retry loops inside the tools stay unchanged for this PR; they continue to raise the same exception classes, just typed.
- `services/layer4-agents/src/layer4_agents/services/integration_service.py`
  - In `test_connection`, wrap provider-specific exceptions with the taxonomy before returning/raising.
  - In `refresh_salesforce_token`, wrap OAuth/token HTTP failures as `AuthError` or `TransientError`.
- `services/layer4-agents/src/layer4_agents/services/crm_sync_service.py`
  - Import the taxonomy.
  - In `_execute_with_retry`, continue catching `CRMError` / `Exception`; use `isinstance(e, TransientError)` to decide whether retry attempts were exhausted for a transient reason (existing behavior already retries on all exceptions, so classification is additive logging/observability only).

**Tests / verification**

- `pytest services/layer4-agents/tests/test_crm_sync_service.py services/layer4-agents/tests/test_integration_service.py`
- Add targeted unit tests for the classification rules in `services/layer4-agents/tests/integrations/test_core_errors.py` (new).
- No Alembic migration in PR 1.

**Rollback trigger:** Any test failure indicating a behavioral change in retry or error propagation.

---

## PR 2 — State Reducer (observed vs operational status)

**Goal:** Fix the raw-status-mutation bug by adding `observed_sync_status`, `operational_status`, `last_known_good_at`, and `error_class` to the existing `Integration` table, and route all status writes through a pure `reduce()` function. Existing `status` column is kept as a shim for backward compatibility.

**Schema changes (Alembic migration)**

```sql
ALTER TABLE integrations ADD COLUMN observed_sync_status VARCHAR(32);
ALTER TABLE integrations ADD COLUMN operational_status VARCHAR(32);
ALTER TABLE integrations ADD COLUMN last_known_good_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE integrations ADD COLUMN error_class VARCHAR(64);

-- Backfill
UPDATE integrations
SET observed_sync_status = CASE
    WHEN status = 'active' THEN 'ready'
    WHEN status = 'failed' AND last_successful_sync_at IS NOT NULL THEN 'degraded'
    WHEN status = 'failed' THEN 'blocked'
    ELSE status
END,
operational_status = observed_sync_status,
last_known_good_at = last_successful_sync_at;
```

**New file**

- `services/layer4-agents/src/layer4_agents/integrations/core/state.py`

```python
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

class OperationalStatus(StrEnum):
    READY = "ready"           # Last sync succeeded; connection healthy
    DEGRADED = "degraded"     # Some records failed or last good sync is stale
    BLOCKED = "blocked"       # Auth/permission/config failure; requires human action
    RUNNING = "running"       # Sync in progress
    IDLE = "idle"             # Never synced; not an error

class ObservedStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    RUNNING = "running"
    IDLE = "idle"

class ErrorClass(StrEnum):
    NONE = "none"
    TRANSIENT = "transient"
    AUTH = "auth"
    PERMISSION = "permission"
    MAPPING = "mapping"
    PERMANENT = "permanent"

STATE_TRANSITIONS: dict[OperationalStatus, set[OperationalStatus]] = {
    OperationalStatus.IDLE: {
        OperationalStatus.RUNNING, OperationalStatus.READY, OperationalStatus.BLOCKED,
    },
    OperationalStatus.RUNNING: {
        OperationalStatus.READY, OperationalStatus.DEGRADED, OperationalStatus.BLOCKED, OperationalStatus.IDLE,
    },
    OperationalStatus.READY: {
        OperationalStatus.RUNNING, OperationalStatus.DEGRADED, OperationalStatus.BLOCKED,
    },
    OperationalStatus.DEGRADED: {
        OperationalStatus.RUNNING, OperationalStatus.READY, OperationalStatus.BLOCKED, OperationalStatus.DEGRADED,
    },
    OperationalStatus.BLOCKED: {
        OperationalStatus.RUNNING, OperationalStatus.READY, OperationalStatus.DEGRADED,
    },
}

def reduce(
    observed: ObservedStatus,
    current: OperationalStatus | None,
    error_class: ErrorClass = ErrorClass.NONE,
    last_known_good_at: datetime | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Pure function: compute the next operational state from an observed event.

    Args:
        observed: What the connector/sync engine just reported.
        current: The current operational_status (None for a never-synced integration).
        error_class: Class of the most recent failure, if any.
        last_known_good_at: Timestamp of the last fully successful sync.
        now: Clock override for deterministic tests.

    Returns:
        A dict with keys: operational_status, observed_sync_status, error_class,
        last_known_good_at, status (legacy shim).
    """
    now = now or datetime.now(timezone.utc)
    current = current or OperationalStatus.IDLE

    if observed == ObservedStatus.RUNNING:
        next_state = OperationalStatus.RUNNING
    elif observed == ObservedStatus.SUCCESS:
        next_state = OperationalStatus.READY
        if error_class == ErrorClass.NONE:
            last_known_good_at = now
    elif observed == ObservedStatus.PARTIAL:
        next_state = OperationalStatus.DEGRADED
    elif observed == ObservedStatus.FAILURE:
        if error_class in {ErrorClass.AUTH, ErrorClass.PERMISSION, ErrorClass.PERMANENT}:
            next_state = OperationalStatus.BLOCKED
        else:
            next_state = OperationalStatus.DEGRADED
    elif observed == ObservedStatus.IDLE:
        next_state = current if current != OperationalStatus.RUNNING else OperationalStatus.IDLE
    else:
        next_state = current

    # Enforce allowed transitions; if disallowed, degrade rather than silently jumping.
    if next_state not in STATE_TRANSITIONS.get(current, set()):
        if current == OperationalStatus.RUNNING and next_state == OperationalStatus.RUNNING:
            pass  # already handled above
        else:
            next_state = OperationalStatus.DEGRADED

    legacy_status_map = {
        OperationalStatus.READY: "active",
        OperationalStatus.RUNNING: "running",
        OperationalStatus.DEGRADED: "failed",
        OperationalStatus.BLOCKED: "failed",
        OperationalStatus.IDLE: "idle",
    }

    return {
        "observed_sync_status": observed.value,
        "operational_status": next_state.value,
        "error_class": error_class.value,
        "last_known_good_at": last_known_good_at,
        "status": legacy_status_map[next_state],
    }
```

**Files touched in PR 2**

- `services/layer4-agents/src/layer4_agents/models/integration.py`
  - Add columns:
    - `observed_sync_status: Mapped[str | None]`
    - `operational_status: Mapped[str | None]`
    - `last_known_good_at: Mapped[datetime | None]`
    - `error_class: Mapped[str | None]`
  - `to_dict()` continues to expose only `status` (legacy) plus the new operational fields; credentials excluded.
- `services/layer4-agents/src/layer4_agents/services/crm_sync_service.py`
  - Replace raw status mutations in `_update_sync_status` and `sync_provider` with calls to `reduce(...)`.
  - When a sync starts: `reduce(ObservedStatus.RUNNING, ...)`.
  - On partial success: `reduce(ObservedStatus.PARTIAL, ..., error_class=...)`.
  - On full success: `reduce(ObservedStatus.SUCCESS, ...)`.
  - On failure: map the PR 1 error taxonomy to `ErrorClass` and call `reduce(ObservedStatus.FAILURE, ..., error_class=...)`. Then persist all returned fields plus the legacy `status`.
- `services/layer4-agents/src/layer4_agents/services/integration_service.py`
  - When connection test succeeds/fails, write status through `reduce(...)`.
- `services/layer4-agents/src/layer4_agents/api/routes/crm_webhooks.py`
  - If webhook handlers mutate integration status, route those writes through `reduce(...)`.
- `services/layer4-agents/src/layer4_agents/api/routes/integrations.py`
  - On create/update, set initial operational state to `idle` via `reduce(ObservedStatus.IDLE, None)`.

**Tests / verification**

- Add `services/layer4-agents/tests/integrations/test_core_state.py` covering:
  - success → ready
  - partial → degraded
  - auth failure → blocked
  - transient failure → degraded
  - running observed while already running stays running
  - disallowed transitions degrade
  - legacy status shim values
- Update existing tests to assert on `operational_status` where they currently assert `status`.
- Run: `pytest services/layer4-agents/tests/test_crm_sync_service.py services/layer4-agents/tests/test_integration_service.py services/layer4-agents/tests/integrations/`
- Run migration check: `make check-migration-heads`.

**Rollback trigger:** Any API response or test that expects the old `status` enum values to change semantics.

---

## PR 3 — Extract Salesforce and HubSpot providers behind `CRMConnector`

**Goal:** Move provider-specific HTTP clients, SOQL, association traversal, auth, and mapping into `providers/salesforce/` and `providers/hubspot/` directories behind a single `CRMConnector` protocol. The existing `CRMSyncService` and `IntegrationService` call the protocol, not the provider internals.

**New package layout**

```
services/layer4-agents/src/layer4_agents/integrations/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── errors.py          # PR 1
│   ├── types.py           # PR 1
│   └── state.py           # PR 2
├── connector.py           # CRMConnector protocol + CRMWriteConnector protocol
├── factory.py             # get_connector(provider, config, db) -> CRMConnector
├── utils.py               # small helpers (timeout wrapper, etc.)
└── providers/
    ├── __init__.py
    ├── salesforce/
    │   ├── __init__.py
    │   ├── auth.py          # OAuth token refresh, header building
    │   ├── client.py        # httpx client + SOQL query helpers + response parsing
    │   ├── mapper.py        # Salesforce record -> CanonicalRecord
    │   └── connector.py     # SalesforceConnector(CRMConnector)
    └── hubspot/
        ├── __init__.py
        ├── auth.py          # HubSpot token/header handling
        ├── client.py        # HubSpot API client + association traversal
        ├── mapper.py        # HubSpot record -> CanonicalRecord
        └── connector.py     # HubSpotConnector(CRMConnector)
```

**New files**

`connector.py`:

```python
from __future__ import annotations

from typing import AsyncIterator, Protocol, runtime_checkable

from .core.types import CanonicalRecord, CRMModel, CRMOperationResult, SyncCursor

@runtime_checkable
class CRMConnector(Protocol):
    """The sole provider boundary for read/sync operations."""

    async def authenticate(self, *, timeout: float | None = None) -> bool:
        ...

    async def read_account(
        self,
        remote_id: str,
        *,
        cursor: SyncCursor | None = None,
        timeout: float | None = None,
    ) -> CanonicalRecord:
        """Read a single account by its provider-native ID."""
        ...

    async def list_accounts(
        self,
        *,
        cursor: SyncCursor | None = None,
        page_size: int = 100,
        timeout: float | None = None,
    ) -> tuple[list[CanonicalRecord], SyncCursor]:
        """Paginate accounts. Returns (records, next_cursor)."""
        ...

    async def read_contacts_for_account(
        self,
        account_remote_id: str,
        *,
        timeout: float | None = None,
    ) -> list[CanonicalRecord]:
        ...

    async def read_opportunities_for_account(
        self,
        account_remote_id: str,
        *,
        timeout: float | None = None,
    ) -> list[CanonicalRecord]:
        ...

    async def read_engagements_for_account(
        self,
        account_remote_id: str,
        *,
        since: str | None = None,
        limit: int = 50,
        timeout: float | None = None,
    ) -> list[CanonicalRecord]:
        ...

@runtime_checkable
class CRMWriteConnector(Protocol):
    """Narrow interface for agent writes back to CRM."""

    async def update_opportunity(
        self,
        remote_id: str,
        updates: dict,
        *,
        timeout: float | None = None,
    ) -> CRMOperationResult:
        ...

    async def create_engagement(
        self,
        account_remote_id: str,
        engagement: dict,
        *,
        timeout: float | None = None,
    ) -> CRMOperationResult:
        ...
```

`factory.py`:

```python
from __future__ import annotations

from .connector import CRMConnector
from .providers.hubspot.connector import HubSpotConnector
from .providers.salesforce.connector import SalesforceConnector

_CONNECTOR_REGISTRY: dict[str, type[CRMConnector]] = {
    "salesforce": SalesforceConnector,
    "hubspot": HubSpotConnector,
}

def get_connector(provider_slug: str, config: dict, db=None) -> CRMConnector:
    try:
        cls = _CONNECTOR_REGISTRY[provider_slug.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported CRM provider: {provider_slug}") from exc
    return cls(config=config, db=db)
```

**Provider implementations**

Salesforce:

- `auth.py`: Move `refresh_salesforce_token` logic and header construction out of `integration_service.py` and `crm_tools.py`. Expose:
  - `SalesforceAuth(config: dict)`
  - `async def get_access_token(self) -> str`
  - `async def refresh(self) -> dict[str, str]`
- `client.py`: Encapsulate `httpx.AsyncClient`, SOQL query building, response parsing, rate-limit detection, and pagination. Key methods:
  - `query(soql, ...)`
  - `get_account(remote_id, ...)`
  - `get_contacts_for_account(account_id, ...)`
  - `get_opportunities_for_account(account_id, ...)`
  - `get_tasks/events_for_account(account_id, ...)`
- `mapper.py`: Convert Salesforce Account/Contact/Opportunity/Task/Event records into `CanonicalRecord`.
- `connector.py`: `SalesforceConnector` implementing `CRMConnector` and `CRMWriteConnector`. Translates httpx exceptions to PR 1 taxonomy at the boundary.

HubSpot:

- `auth.py`: HubSpot token/header handling.
- `client.py`: Encapsulate HubSpot API client, association traversal, pagination.
- `mapper.py`: Convert HubSpot Company/Contact/Deal/Engagement records into `CanonicalRecord`.
- `connector.py`: `HubSpotConnector` implementing `CRMConnector` and `CRMWriteConnector`.

**Files touched in PR 3**

- `services/layer4-agents/src/layer4_agents/tools/crm_tools.py`
  - `GetProspectDataTool`, `UpdateOpportunityTool`, `FetchInteractionHistoryTool` become thin adapters:
    - `GetProspectDataTool.execute` → call `CRMConnector.read_account`, `read_contacts_for_account`, `read_opportunities_for_account`, `read_engagements_for_account`, then assemble `GetProspectDataOutput`.
    - `UpdateOpportunityTool.execute` → call `CRMWriteConnector.update_opportunity`.
    - `FetchInteractionHistoryTool.execute` → call `CRMConnector.read_engagements_for_account`.
  - Remove direct SOQL, HubSpot association logic, pagination, and response parsing from this file; they move to provider modules.
  - Keep `_SalesforceIdSafetyMixin` until PR 5 (or move it to `providers/salesforce/utils.py` if it is purely Salesforce-specific).
- `services/layer4-agents/src/layer4_agents/services/integration_service.py`
  - `test_connection` → `connector = get_connector(...); await connector.authenticate()`.
  - `refresh_salesforce_token` → delegate to `SalesforceAuth(config).refresh()` and persist returned tokens.
  - Connection validation still lives here; provider credential shape validation stays here because it is generic.
- `services/layer4-agents/src/layer4_agents/services/crm_sync_service.py`
  - `GetProspectDataTool(...)` stays the sync engine's data source in PR 3 (no SyncEngine yet). The tool now internally uses the connector.
  - Provider-specific status writes and token refresh checks remain, but any direct provider branching is removed or simplified.
- `services/layer4-agents/src/layer4_agents/api/routes/crm_webhooks.py`
  - Provider-specific fetch-on-notify paths, if any, route through the connector.

**Tests / verification**

- Add `services/layer4-agents/tests/integrations/providers/test_salesforce_connector.py` and `test_hubspot_connector.py`.
- Add `services/layer4-agents/tests/integrations/test_factory.py`.
- Existing `test_crm_sync_service.py` and `test_integration_service.py` should pass with minimal mock updates because the public tool/service signatures are preserved.
- Run: `pytest services/layer4-agents/tests/integrations/ services/layer4-agents/tests/test_crm_sync_service.py services/layer4-agents/tests/test_integration_service.py`

**Rollback trigger:** Any agent tool or API test failure, or increased line count in `crm_tools.py` / `integration_service.py` instead of decreased.

---

## PR 4a — Normalize child tables (parallel with PR 3)

**Goal:** Move opportunities, contacts, and engagements out of `Account` JSONB into normalized tables so PR 5's SyncEngine can upsert, watermark, quarantine, and tombstone individual records.

**Schema**

```sql
CREATE TABLE crm_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR NOT NULL,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    provider_slug VARCHAR NOT NULL,
    remote_id VARCHAR NOT NULL,
    remote_modified_at TIMESTAMP WITH TIME ZONE,
    remote_deleted_at TIMESTAMP WITH TIME ZONE,
    name VARCHAR,
    email VARCHAR,
    phone VARCHAR,
    title VARCHAR,
    supplemental JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(tenant_id, provider_slug, remote_id)
);

CREATE TABLE crm_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR NOT NULL,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    provider_slug VARCHAR NOT NULL,
    remote_id VARCHAR NOT NULL,
    remote_modified_at TIMESTAMP WITH TIME ZONE,
    remote_deleted_at TIMESTAMP WITH TIME ZONE,
    name VARCHAR,
    stage VARCHAR,
    amount DECIMAL(19,4),
    close_date DATE,
    probability FLOAT,
    supplemental JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(tenant_id, provider_slug, remote_id)
);

CREATE TABLE crm_engagements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR NOT NULL,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    provider_slug VARCHAR NOT NULL,
    remote_id VARCHAR NOT NULL,
    remote_modified_at TIMESTAMP WITH TIME ZONE,
    remote_deleted_at TIMESTAMP WITH TIME ZONE,
    kind VARCHAR,  -- call, email, meeting, task, note
    subject VARCHAR,
    occurred_at TIMESTAMP WITH TIME ZONE,
    direction VARCHAR,
    outcome VARCHAR,
    supplemental JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(tenant_id, provider_slug, remote_id)
);

-- RLS policies and indexes (tenant-scoped)
CREATE INDEX idx_crm_contacts_account ON crm_contacts(tenant_id, account_id);
CREATE INDEX idx_crm_opportunities_account ON crm_opportunities(tenant_id, account_id);
CREATE INDEX idx_crm_engagements_account ON crm_engagements(tenant_id, account_id);
CREATE INDEX idx_crm_engagements_occurred ON crm_engagements(tenant_id, account_id, occurred_at);
```

**Files touched**

- `services/layer4-agents/src/layer4_agents/models/__init__.py` — register new models.
- `services/layer4-agents/src/layer4_agents/models/crm_records.py` — new SQLAlchemy models.
- `services/layer4-agents/src/layer4_agents/services/crm_sync_service.py` — dual-write JSONB + normalized rows during sync (flag-gated or unconditional in PR 4a).
- Backfill migration from existing JSONB columns.

**Exit criteria:** Tables exist, dual-write stable, backfill complete.

---

## PR 4b — Cut agent read tools to canonical tables

**Goal:** `GetProspectDataTool`, `FetchInteractionHistoryTool` read from normalized tables when the per-tenant flag is on.

**Feature flag:** `connection.read_from_normalized_tables` (tenant-level setting or global env).

**Files touched**

- `services/layer4-agents/src/layer4_agents/tools/crm_tools.py` — branch on flag; compare outputs in shadow mode.
- Add comparison telemetry: mismatches between JSONB and normalized outputs logged but not failing the tool.

**Exit criteria:** Shadow comparison shows <0.1% mismatch for one week in staging; then default-on.

---

## PR 5 — Generic SyncEngine

**Goal:** Replace `CRMSyncService.sync_provider` with a provider-agnostic `SyncEngine` that handles watermarks, pagination, retries, quarantine, and last-known-good status.

**New files**

- `services/layer4-agents/src/layer4_agents/integrations/sync_engine.py`
- `services/layer4-agents/src/layer4_agents/integrations/quarantine.py` (quarantine table / store)
- `services/layer4-agents/src/layer4_agents/integrations/watermark.py`

**Files touched**

- `services/layer4-agents/src/layer4_agents/services/crm_sync_service.py` — becomes a thin wrapper that constructs `SyncEngine` and calls `sync(connection_id)`.
- Webhooks enqueue a sync task instead of triggering inline logic.

**Exit criteria:** `test_crm_sync_service.py` passes with the engine under the hood; no regressions in sync stats semantics.

---

## PR 6 — Lease-based scheduler

**Goal:** Replace tenant sweeps with a lease-based scheduler using a `sync_leases` table.

**Schema**

```sql
CREATE TABLE sync_leases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR NOT NULL,
    provider_slug VARCHAR NOT NULL,
    worker_id VARCHAR,
    acquired_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(tenant_id, provider_slug)
);
```

**Files touched**

- `services/layer4-agents/src/layer4_agents/services/crm_sync_scheduler.py`

**Exit criteria:** Scheduler no longer sweeps all tenants; workers acquire leases; missed leases recover.

---

## PR 7 — Generic `ExternalConnection` model and API

**Goal:** Rename/replace `Integration` with `external_connections`; expose generic `/v1/external-connections/*` endpoints while keeping old endpoints as shims.

**Schema**

```sql
CREATE TABLE external_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR NOT NULL,
    connection_type VARCHAR NOT NULL,  -- 'crm' today, extensible later
    provider_slug VARCHAR NOT NULL,
    enabled BOOLEAN DEFAULT false,
    display_name VARCHAR,
    credentials_encrypted BYTEA,
    encryption_key_id VARCHAR,
    config JSONB DEFAULT '{}',
    observed_sync_status VARCHAR(32),
    operational_status VARCHAR(32),
    last_sync_at TIMESTAMP WITH TIME ZONE,
    last_successful_sync_at TIMESTAMP WITH TIME ZONE,
    last_known_good_at TIMESTAMP WITH TIME ZONE,
    error_class VARCHAR(64),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(tenant_id, connection_type, provider_slug)
);
```

**Dual-write rule:** Both `Integration` and `external_connections` are updated from the same `ConnectionState` object in the same transaction; the reducer output is the single source of truth.

**Files touched**

- `services/layer4-agents/src/layer4_agents/models/external_connection.py` (new)
- `services/layer4-agents/src/layer4_agents/api/routes/external_connections.py` (new)
- `services/layer4-agents/src/layer4_agents/api/routes/integrations.py` — shim old endpoints to new model.
- Frontend schema in `apps/web/src/lib/schemas/integrations.ts` updated to new field names.

**Exit criteria:** New endpoints pass contract tests; old endpoints continue to work.

---

## PR 8 — Frontend Connection Center

**Goal:** Provider-agnostic React Connection Center that does not require frontend changes to add a new provider.

**Files touched**

- `apps/web/src/pages/Integrations.tsx`
- `apps/web/src/components/integrations/IntegrationConfigPanel.tsx`
- `apps/web/src/hooks/useIntegrations.ts`
- `apps/web/src/lib/schemas/integrations.ts`

**Exit criteria:** Adding a new provider requires only backend connector + a provider metadata entry; no UI or hook changes.

---

## PR 9 — Cleanup

**Goal:** Remove legacy shims and JSONB fields after dual-write windows have proven stable.

**Items**

- Drop `Integration` table.
- Remove legacy `/integrations/*` shim routes.
- Drop embedded `opportunities`, `contacts`, `interactions` JSONB columns from `Account`.
- Remove legacy `status` shim column from `external_connections` (kept during PR 7).

**Exit criteria:** All 111 tests green; no references to legacy types in code or OpenAPI specs.

---

## Cross-PR risks and mitigations

| Risk | Mitigation |
|---|---|
| PR 1 error classification changes retry behavior | Add tests asserting the exact retry count per exception class; preserve existing catch-all fallback. |
| PR 2 legacy status shim drifts from operational status | Unit-test the shim map; dual-write both columns from the same `reduce()` output. |
| PR 3 moving code to providers loses fix history | Use `git mv`-style moves where possible; preserve commit history via focused commits. |
| PR 4a normalized tables create write amplification | Dual-write; keep JSONB primary until PR 5 validates. |
| PR 7 dual-write between `Integration` and `external_connections` | Single `ConnectionState` object written in one transaction; never update tables separately. |
| Live tenant credential migration | PR 7 includes deterministic ID/backfill script; credentials remain encrypted and key IDs preserved. |

## Next action

Upon approval of this plan, begin implementing PR 1: create `integrations/core/errors.py` and `types.py`, and wrap existing provider exceptions at the boundary in `crm_tools.py`, `integration_service.py`, and `crm_sync_service.py`.

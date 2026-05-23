"""
Persistence layer for the standalone API.

The in-memory implementation is retained for local demos and tests only.
When ``mock_persistence`` is disabled, the API requires an external
PostgreSQL database and will fail fast if one is not configured.
"""

from __future__ import annotations

import builtins
import json
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from value_fabric.shared.database import MissingTenantContextError, require_tenant_context
from value_fabric.shared.database.tenant_validation import RESERVED_TENANT_KEYWORDS

from app.core.config import get_settings
from app.models.schemas import (
    Account,
    AccountVersionSnapshot,
    AgentRun,
    AuditLogEvent,
    BusinessCase,
    Evidence,
    Formula,
    GovernanceGate,
    GroundTruthObject,
    ReviewComment,
    ReviewDecision,
    ReviewRequest,
    ROICalculation,
    Scenario,
    Signal,
    Stakeholder,
    Tenant,
    ToolResult,
    User,
    ValueDriver,
    DSARRequestRecord,
    DSARPackage,
    ValueHypothesis,
    ValuePack,
)

T = TypeVar("T")


class ProductionPersistenceNotConfigured(RuntimeError):
    """Raised when the API is asked to run without a durable persistence backend."""


class UnsupportedDatabaseURL(ProductionPersistenceNotConfigured):
    """Raised when ``database_url`` does not identify a supported durable backend."""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _to_payload(obj: Any) -> dict[str, Any]:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return dict(obj)
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    raise TypeError(f"Unsupported persistence object type: {type(obj).__name__}")


def _tenant_from_obj(obj: Any, tenant_field: str) -> str | None:
    if isinstance(obj, dict):
        value = obj.get(tenant_field)
    else:
        value = getattr(obj, tenant_field, None)
    return str(value) if value is not None else None


def _is_tenant_scoped_field(tenant_field: str) -> bool:
    return tenant_field == "tenant_id"


class InMemoryTable(Generic[T]):
    """Thread-safe, tenant-aware table used for local development and tests only."""

    def __init__(self, name: str, tenant_field: str = "tenant_id"):
        self.name = name
        self.tenant_field = tenant_field
        self._store: dict[str, T] = {}
        self._lock = threading.Lock()

    def _get_tenant_id(self, obj: T) -> str | None:
        return _tenant_from_obj(obj, self.tenant_field)

    def _require_tenant_scope(self, tenant_id: str | None, *, operation: str) -> str:
        if not _is_tenant_scoped_field(self.tenant_field):
            return str(tenant_id) if tenant_id is not None else ""
        return require_tenant_context(tenant_id, operation=f"{self.name}.{operation}")

    def _require_object_tenant(self, obj: T) -> str:
        if not _is_tenant_scoped_field(self.tenant_field):
            tenant_id = self._get_tenant_id(obj)
            return str(tenant_id) if tenant_id is not None else ""
        return require_tenant_context(
            self._get_tenant_id(obj),
            operation=f"{self.name}.insert",
        )

    def insert(self, id: str, obj: T) -> T:
        self._require_object_tenant(obj)
        with self._lock:
            self._store[id] = obj
        return obj

    def get(self, id: str, tenant_id: str | None = None) -> T | None:
        normalized_tenant_id = self._require_tenant_scope(tenant_id, operation="get")
        with self._lock:
            obj = self._store.get(id)
            if obj is None:
                return None
            if _is_tenant_scoped_field(self.tenant_field) and self._get_tenant_id(obj) != normalized_tenant_id:
                return None
            return obj

    def list(
        self,
        tenant_id: str | None = None,
        filter_fn: Callable[[T], bool] | None = None,
        *,
        allow_system_scope: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> builtins.list[T]:
        normalized_tenant_id = self._require_tenant_scope(tenant_id, operation="list")
        with self._lock:
            items = list(self._store.values())
        if _is_tenant_scoped_field(self.tenant_field):
            # Cross-tenant reads are only permitted when the caller explicitly
            # opts in via allow_system_scope=True AND passes a reserved keyword.
            # Passing a reserved keyword alone is not sufficient — this prevents
            # any caller from obtaining unscoped reads by guessing "system".
            if allow_system_scope and normalized_tenant_id in RESERVED_TENANT_KEYWORDS:
                pass  # intentional cross-tenant read
            else:
                items = [i for i in items if self._get_tenant_id(i) == normalized_tenant_id]
        if filter_fn:
            items = [i for i in items if filter_fn(i)]
        if offset:
            items = items[offset:]
        if limit is not None:
            items = items[:limit]
        return items

    def update(self, id: str, tenant_id: str | None = None, **fields: Any) -> T | None:
        normalized_tenant_id = self._require_tenant_scope(tenant_id, operation="update")
        with self._lock:
            obj = self._store.get(id)
            if obj is None:
                return None
            if _is_tenant_scoped_field(self.tenant_field) and self._get_tenant_id(obj) != normalized_tenant_id:
                return None
            if isinstance(obj, dict):
                obj.update(fields)
                obj["updated_at"] = _now_iso()
            else:
                for key, value in fields.items():
                    setattr(obj, key, value)
                if hasattr(obj, "updated_at"):
                    obj.updated_at = _now_iso()
            return obj

    def delete(self, id: str, tenant_id: str | None = None) -> bool:
        normalized_tenant_id = self._require_tenant_scope(tenant_id, operation="delete")
        with self._lock:
            obj = self._store.get(id)
            if obj is None:
                return False
            if _is_tenant_scoped_field(self.tenant_field) and self._get_tenant_id(obj) != normalized_tenant_id:
                return False
            del self._store[id]
            return True


class AppendOnlyInMemoryTable(InMemoryTable[T]):
    def update(self, id: str, tenant_id: str | None = None, **fields: Any) -> T | None:  # noqa: ARG002
        raise PermissionError(f"{self.name} is immutable and cannot be updated")

    def delete(self, id: str, tenant_id: str | None = None) -> bool:  # noqa: ARG002
        raise PermissionError(f"{self.name} is immutable and cannot be deleted")


class SQLiteTable(Generic[T]):
    """Durable JSON-record table preserving the current standalone API table API.

    The table stores each Pydantic object as a JSON payload and keeps a separate
    tenant column for fail-closed tenant-scoped reads. This intentionally avoids
    importing lower-layer implementations or duplicating business logic across
    Fabric_4L layers while making the non-mock standalone API path executable.
    """

    def __init__(
        self,
        name: str,
        connection: sqlite3.Connection,
        lock: threading.RLock,
        model_cls: type[T] | None = None,
        tenant_field: str = "tenant_id",
    ):
        self.name = name
        self.tenant_field = tenant_field
        self._connection = connection
        self._lock = lock
        self._model_cls = model_cls

    def _deserialize(self, payload: str) -> T:
        data = json.loads(payload)
        if self._model_cls and issubclass(self._model_cls, BaseModel):
            return self._model_cls.model_validate(data)  # type: ignore[return-value]
        return data  # type: ignore[return-value]

    def _get_tenant_id(self, obj: T) -> str | None:
        return _tenant_from_obj(obj, self.tenant_field)

    def _require_tenant_scope(self, tenant_id: str | None, *, operation: str) -> str:
        if not _is_tenant_scoped_field(self.tenant_field):
            return str(tenant_id) if tenant_id is not None else ""
        return require_tenant_context(tenant_id, operation=f"{self.name}.{operation}")

    def _require_object_tenant(self, obj: T) -> str:
        if not _is_tenant_scoped_field(self.tenant_field):
            tenant_id = self._get_tenant_id(obj)
            return str(tenant_id) if tenant_id is not None else ""
        return require_tenant_context(
            self._get_tenant_id(obj),
            operation=f"{self.name}.insert",
        )

    def insert(self, id: str, obj: T) -> T:
        payload = _to_payload(obj)
        tenant_id = self._require_object_tenant(obj)
        now = _now_iso()
        payload_json = json.dumps(payload, default=_json_default, sort_keys=True)
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO fabric_api_records(table_name, id, tenant_id, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(table_name, tenant_id, id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (self.name, id, tenant_id, payload_json, now, now),
            )
        return obj

    def get(self, id: str, tenant_id: str | None = None) -> T | None:
        normalized_tenant_id = self._require_tenant_scope(tenant_id, operation="get")
        query = "SELECT payload FROM fabric_api_records WHERE table_name = ? AND id = ?"
        params: list[Any] = [self.name, id]
        if _is_tenant_scoped_field(self.tenant_field):
            query += " AND tenant_id = ?"
            params.append(normalized_tenant_id)
        with self._lock:
            row = self._connection.execute(query, params).fetchone()
        if row is None:
            return None
        return self._deserialize(row[0])

    def list(
        self,
        tenant_id: str | None = None,
        filter_fn: Callable[[T], bool] | None = None,
        *,
        allow_system_scope: bool = False,
    ) -> builtins.list[T]:
        normalized_tenant_id = self._require_tenant_scope(tenant_id, operation="list")
        query = "SELECT payload FROM fabric_api_records WHERE table_name = ?"
        params: list[Any] = [self.name]
        if _is_tenant_scoped_field(self.tenant_field):
            # Cross-tenant reads require explicit opt-in via allow_system_scope=True
            # in addition to a reserved keyword — string value alone is not enough.
            if allow_system_scope and normalized_tenant_id in RESERVED_TENANT_KEYWORDS:
                pass  # intentional cross-tenant read
            else:
                query += " AND tenant_id = ?"
                params.append(normalized_tenant_id)
        query += " ORDER BY id"
        with self._lock:
            rows = self._connection.execute(query, params).fetchall()
        items = [self._deserialize(row[0]) for row in rows]
        if filter_fn:
            items = [item for item in items if filter_fn(item)]
        return items

    def update(self, id: str, tenant_id: str | None = None, **fields: Any) -> T | None:
        self._require_tenant_scope(tenant_id, operation="update")
        obj = self.get(id, tenant_id=tenant_id)
        if obj is None:
            return None
        if isinstance(obj, dict):
            obj.update(fields)
            obj["updated_at"] = _now_iso()
        else:
            for key, value in fields.items():
                setattr(obj, key, value)
            if hasattr(obj, "updated_at"):
                setattr(obj, "updated_at", _now_iso())
        self.insert(id, obj)
        return obj

    def delete(self, id: str, tenant_id: str | None = None) -> bool:
        normalized_tenant_id = self._require_tenant_scope(tenant_id, operation="delete")
        obj = self.get(id, tenant_id=tenant_id)
        if obj is None:
            return False
        query = "DELETE FROM fabric_api_records WHERE table_name = ? AND id = ?"
        params: list[Any] = [self.name, id]
        if _is_tenant_scoped_field(self.tenant_field):
            query += " AND tenant_id = ?"
            params.append(normalized_tenant_id)
        with self._lock, self._connection:
            cursor = self._connection.execute(query, params)
        return cursor.rowcount > 0


class AppendOnlySQLiteTable(SQLiteTable[T]):
    def update(self, id: str, tenant_id: str | None = None, **fields: Any) -> T | None:  # noqa: ARG002
        raise PermissionError(f"{self.name} is immutable and cannot be updated")

    def delete(self, id: str, tenant_id: str | None = None) -> bool:  # noqa: ARG002
        raise PermissionError(f"{self.name} is immutable and cannot be deleted")


class InMemoryDatabase:
    """Development-only database facade matching the current repository API."""

    def __init__(self):
        self.accounts = InMemoryTable("accounts", "tenant_id")
        self.stakeholders = InMemoryTable("stakeholders", "tenant_id")
        self.signals = InMemoryTable("signals", "tenant_id")
        self.evidence = InMemoryTable("evidence", "tenant_id")
        self.hypotheses = InMemoryTable("hypotheses", "tenant_id")
        self.drivers = InMemoryTable("drivers", "tenant_id")
        self.levers = InMemoryTable("levers", "tenant_id")
        self.formulas = InMemoryTable("formulas", "tenant_id")
        self.scenarios = InMemoryTable("scenarios", "tenant_id")
        self.roi_calculations = InMemoryTable("roi_calculations", "tenant_id")
        self.business_cases = InMemoryTable("business_cases", "tenant_id")
        self.ground_truth = InMemoryTable("ground_truth", "tenant_id")
        self.agent_runs = InMemoryTable("agent_runs", "tenant_id")
        self.tool_results = InMemoryTable("tool_results", "tenant_id")
        self.review_decisions = InMemoryTable("review_decisions", "tenant_id")
        self.review_requests = InMemoryTable("review_requests", "tenant_id")
        self.review_comments = InMemoryTable("review_comments", "tenant_id")
        self.snapshots = InMemoryTable("snapshots", "tenant_id")
        self.audit_logs = AppendOnlyInMemoryTable("audit_logs", "tenant_id")
        self.value_packs = InMemoryTable("value_packs", "tenant_id")
        self.governance_gates = InMemoryTable("governance_gates", "tenant_id")
        self.users = InMemoryTable("users", "tenant_id")
        self.tenants = InMemoryTable("tenants", "id")
        self.dsar_requests = InMemoryTable("dsar_requests", "tenant_id")
        self.dsar_packages = InMemoryTable("dsar_packages", "tenant_id")



# Backward-compatible aliases for existing tests and imports. New code should use
# the explicit InMemory* names to avoid implying production persistence.
MockTable = InMemoryTable
MockDatabase = InMemoryDatabase


def create_database() -> InMemoryDatabase:
    settings = get_settings()
    if settings.mock_persistence:
        if settings.is_production_like:
            raise ProductionPersistenceNotConfigured(
                "In-memory persistence is disabled in production-like environments."
            )
        return InMemoryDatabase()
    if not settings.database_url:
        raise ProductionPersistenceNotConfigured(
            "database_url must be configured when mock_persistence is false."
        )
    # SQLite is rejected at the Settings level; any URL reaching here is
    # expected to be PostgreSQL. A full PostgreSQL facade will be implemented
    # in a future sprint (API-00x). For now, fail fast with a clear message.
    raise UnsupportedDatabaseURL(
        "PostgreSQL persistence is required but not yet implemented for the standalone API. "
        "Use mock_persistence=true for development and tests, or configure a layer service."
    )


# Lazy proxy to avoid import-time side effects when settings haven't been
# configured yet (e.g. during test module loading).
class _LazyDB:
    """Lazy database proxy that creates the backing instance on first use."""

    _instance: InMemoryDatabase | None = None

    @classmethod
    def _get(cls) -> InMemoryDatabase:
        if cls._instance is None:
            cls._instance = create_database()
        return cls._instance

    def __getattr__(self, name: str):
        return getattr(self._get(), name)

    def __setattr__(self, name: str, value):
        if name == "_instance":
            super().__setattr__(name, value)
        else:
            setattr(self._get(), name, value)

    def __call__(self, *args, **kwargs):
        return self._get()(*args, **kwargs)

    def __iter__(self):
        return iter(self._get())

    def __contains__(self, item):
        return item in self._get()

    def __len__(self):
        return len(self._get())

    def __getitem__(self, key):
        return self._get()[key]

    def __setitem__(self, key, value):
        self._get()[key] = value

    def __delitem__(self, key):
        del self._get()[key]


db: InMemoryDatabase = _LazyDB()  # type: ignore[assignment]

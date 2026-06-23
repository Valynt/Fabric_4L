import json

import pytest

from src.backup.backup_manager import (
    BackupConfig,
    BackupManager,
    BackupRequest,
    BackupType,
    SignedAdminCapability,
)


class _AsyncIter:
    def __init__(self, rows):
        self._rows = iter(rows)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._rows)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class _FakeSession:
    def __init__(self):
        self.queries = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run(self, query, **params):
        self.queries.append((query, params))
        normalized = " ".join(query.split())
        if "RETURN n, labels(n) as types, id(n) as node_id" in normalized:
            return _AsyncIter(
                [{"n": {"id": "n1", "tenant_id": "tenant-a", "name": "A"}, "types": ["Entity"], "node_id": 1}]
            )
        if "RETURN n.id as source_id, m.id as target_id" in normalized:
            return _AsyncIter(
                [{"source_id": "n1", "target_id": "n2", "rel_type": "LINKS_TO", "rel_props": {"tenant_id": "tenant-a"}}]
            )
        return _AsyncIter([])


class _FakeDriver:
    def __init__(self, session):
        self._session = session

    def session(self):
        return self._session


def _capability(**overrides):
    base = {
        "actor_id": "actor-1",
        "role": "platform_admin",
        "tenant_domain": "platform",
        "platform_scope": True,
        "signature": "sig-abc",
        "reason_code": "LEGAL_HOLD",
        "ticket_reference": "CHG-1234",
        "correlation_id": "corr-123",
    }
    base.update(overrides)
    return SignedAdminCapability(**base)


@pytest.mark.asyncio
async def test_default_full_backup_scopes_nodes_and_edges_to_tenant(tmp_path):
    session = _FakeSession()
    manager = BackupManager(
        BackupConfig(backup_directory=str(tmp_path)),
        neo4j_driver=_FakeDriver(session),
    )

    raw = await manager._generate_backup_data(backup_type=BackupType.FULL, tenant_id="tenant-a")
    payload = json.loads(raw.decode("utf-8"))

    assert payload["metadata"]["entity_count"] == 1
    assert payload["metadata"]["relationship_count"] == 1
    assert "MATCH (n {tenant_id: $tenant_id})" in session.queries[0][0]


@pytest.mark.asyncio
async def test_tenant_admin_cannot_trigger_global_export(tmp_path):
    session = _FakeSession()

    async def allow(_cap):
        return True

    async def audit(_event):
        return None


    manager = BackupManager(
        BackupConfig(backup_directory=str(tmp_path)),
        neo4j_driver=_FakeDriver(session),
        global_backup_authorizer=allow,
        immutable_audit_logger=audit,
    )

    with pytest.raises(PermissionError, match="platform_admin role"):
        await manager._generate_backup_data(backup_type=BackupType.FULL, global_export=True, admin_capability=_capability(role="tenant_admin"))


@pytest.mark.asyncio
async def test_service_account_without_admin_scope_cannot_trigger_global_export(tmp_path):
    session = _FakeSession()

    async def allow(_cap):
        return True

    async def audit(_event):
        return None

    manager = BackupManager(
        BackupConfig(backup_directory=str(tmp_path)),
        neo4j_driver=_FakeDriver(session),
        global_backup_authorizer=allow,
        immutable_audit_logger=audit,
    )

    with pytest.raises(PermissionError, match="platform_admin role"):
        await manager.create_backup(
            BackupRequest(
                backup_type=BackupType.FULL,
                global_export=True,
                admin_capability=_capability(role="service_account", tenant_domain="tenant-a"),
            ),
            authenticated_tenant_id="tenant-a",
        )


@pytest.mark.asyncio
async def test_platform_admin_global_export_succeeds_and_emits_before_after_audit(tmp_path):
    session = _FakeSession()
    events = []

    async def allow(cap):
        return cap.signature == "sig-abc"

    async def audit(event):
        events.append(event)

    manager = BackupManager(
        BackupConfig(backup_directory=str(tmp_path)),
        neo4j_driver=_FakeDriver(session),
        global_backup_authorizer=allow,
        immutable_audit_logger=audit,
    )

    response = await manager.create_backup(
        BackupRequest(
            backup_type=BackupType.FULL,
            global_export=True,
            admin_capability=_capability(),
        ),
        authenticated_tenant_id="tenant-a",
    )

    assert response.status.value == "completed"
    assert len(events) == 2
    assert events[0]["stage"] == "before"
    assert events[1]["stage"] == "after"
    assert events[0]["actor_id"] == "actor-1"


@pytest.mark.asyncio
async def test_create_backup_fails_closed_on_tenant_hint_mismatch(tmp_path):
    session = _FakeSession()
    manager = BackupManager(
        BackupConfig(backup_directory=str(tmp_path)),
        neo4j_driver=_FakeDriver(session),
    )

    response = await manager.create_backup(
        BackupRequest(
            backup_type=BackupType.FULL,
            tenant_id="tenant-spoofed",
        ),
        authenticated_tenant_id="tenant-a",
    )

    assert response.status.value == "failed"
    assert response.error is not None
    assert '"code": "TENANT_SCOPE_MISMATCH"' in response.error
    assert '"requested_tenant_hint": "tenant-spoofed"' in response.error


@pytest.mark.asyncio
async def test_create_backup_uses_authenticated_tenant_not_hint(tmp_path):
    session = _FakeSession()
    manager = BackupManager(
        BackupConfig(backup_directory=str(tmp_path)),
        neo4j_driver=_FakeDriver(session),
    )

    response = await manager.create_backup(
        BackupRequest(
            backup_type=BackupType.FULL,
            tenant_id="tenant-a",
        ),
        authenticated_tenant_id="tenant-a",
    )

    assert response.status.value == "completed"
    assert session.queries
    query, params = session.queries[0]
    assert "MATCH (n {tenant_id: $tenant_id})" in query
    assert params["tenant_id"] == "tenant-a"

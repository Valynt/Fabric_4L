"""Regression tests for Neo4j cross-tenant write isolation.

These tests pin the invariant that Layer 3 write paths must never allow a
caller to execute tenant-owned writes using a spoofed ``tenant_id`` parameter.
"""

from __future__ import annotations

import pytest
from src.api.dependencies_tenant import Neo4jTenantSession


class _RecordingSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def run(self, query: str, parameters: dict):
        self.calls.append((query, dict(parameters)))

        class _EmptyResult:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

        return _EmptyResult()


class _RecordingTx:
    def __init__(self, sink: list[tuple[str, dict]]) -> None:
        self._sink = sink

    async def run(self, query: str, parameters: dict):
        self._sink.append((query, dict(parameters)))

        class _EmptyResult:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

        return _EmptyResult()


class _RecordingTxSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def run(self, query: str, parameters: dict):
        self.calls.append((query, dict(parameters)))

        class _EmptyResult:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

        return _EmptyResult()

    async def write_transaction(self, callback):
        return await callback(_RecordingTx(self.calls))


@pytest.mark.security
@pytest.mark.cross_tenant_write
@pytest.mark.asyncio
async def test_neo4j_session_run_prevents_spoofed_tenant_id_in_write_params() -> None:
    """Tenant-bound session writes must pin tenant params to context tenant."""
    session = _RecordingSession()
    tenant_session = Neo4jTenantSession(None, tenant_id="tenant-a", session=session)

    await tenant_session.run(
        "MATCH (n:Entity {id: $id, tenant_id: $tenant_id}) SET n.name = $name RETURN n",
        {"id": "node-1", "name": "safe", "tenant_id": "tenant-b"},
    )

    assert session.calls, "Expected a write query execution"
    _, params = session.calls[-1]
    assert params["tenant_id"] == "tenant-a"
    assert params["_tenant_id"] == "tenant-a"


@pytest.mark.security
@pytest.mark.cross_tenant_write
@pytest.mark.asyncio
async def test_neo4j_write_transaction_prevents_spoofed_tenant_id() -> None:
    """Write transactions must enforce context tenant over caller-supplied tenant_id."""
    session = _RecordingTxSession()
    tenant_session = Neo4jTenantSession(None, tenant_id="tenant-a", session=session)

    await tenant_session.run(
        "MATCH (n:Entity {id: $id, tenant_id: $tenant_id}) "
        "SET n.status = $status RETURN n",
        {"id": "node-1", "status": "updated", "tenant_id": "tenant-b"},
    )

    assert session.calls, "Expected a write query execution"
    _, params = session.calls[-1]
    assert params["tenant_id"] == "tenant-a"
    assert params["_tenant_id"] == "tenant-a"

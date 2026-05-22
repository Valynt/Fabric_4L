"""Hostile regression tests for formula_governance tenant extraction.

Verifies that _get_authenticated_tenant_id raises HTTPException(401) for all
invalid api_key.metadata shapes, and that the Neo4j session is never reached.
"""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from value_fabric.layer3.api.routes.formula_governance import list_pending_approvals


class _Result:
    def __init__(self, records):
        self._records = records

    async def data(self):
        return self._records


class _Neo4jSession:
    def __init__(self):
        self.called = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run(self, query, **kwargs):
        self.called = True
        return _Result([])


# ---------------------------------------------------------------------------
# Happy-path — metadata["tenant_id"] shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_pending_approvals_accepts_valid_tenant_metadata(monkeypatch):
    session = _Neo4jSession()

    async def _session_factory(_tenant_id):
        return session

    monkeypatch.setattr(
        "value_fabric.layer3.api.routes.formula_governance.create_neo4j_tenant_session",
        _session_factory,
    )

    api_key = SimpleNamespace(metadata={"tenant_id": "tenant-a"})
    result = await list_pending_approvals(api_key=api_key)

    assert result == []
    assert session.called


# ---------------------------------------------------------------------------
# Hostile regression — invalid/missing metadata.tenant_id must 401
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "api_key",
    [
        SimpleNamespace(metadata={}),
        SimpleNamespace(metadata={"tenant_id": ""}),
        SimpleNamespace(metadata={"tenant_id": "   "}),  # whitespace-only
        SimpleNamespace(metadata={"tenant_id": None}),
        SimpleNamespace(metadata=None),
        SimpleNamespace(),  # no metadata attr at all
        # Non-dict metadata — previously caused AttributeError (500); must be 401
        SimpleNamespace(metadata="tenant-a"),
        SimpleNamespace(metadata=[]),
        # Non-string tenant_id — must not be coerced; must be 401
        SimpleNamespace(metadata={"tenant_id": True}),
        SimpleNamespace(metadata={"tenant_id": 42}),
        SimpleNamespace(metadata={"tenant_id": ["x"]}),
    ],
    ids=[
        "empty_metadata_dict",
        "empty_string_tenant_id",
        "whitespace_tenant_id",
        "none_tenant_id",
        "none_metadata",
        "missing_metadata_attr",
        "string_metadata",
        "list_metadata",
        "bool_true_tenant_id",
        "int_tenant_id",
        "list_tenant_id",
    ],
)
@pytest.mark.asyncio
async def test_rejects_api_key_without_valid_tenant_metadata(api_key, monkeypatch):
    """_get_authenticated_tenant_id must raise 401 for all invalid tenant shapes.

    Asserts:
    - HTTPException with status_code=401 is raised.
    - The Neo4j session is never called (tenant extraction fails before query).
    """
    session = _Neo4jSession()

    async def _session_factory(_tenant_id):
        return session

    monkeypatch.setattr(
        "value_fabric.layer3.api.routes.formula_governance.create_neo4j_tenant_session",
        _session_factory,
    )

    with pytest.raises(HTTPException) as exc_info:
        await list_pending_approvals(api_key=api_key)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid tenant context"
    assert not session.called, "Neo4j session must not be called when tenant extraction fails"

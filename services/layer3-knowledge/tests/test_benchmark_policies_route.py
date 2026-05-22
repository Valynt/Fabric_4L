from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from value_fabric.layer3.api.routes.benchmarks import list_benchmark_policies


class _Result:
    def __init__(self, records):
        self._records = records

    async def data(self):
        return self._records


class _Neo4jSession:
    def __init__(self, records, expected_tenant_id=None):
        self.records = records
        self.expected_tenant_id = expected_tenant_id
        self.last_tenant_id = None
        self.called = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run(self, query, *, tenant_id):
        self.called = True
        self.last_tenant_id = tenant_id
        if self.expected_tenant_id is not None:
            assert tenant_id == self.expected_tenant_id
        tenant_scoped = [r for r in self.records if r["bp"].get("tenant_id") == tenant_id]
        return _Result(tenant_scoped)


# ---------------------------------------------------------------------------
# Happy-path tests — updated to api_key.metadata["tenant_id"] shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_benchmark_policies_returns_same_tenant_records(monkeypatch):
    tenant_id = "tenant-a"
    records = [
        {
            "bp": {
                "id": "policy-1",
                "policyType": "threshold",
                "name": "A Policy",
                "description": "desc",
                "value": "10",
                "isEnabled": True,
                "scope": "tenant",
                "tenant_id": tenant_id,
            }
        }
    ]
    session = _Neo4jSession(records=records, expected_tenant_id=tenant_id)

    async def _session_factory(_tenant_id):
        return session

    monkeypatch.setattr(
        "value_fabric.layer3.api.routes.benchmarks.create_neo4j_tenant_session",
        _session_factory,
    )

    api_key = SimpleNamespace(metadata={"tenant_id": tenant_id})
    policies = await list_benchmark_policies(api_key=api_key)

    assert len(policies) == 1
    assert policies[0].id == "policy-1"
    assert session.last_tenant_id == tenant_id


@pytest.mark.asyncio
async def test_list_benchmark_policies_returns_empty_for_cross_tenant_records(monkeypatch):
    tenant_id = "tenant-a"
    other_tenant_id = "tenant-b"
    records = [
        {
            "bp": {
                "id": "policy-foreign",
                "policyType": "threshold",
                "name": "Foreign Policy",
                "value": "20",
                "scope": "tenant",
                "tenant_id": other_tenant_id,
            }
        }
    ]
    session = _Neo4jSession(records=records, expected_tenant_id=tenant_id)

    async def _session_factory(_tenant_id):
        return session

    monkeypatch.setattr(
        "value_fabric.layer3.api.routes.benchmarks.create_neo4j_tenant_session",
        _session_factory,
    )

    api_key = SimpleNamespace(metadata={"tenant_id": tenant_id})
    policies = await list_benchmark_policies(api_key=api_key)

    assert policies == []
    assert session.last_tenant_id == tenant_id


@pytest.mark.asyncio
async def test_list_benchmark_policies_passes_required_tenant_parameter_to_neo4j(monkeypatch):
    tenant_id = "tenant-a"
    session = _Neo4jSession(records=[], expected_tenant_id=tenant_id)

    async def _session_factory(_tenant_id):
        return session

    monkeypatch.setattr(
        "value_fabric.layer3.api.routes.benchmarks.create_neo4j_tenant_session",
        _session_factory,
    )

    api_key = SimpleNamespace(metadata={"tenant_id": tenant_id})
    result = await list_benchmark_policies(api_key=api_key)

    assert result == []
    assert session.last_tenant_id == tenant_id


# ---------------------------------------------------------------------------
# Hostile regression tests — invalid/missing metadata.tenant_id must 401
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
    - No fallback to api_key.tenant_id, request body, path, or query params.
    """
    session = _Neo4jSession(records=[])

    async def _session_factory(_tenant_id):
        return session

    monkeypatch.setattr(
        "value_fabric.layer3.api.routes.benchmarks.create_neo4j_tenant_session",
        _session_factory,
    )

    with pytest.raises(HTTPException) as exc_info:
        await list_benchmark_policies(api_key=api_key)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid tenant context"
    assert not session.called, "Neo4j session must not be called when tenant extraction fails"

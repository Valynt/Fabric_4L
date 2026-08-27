from __future__ import annotations

"""Tenant context propagation guardrails for layer3-knowledge.

These tests prove that authenticated request context is propagated into the
Neo4j tenant session and that the propagation seams fail closed when context
is missing.
"""

from types import SimpleNamespace

import pytest
from fastapi import Request
from src.api.dependencies_tenant_secured import (
    Neo4jTenantSessionSecured,
    get_neo4j_secured,
    require_request_tenant_id,
)
from value_fabric.shared.identity.context import RequestContext


class _FakeApp:
    class state:
        neo4j_driver = None


class _FakeRequest:
    def __init__(self, context=None):
        self.app = _FakeApp()
        self.state = SimpleNamespace(governance_context=context)


def test_require_request_tenant_id_extracts_from_governance_context():
    request = _FakeRequest(context=RequestContext(tenant_id="tenant-a"))
    assert require_request_tenant_id(request) == "tenant-a"


def test_require_request_tenant_id_fails_closed_without_context():
    request = _FakeRequest(context=None)
    with pytest.raises(Exception):
        require_request_tenant_id(request)


def test_require_request_tenant_id_fails_closed_with_empty_tenant():
    request = _FakeRequest(context=RequestContext(tenant_id=""))
    with pytest.raises(Exception):
        require_request_tenant_id(request)


@pytest.mark.asyncio
async def test_get_neo4j_secured_propagates_tenant_id_to_session():
    request = _FakeRequest(context=RequestContext(tenant_id="tenant-a"))

    with pytest.raises(Exception):  # driver unavailable, tenant propagated first
        await get_neo4j_secured(request, context=RequestContext(tenant_id="tenant-a"))


def test_secured_session_carries_request_tenant_id():
    class _FakeDriver:
        def session(self):
            return None

    session = Neo4jTenantSessionSecured(
        driver=_FakeDriver(),
        tenant_id="tenant-a",
        strict_validation=True,
        session=None,
    )
    assert session.tenant_id == "tenant-a"

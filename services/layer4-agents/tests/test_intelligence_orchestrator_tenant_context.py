from __future__ import annotations

import pytest
from value_fabric.shared.identity.context import (
    RequestContext,
    clear_current_context,
    set_current_context,
)

from layer4_agents.services.intelligence_orchestrator import _get_tenant_id


@pytest.fixture(autouse=True)
def _clear_context() -> None:
    clear_current_context()
    yield
    clear_current_context()


def test_get_tenant_id_requires_authenticated_context() -> None:
    """Without a request context the orchestrator must fail closed."""
    with pytest.raises(RuntimeError, match="No RequestContext is set"):
        _get_tenant_id()


def test_get_tenant_id_uses_request_context() -> None:
    """When a request context is set, the orchestrator uses its tenant_id."""
    set_current_context(RequestContext(tenant_id="tenant-analytics", user_id="user-analytics"))
    assert _get_tenant_id() == "tenant-analytics"

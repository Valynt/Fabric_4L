from __future__ import annotations

import pytest

from layer4_agents.tools import analytics
from value_fabric.shared.identity.context import (
    RequestContext,
    clear_current_context,
    set_current_context,
)


@pytest.fixture(autouse=True)
def _clear_context() -> None:
    clear_current_context()
    yield
    clear_current_context()


def test_analytics_tenant_id_requires_authenticated_context() -> None:
    with pytest.raises(RuntimeError, match="No RequestContext is set"):
        analytics._get_tenant_id()


def test_analytics_tenant_id_uses_request_context() -> None:
    set_current_context(RequestContext(tenant_id="tenant-analytics", user_id="user-analytics"))

    assert analytics._get_tenant_id() == "tenant-analytics"

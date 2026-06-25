

import pytest

from layer4_agents.config.settings import get_settings
from layer4_agents.tools.knowledge import _NEO4J_PASSWORD, ConfigurationError, _get_driver
from layer4_agents.tools.knowledge_tools import QueryGraphTool


def test_knowledge_module_has_no_literal_password():
    # The module-level password should come from environment, not a hardcoded default.
    assert _NEO4J_PASSWORD != "password"


def test_query_graph_tool_uses_settings_not_literal(monkeypatch):
    monkeypatch.setenv("NEO4J_PASSWORD", "not-the-default-password")
    monkeypatch.delenv("LAYER4_NEO4J_PASSWORD", raising=False)
    get_settings.cache_clear()
    tool = QueryGraphTool()
    assert tool.neo4j_password != "password"
    assert tool.neo4j_password is not None


def test_knowledge_driver_fails_closed_when_password_missing(monkeypatch):
    # Ensure a missing password raises ConfigurationError, not a generic TypeError
    # from the Neo4j driver or, worse, a silent default.
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    monkeypatch.setenv("LAYER4_NEO4J_PASSWORD", "")
    get_settings.cache_clear()

    # Reset the lazy driver singleton so the test does not see a cached instance.
    import layer4_agents.tools.knowledge as knowledge_module

    knowledge_module._DRIVER = None
    with pytest.raises(ConfigurationError) as excinfo:
        _get_driver()

    # Also assert the error message is actionable.
    assert "NEO4J_PASSWORD" in str(excinfo.value)

    # Avoid leaking the unset state to subsequent tests.
    knowledge_module._DRIVER = None
    get_settings.cache_clear()

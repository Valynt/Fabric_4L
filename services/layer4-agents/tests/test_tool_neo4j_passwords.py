
from layer4_agents.tools.knowledge import _NEO4J_PASSWORD
from layer4_agents.tools.knowledge_tools import QueryGraphTool


def test_knowledge_module_has_no_literal_password():
    # The module-level password should come from environment, not a hardcoded default.
    assert _NEO4J_PASSWORD != "password"


def test_query_graph_tool_uses_settings_not_literal():
    tool = QueryGraphTool()
    assert tool.neo4j_password != "password"

import pytest
from unittest.mock import AsyncMock, patch

from layer4_agents.tools.knowledge_tools import TraverseTreeTool, TraverseTreeInput
from layer4_agents.shared.domain.context import TenantContextError

@pytest.mark.asyncio
async def test_traverse_tree_tenant_context_error():
    tool = TraverseTreeTool()
    input_data = TraverseTreeInput(start_entity_id="test-id", path_pattern="*", max_depth=3)

    with patch("layer4_agents.tools.knowledge_tools.tenant_context.get_current_tenant_context") as mock_get_context:
        mock_get_context.side_effect = TenantContextError("Test error")

        result = await tool.execute(input_data)

        assert result.paths == []
        assert result.nodes_discovered == 0
        assert "Tenant context required: Test error. Authentication required." in result.error

from __future__ import annotations

from typing import Any

from layer4_agents.contracts.tool_dto import (
    ToolCategoryListResponse,
    ToolSchemaExample,
    ToolSchemaResponse,
)


def test_tool_schema_response_has_typed_fields() -> None:
    fields = ToolSchemaResponse.model_fields

    assert fields["category"].annotation.__name__ == "ToolCategory"
    assert fields["input_schema"].annotation == dict[str, Any]
    assert fields["output_schema"].annotation == dict[str, Any]
    assert fields["examples"].annotation == list[ToolSchemaExample]
    assert fields["timeout_seconds"].annotation is int
    assert fields["requires_auth"].annotation is bool


def test_tool_category_list_response_shape_and_types() -> None:
    payload = ToolCategoryListResponse.model_validate(
        {"categories": [{"id": "knowledge", "name": "Knowledge"}]}
    )

    dumped = payload.model_dump()
    assert set(dumped.keys()) == {"categories"}
    assert isinstance(dumped["categories"], list)
    assert set(dumped["categories"][0].keys()) == {"id", "name"}
    assert isinstance(dumped["categories"][0]["id"], str)
    assert isinstance(dumped["categories"][0]["name"], str)

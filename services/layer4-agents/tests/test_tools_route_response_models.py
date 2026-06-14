from __future__ import annotations

from layer4_agents.contracts.tool_dto import ToolCategoryListResponse, ToolSchemaResponse


def test_tool_schema_response_has_typed_fields() -> None:
    fields = ToolSchemaResponse.model_fields

    assert fields["category"].annotation.__name__ == "ToolCategory"
    assert str(fields["input_schema"].annotation) == "dict[str, str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]]"
    assert str(fields["output_schema"].annotation) == "dict[str, str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]]"
    assert str(fields["examples"].annotation) == "list[value_fabric.layer4.contracts.tool_dto.ToolSchemaExample]"
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

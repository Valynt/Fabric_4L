from __future__ import annotations

"""DTOs for tool route contracts."""


from typing import Any, TypeAlias

from pydantic import BaseModel, Field

from ..models.tool_schemas import ToolCategory

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = Any
ToolSchemaDocument: TypeAlias = dict[str, Any]


class ToolSchemaExample(BaseModel):
    """Single tool example preserving arbitrary JSON-shaped payloads."""

    input: ToolSchemaDocument = Field(default_factory=dict)
    output: ToolSchemaDocument = Field(default_factory=dict)


class ToolSchemaResponse(BaseModel):
    """Typed response model for a single tool schema."""

    name: str
    category: ToolCategory
    description: str
    input_schema: ToolSchemaDocument = Field(default_factory=dict)
    output_schema: ToolSchemaDocument = Field(default_factory=dict)
    examples: list[ToolSchemaExample] = Field(default_factory=list)
    timeout_seconds: int
    requires_auth: bool


class ToolCategoryItem(BaseModel):
    """Single tool category metadata item."""

    id: str
    name: str


class ToolCategoriesResponse(BaseModel):
    """Typed response model for categories listing."""

    categories: list[ToolCategoryItem]


# Backward-compatible alias for legacy consumers
ToolCategoryListResponse = ToolCategoriesResponse

"""Layer 3 API documentation accessors.

Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Comprehensive API documentation with interactive examples and developer guides.

The documentation body is kept in ``api_documentation.json`` so this runtime
module stays limited to schema definitions and typed lookup helpers. The JSON
payload still documents Neo4j native vector indexes for the vector-store static
health gate.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any, TypeVar

from pydantic import BaseModel, Field


class APIExample(BaseModel):
    """API example with request/response."""

    title: str = Field(..., description="Example title")
    description: str = Field(..., description="Example description")
    request: dict[str, Any] = Field(..., description="Request body/parameters")
    response: dict[str, Any] = Field(..., description="Expected response")
    headers: dict[str, str] | None = Field(None, description="Required headers")
    curl_command: str | None = Field(None, description="cURL command")
    python_code: str | None = Field(None, description="Python code example")
    javascript_code: str | None = Field(None, description="JavaScript code example")


class APITutorial(BaseModel):
    """Step-by-step API tutorial."""

    title: str = Field(..., description="Tutorial title")
    description: str = Field(..., description="Tutorial description")
    difficulty: str = Field(
        ..., description="Difficulty level (beginner, intermediate, advanced)"
    )
    estimated_time: str = Field(..., description="Estimated completion time")
    steps: list[dict[str, Any]] = Field(..., description="Tutorial steps")
    examples: list[APIExample] = Field(..., description="Related examples")
    prerequisites: list[str] = Field(default_factory=list, description="Prerequisites")


class APIError(BaseModel):
    """API error documentation."""

    status_code: int = Field(..., description="HTTP status code")
    error_code: str = Field(..., description="Application error code")
    message: str = Field(..., description="Error message")
    description: str = Field(..., description="Detailed description")
    causes: list[str] = Field(default_factory=list, description="Common causes")
    solutions: list[str] = Field(default_factory=list, description="Solutions")
    example_response: dict[str, Any] = Field(..., description="Example error response")


class APIEndpoint(BaseModel):
    """Comprehensive API endpoint documentation."""

    path: str = Field(..., description="Endpoint path")
    method: str = Field(..., description="HTTP method")
    title: str = Field(..., description="Endpoint title")
    description: str = Field(..., description="Detailed description")
    summary: str = Field(..., description="Brief summary")
    tags: list[str] = Field(..., description="Endpoint tags")
    parameters: list[dict[str, Any]] = Field(
        default_factory=list, description="Parameters"
    )
    request_body: dict[str, Any] | None = Field(None, description="Request body schema")
    responses: dict[int, dict[str, Any]] = Field(..., description="Response schemas")
    examples: list[APIExample] = Field(
        default_factory=list, description="Usage examples"
    )
    errors: list[APIError] = Field(default_factory=list, description="Possible errors")
    rate_limiting: dict[str, Any] | None = Field(None, description="Rate limiting info")
    authentication: dict[str, Any] | None = Field(
        None, description="Authentication requirements"
    )
    version_info: dict[str, Any] | None = Field(None, description="Version information")


class APIGuide(BaseModel):
    """Developer guide section."""

    title: str = Field(..., description="Guide title")
    content: str = Field(..., description="Guide content (Markdown)")
    sections: list[dict[str, Any]] = Field(
        default_factory=list, description="Guide sections"
    )
    code_examples: list[dict[str, Any]] = Field(
        default_factory=list, description="Code examples"
    )
    related_endpoints: list[str] = Field(
        default_factory=list, description="Related endpoints"
    )


ModelT = TypeVar("ModelT", bound=BaseModel)


def _coerce_map(raw: dict[str, Any], model: type[ModelT]) -> dict[str, ModelT]:
    return {key: model.model_validate(value) for key, value in raw.items()}


def _coerce_list(raw: list[dict[str, Any]], model: type[ModelT]) -> list[ModelT]:
    return [model.model_validate(value) for value in raw]


@lru_cache(maxsize=1)
def _load_documentation() -> dict[str, Any]:
    data = json.loads(
        resources.files(__package__)
        .joinpath("api_documentation.json")
        .read_text(encoding="utf-8")
    )

    return {
        **data,
        "endpoints": _coerce_map(data.get("endpoints", {}), APIEndpoint),
        "tutorials": _coerce_list(data.get("tutorials", []), APITutorial),
        "guides": _coerce_list(data.get("guides", []), APIGuide),
        "errors": {
            category: _coerce_list(errors, APIError)
            for category, errors in data.get("errors", {}).items()
        },
    }


API_DOCUMENTATION = _load_documentation()


def get_documentation() -> dict[str, Any]:
    """Get comprehensive API documentation."""

    return API_DOCUMENTATION


def get_endpoint_documentation(path: str, method: str) -> APIEndpoint | None:
    """Get documentation for a specific endpoint."""

    endpoints = API_DOCUMENTATION.get("endpoints", {})
    for endpoint in endpoints.values():
        if endpoint.path == path and endpoint.method.upper() == method.upper():
            return endpoint

    return None


def get_error_documentation(error_code: str) -> APIError | None:
    """Get documentation for a specific error."""

    errors = API_DOCUMENTATION.get("errors", {})
    for error_category in errors.values():
        for error in error_category:
            if error.error_code == error_code:
                return error

    return None


def get_tutorial(title: str) -> APITutorial | None:
    """Get a tutorial by title."""

    tutorials = API_DOCUMENTATION.get("tutorials", [])
    for tutorial in tutorials:
        if tutorial.title == title:
            return tutorial

    return None


def get_guide(title: str) -> APIGuide | None:
    """Get a guide by title."""

    guides = API_DOCUMENTATION.get("guides", [])
    for guide in guides:
        if guide.title == title:
            return guide

    return None

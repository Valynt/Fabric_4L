from __future__ import annotations

"""Contract tests for frontend-consumed Layer 4 endpoints.

Prevents drift between frontend API clients and backend endpoint contracts.
"""


import pytest

import psycopg  # noqa: F401 — mandatory dep; install via layer4-agents[dev] (psycopg[binary])

from fastapi.testclient import TestClient

from layer4_agents.api.main import app


client = TestClient(app)


def _openapi() -> dict:
    return client.get("/openapi.json").json()


def _operation(path: str, method: str) -> dict:
    schema = _openapi()
    return schema["paths"][path][method]


def _resolve_schema(schema: dict, spec: dict) -> dict:
    ref = schema.get("$ref")
    if not ref:
        return schema
    _, _, pointer = ref.partition("#/")
    node = spec
    for part in pointer.split("/"):
        node = node[part]
    return node


def test_frontend_canonical_paths_exist() -> None:
    schema = _openapi()
    assert "/v1/tenants/register" in schema["paths"]
    assert "/v1/tenants/current/settings" in schema["paths"]


def test_frontend_register_response_contract_fields() -> None:
    post_op = _operation("/v1/tenants/register", "post")
    spec = _openapi()
    content = post_op["responses"]["202"]["content"]["application/json"]["schema"]
    props = _resolve_schema(content, spec)["properties"]

    assert {"message", "tenant_id", "verification_required"}.issubset(props.keys())


def test_frontend_settings_response_contract_fields() -> None:
    get_op = _operation("/v1/tenants/current/settings", "get")
    spec = _openapi()
    content = get_op["responses"]["200"]["content"]["application/json"]["schema"]
    props = _resolve_schema(content, spec)["properties"]

    assert {"id", "name", "slug", "status", "tier_id", "settings", "created_at"}.issubset(props.keys())


def test_frontend_alias_routes_marked_deprecated_with_removal_dates() -> None:
    get_alias = _operation("/v1/tenant/settings", "get")
    patch_alias = _operation("/v1/tenant/settings", "patch")
    post_alias = _operation("/v1/auth/register", "post")

    assert get_alias["deprecated"] is True
    assert patch_alias["deprecated"] is True
    assert post_alias["deprecated"] is True

    assert get_alias["x-deprecated-removal-date"] == "2026-08-01"
    assert patch_alias["x-deprecated-removal-date"] == "2026-08-01"
    assert post_alias["x-deprecated-removal-date"] == "2026-07-01"

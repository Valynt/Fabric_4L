from __future__ import annotations

"""Contract tests for the current-user profile endpoints."""

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


def test_users_me_paths_exist() -> None:
    schema = _openapi()
    assert "/v1/users/me" in schema["paths"]
    methods = schema["paths"]["/v1/users/me"]
    assert "get" in methods
    assert "patch" in methods


def test_users_me_get_response_contract_fields() -> None:
    get_op = _operation("/v1/users/me", "get")
    spec = _openapi()
    content = get_op["responses"]["200"]["content"]["application/json"]["schema"]
    props = _resolve_schema(content, spec).get("properties", {})
    assert {"id", "tenant_id", "email", "display_name", "role", "status"}.issubset(
        props.keys()
    )


def test_users_me_patch_request_contract_fields() -> None:
    patch_op = _operation("/v1/users/me", "patch")
    spec = _openapi()
    content = patch_op["requestBody"]["content"]["application/json"]["schema"]
    props = _resolve_schema(content, spec).get("properties", {})
    assert "display_name" in props

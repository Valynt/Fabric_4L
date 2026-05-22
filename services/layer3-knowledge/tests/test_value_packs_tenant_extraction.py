"""Hostile regression tests for value_packs tenant extraction.

Verifies that _tenant_id_from_api_key raises HTTPException(401) for all
invalid api_key.metadata shapes, and returns the correct tenant ID for
valid input.

Contract note: _tenant_id_from_api_key previously raised 403; it now raises
401 to align with benchmarks.py and formula_governance.py. These tests lock
in the new contract.
"""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from value_fabric.layer3.api.routes.value_packs import _tenant_id_from_api_key


# ---------------------------------------------------------------------------
# Happy-path
# ---------------------------------------------------------------------------


def test_returns_tenant_id_for_valid_metadata():
    api_key = SimpleNamespace(metadata={"tenant_id": "tenant-a"})
    assert _tenant_id_from_api_key(api_key) == "tenant-a"


def test_strips_whitespace_from_valid_tenant_id():
    api_key = SimpleNamespace(metadata={"tenant_id": "  tenant-b  "})
    assert _tenant_id_from_api_key(api_key) == "tenant-b"


# ---------------------------------------------------------------------------
# Hostile regression — invalid/missing metadata.tenant_id must 401
# No fallback to api_key.tenant_id, workspace_id, or 'default'.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "api_key",
    [
        SimpleNamespace(metadata={}),
        SimpleNamespace(metadata={"tenant_id": ""}),
        SimpleNamespace(metadata={"tenant_id": "   "}),  # whitespace-only
        SimpleNamespace(metadata={"tenant_id": None}),
        SimpleNamespace(metadata=None),
        SimpleNamespace(),  # no metadata attr at all
        # Non-dict metadata — previously caused AttributeError (500); must be 401
        SimpleNamespace(metadata="tenant-a"),
        SimpleNamespace(metadata=42),
        SimpleNamespace(metadata=[]),
        SimpleNamespace(metadata=["tenant-a"]),
        # Non-string tenant_id — must not be coerced; must be 401
        SimpleNamespace(metadata={"tenant_id": True}),
        SimpleNamespace(metadata={"tenant_id": 42}),
        SimpleNamespace(metadata={"tenant_id": {"id": "x"}}),
        SimpleNamespace(metadata={"tenant_id": ["x"]}),
        # Ensure old api_key.tenant_id / workspace_id attrs are NOT used as fallback
        SimpleNamespace(tenant_id="tenant-a"),
        SimpleNamespace(workspace_id="tenant-a"),
        SimpleNamespace(tenant_id="tenant-a", workspace_id="tenant-a"),
    ],
    ids=[
        "empty_metadata_dict",
        "empty_string_tenant_id",
        "whitespace_tenant_id",
        "none_tenant_id",
        "none_metadata",
        "missing_metadata_attr",
        "string_metadata",
        "int_metadata",
        "empty_list_metadata",
        "list_metadata",
        "bool_true_tenant_id",
        "int_tenant_id",
        "dict_tenant_id",
        "list_tenant_id",
        "old_tenant_id_attr_not_used",
        "old_workspace_id_attr_not_used",
        "both_old_attrs_not_used",
    ],
)
def test_rejects_api_key_without_valid_tenant_metadata(api_key):
    """_tenant_id_from_api_key must raise 401 for all invalid tenant shapes.

    Asserts:
    - HTTPException with status_code=401 is raised.
    - detail is "Invalid tenant context".
    - No fallback to api_key.tenant_id, workspace_id, or the old 'default' value.
    """
    with pytest.raises(HTTPException) as exc_info:
        _tenant_id_from_api_key(api_key)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid tenant context"

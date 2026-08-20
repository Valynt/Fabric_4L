import copy
import datetime
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_PATH = (
    Path(__file__).resolve().parents[5]
    / "contracts"
    / "auth"
    / "authorization-snapshot.schema.json"
)


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    format_checker = FormatChecker()
    if "date-time" not in format_checker.checkers:
        @format_checker.checks("date-time")
        def _validate_datetime(value: object) -> bool:
            if not isinstance(value, str):
                return False
            try:
                datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
                return True
            except (ValueError, TypeError):
                return False
    return Draft202012Validator(schema, format_checker=format_checker)


@pytest.fixture
def valid_snapshot() -> dict[str, object]:
    return {
        "principalId": "user-123",
        "sessionDiscriminator": "session-binding-123",
        "tenant": {"id": "tenant-123", "slug": "acme"},
        "accountScope": {"kind": "account", "accountId": "account-123"},
        "roles": ["tenant_admin"],
        "permissions": ["accounts:read"],
        "entitlements": [
            {"key": "advanced-analytics", "expiresAt": "2026-08-15T00:00:00Z"}
        ],
        "source": "backend",
        "issuedAt": "2026-08-14T18:00:00Z",
        "expiresAt": "2026-08-14T19:00:00Z",
    }


def test_valid_identity_bound_snapshot_matches_contract(
    validator: Draft202012Validator, valid_snapshot: dict[str, object]
) -> None:
    validator.validate(valid_snapshot)


@pytest.mark.parametrize(
    ("mutate", "description"),
    [
        (lambda value: value.pop("principalId"), "missing principal echo"),
        (lambda value: value.pop("sessionDiscriminator"), "missing session echo"),
        (lambda value: value.update(source="client"), "non-backend authority"),
        (lambda value: value.update(roles=[]), "absent authoritative roles"),
        (lambda value: value.update(roles=["unknown_role"]), "unknown role"),
        (
            lambda value: value.update(accountScope={"kind": "account"}),
            "account scope without exact account echo",
        ),
        (
            lambda value: value.update(status="denied"),
            "denial mixed into a success payload",
        ),
        (lambda value: value.update(expiresAt="not-a-time"), "invalid expiry"),
    ],
)
def test_malformed_or_partial_snapshot_fails_closed(
    validator: Draft202012Validator,
    valid_snapshot: dict[str, object],
    mutate,
    description: str,
) -> None:
    candidate = copy.deepcopy(valid_snapshot)
    mutate(candidate)

    assert list(validator.iter_errors(candidate)), description

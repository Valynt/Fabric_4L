"""Behavior tests for generated SDK models that rely on pydantic's EmailStr.

The L4 generated models declare ``admin_email`` as ``EmailStr``, which requires
the ``email-validator`` package at import time. These tests encode both the
allowed behavior (valid emails validate) and the denied behavior (invalid
emails are rejected), guarding the release dependency so the gap cannot remain
latent in the distributable artifact.
"""

from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from valuefabric.generated.l4 import (
    Layer4AgentsTenantsApiRoutesRegistrationRegisterTenantRequest,
)


def test_register_tenant_request_accepts_valid_admin_email() -> None:
    req = Layer4AgentsTenantsApiRoutesRegistrationRegisterTenantRequest(
        name="Acme",
        slug="acme",
        admin_email="ops@acme.example",
    )
    assert req.admin_email == "ops@acme.example"
    assert re.match(r"^[^@]+@[^@]+$", req.admin_email)


def test_register_tenant_request_rejects_invalid_admin_email() -> None:
    with pytest.raises(ValidationError):
        Layer4AgentsTenantsApiRoutesRegistrationRegisterTenantRequest(
            name="Acme",
            slug="acme",
            admin_email="not-an-email",
        )


def test_register_tenant_request_serializes_admin_email() -> None:
    req = Layer4AgentsTenantsApiRoutesRegistrationRegisterTenantRequest(
        name="Acme",
        slug="acme",
        admin_email="ops@acme.example",
    )
    assert req.model_dump()["admin_email"] == "ops@acme.example"
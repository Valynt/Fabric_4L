from __future__ import annotations

import importlib
import os
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from value_fabric.shared.identity import RequestContext, require_authenticated
from value_fabric.shared.identity.middleware import GovernanceMiddleware


def test_require_authenticated_uses_middleware_context_when_post_body_present(monkeypatch):
    """Regression: request bodies must not populate the internal context override.

    FastAPI used to treat ``require_authenticated(context=...)`` as a body
    parameter when the dependency was mounted on POST routes.  A generic JSON body
    could therefore be coerced into ``RequestContext()`` and replace the validated
    ``request.state.governance_context``, yielding ``tenant_id is required`` even
    for valid service-to-service calls.
    """
    secret = "release-smoke-service-auth-secret-with-more-than-32-characters"
    monkeypatch.setenv("SERVICE_AUTH_SECRET", secret)

    app = FastAPI()
    app.add_middleware(GovernanceMiddleware)

    @app.post("/protected")
    async def protected(ctx: RequestContext = Depends(require_authenticated)):
        return ctx.to_dict()

    tenant_id = str(uuid4())
    response = TestClient(app).post(
        "/protected",
        headers={
            "X-Tenant-ID": tenant_id,
            "X-Service-Auth": secret,
            "Content-Type": "application/json",
        },
        json={"name": "release-smoke source payload"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tenant_id"] == tenant_id
    assert body["auth_source"] == "service_account"
    assert body["service_account_id"] == "service-auth-header"


def test_identity_dependency_imports_resolve_to_authoritative_fastapi_helpers():
    """Package exports must resolve to the canonical FastAPI dependency module."""
    dependencies = importlib.reload(
        importlib.import_module("value_fabric.shared.identity.dependencies")
    )
    identity = importlib.reload(importlib.import_module("value_fabric.shared.identity"))

    dependency_path = Path(dependencies.__file__).as_posix()
    assert dependency_path.endswith(
        "packages/shared/src/value_fabric/shared/identity/dependencies.py"
    )
    assert identity.require_authenticated is dependencies.require_authenticated
    assert identity.require_tenant_context is dependencies.require_tenant_context

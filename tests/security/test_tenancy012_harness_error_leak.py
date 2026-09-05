"""V1-TENANCY-012: harness transition must not leak raw exception text.

``POST /v1/harness/runs/{run_id}/transition`` previously forwarded
``str(exc)`` from registry ``ValueError`` into the HTTP ``ValidationError``
message, exposing internal state (and potentially cross-tenant identifiers)
in the response body. The handler must return a static, tenant-safe message.
"""

from __future__ import annotations

import importlib
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest


def _load_harness_module():
    """Import the harness routes module without executing routes/__init__.

    routes/__init__.py pulls in unrelated routers (analysis_scenarios) whose
    import-time behaviour depends on the exact FastAPI version; the harness
    module under test does not need it.
    """
    package_name = "layer4_agents.api.routes"
    if package_name not in sys.modules:
        stub = types.ModuleType(package_name)
        stub.__path__ = [  # mark as package so submodule import works
            str(
                importlib.import_module("layer4_agents.api").__path__[0]
                + "/routes"
            )
        ]
        sys.modules[package_name] = stub
    try:
        return importlib.import_module("layer4_agents.api.routes.harness")
    except AssertionError as exc:
        if "Status code 204" not in str(exc):
            raise
        # Some FastAPI versions reject the pre-existing 204 delete route at
        # import time. Bypass that unrelated assertion for this unit test
        # only; route registration is not under test here.
        import fastapi.routing

        original = fastapi.routing.is_body_allowed_for_status_code
        fastapi.routing.is_body_allowed_for_status_code = lambda _s: True
        try:
            return importlib.import_module("layer4_agents.api.routes.harness")
        finally:
            fastapi.routing.is_body_allowed_for_status_code = original


@pytest.mark.asyncio
async def test_transition_run_does_not_leak_raw_exception_text():
    harness = _load_harness_module()
    from value_fabric.shared.error_handling.exceptions import ValidationError

    secret_detail = "tenant-b-internal-uuid 3fa85f64-5717-4562-b3fc-2c963f66afa6"
    registry = MagicMock()
    registry.transition = AsyncMock(side_effect=ValueError(secret_detail))

    ctx = MagicMock()
    ctx.tenant_id = "tenant-a"

    body = MagicMock()
    body.to_state = MagicMock()
    body.validation_results = None
    body.human_override = False
    body.state_payload = {}

    with pytest.raises(ValidationError) as exc_info:
        await harness.transition_run(
            run_id="run-1", body=body, registry=registry, ctx=ctx
        )

    message = str(exc_info.value)
    assert secret_detail not in message, f"raw exception leaked: {message}"
    assert "3fa85f64" not in message


def test_harness_route_source_has_no_str_exc_in_http_errors():
    """Static guard: no str(exc)/str(e) forwarded into HTTP error messages."""
    import pathlib
    import re

    src = pathlib.Path(
        __file__
    ).resolve().parents[2].joinpath(
        "services/layer4-agents/src/layer4_agents/api/routes/harness.py"
    ).read_text()
    offenders = re.findall(
        r"raise \w*Error\([^)]*str\(\s*(?:exc|e)\s*\)", src, re.DOTALL
    )
    assert not offenders, f"str(exc) forwarded to HTTP errors: {offenders}"

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from value_fabric.shared.identity.context import RequestContext

import layer4_agents.tools.files as module
from layer4_agents.tools.files import TenantRequiredError

TENANT = UUID("550e8400-e29b-41d4-a716-446655440000")


def test_tenant_identity_fails_closed(monkeypatch) -> None:
    context = RequestContext(tenant_id=TENANT)
    assert module._get_tenant_id(context) == str(TENANT)
    monkeypatch.setattr(module, "require_context", lambda: _raise(RuntimeError("missing")))
    with pytest.raises(TenantRequiredError):
        module._get_tenant_id()


def test_path_validation_rejects_absolute_traversal_and_escape(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(module, "TENANT_STORAGE_ROOT", tmp_path)
    assert (
        module._validate_path("folder/file.txt", "tenant")
        == (tmp_path / "tenant/folder/file.txt").resolve()
    )
    assert module._validate_path("../other/file", "tenant") is None
    assert module._validate_path("/etc/passwd", "tenant") is None


@pytest.mark.asyncio
async def test_file_lifecycle_is_tenant_scoped(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(module, "TENANT_STORAGE_ROOT", tmp_path)
    context = RequestContext(tenant_id=TENANT)
    assert await module.write_file("reports/result.txt", "safe", context)
    target = tmp_path / str(TENANT) / "reports/result.txt"
    assert target.read_text() == "safe"
    assert await module.read_file("reports/result.txt", context) == "safe"
    assert await module.read_file("missing.txt", context) is None
    assert await module.read_file("../escape", context) is None
    assert not await module.write_file("../escape", "bad", context)
    assert await module.delete_file("reports/result.txt", context)
    assert not await module.delete_file("reports/result.txt", context)
    assert not await module.delete_file("../escape", context)


@pytest.mark.asyncio
async def test_file_io_errors_return_safe_failure(tmp_path, monkeypatch) -> None:
    context = RequestContext(tenant_id=TENANT)
    bad = tmp_path / "bad"
    monkeypatch.setattr(module, "_validate_path", lambda *_args: bad)
    monkeypatch.setattr(Path, "read_text", lambda *_args, **_kwargs: _raise(OSError("no")))
    monkeypatch.setattr(Path, "exists", lambda *_args: True)
    assert await module.read_file("bad", context) is None
    monkeypatch.setattr(Path, "write_text", lambda *_args, **_kwargs: _raise(OSError("no")))
    assert not await module.write_file("bad", "data", context)
    monkeypatch.setattr(Path, "unlink", lambda *_args: _raise(OSError("no")))
    assert not await module.delete_file("bad", context)


def _raise(error):
    raise error

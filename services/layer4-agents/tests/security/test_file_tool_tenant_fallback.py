"""P0-006: File tool must fail closed when tenant context is missing.

Verifies that _get_tenant_id never falls back to a shared "default" tenant
and that all file operations (read, write, delete) require explicit or
ambient tenant context.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: load tools.files directly without importing tools/__init__.py
# which triggers problematic relative imports in sibling modules.
# ---------------------------------------------------------------------------
spec = importlib.util.spec_from_file_location(
    "_test_files",
    os.path.join(os.path.dirname(__file__), "../../src/tools/files.py"),
)
_test_files = importlib.util.module_from_spec(spec)

# Minimal mocks for value_fabric.shared.identity.context
import types

_vf = types.ModuleType("value_fabric")
_vf.shared = types.ModuleType("value_fabric.shared")
_vf.shared.identity = types.ModuleType("value_fabric.shared.identity")
_vf.shared.identity.context = types.ModuleType("value_fabric.shared.identity.context")


class _FakeRequestContext:
    """Lightweight stand-in for RequestContext."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.user_id = None
        self.org_id = None
        self.workspace_id = None
        self.roles = ["read_only"]
        self.permissions = frozenset()
        self.source = "test"
        self.raw = {}
        self.api_key_id = None
        self.impersonator_id = None
        self.service_account_id = None
        self.service_account_scopes = []

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_any_role(self, *roles: str) -> bool:
        return any(r in self.roles for r in roles)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions


_vf.shared.identity.context.RequestContext = _FakeRequestContext

# require_context will be patched per-test; default raises RuntimeError
_vf.shared.identity.context.require_context = lambda: (_ for _ in ()).throw(
    RuntimeError("no context")
)

sys.modules.setdefault("value_fabric", _vf)
sys.modules.setdefault("value_fabric.shared", _vf.shared)
sys.modules.setdefault("value_fabric.shared.identity", _vf.shared.identity)
sys.modules.setdefault("value_fabric.shared.identity.context", _vf.shared.identity.context)

spec.loader.exec_module(_test_files)

TenantRequiredError = _test_files.TenantRequiredError
_get_tenant_id = _test_files._get_tenant_id
_validate_path = _test_files._validate_path
read_file = _test_files.read_file
write_file = _test_files.write_file
delete_file = _test_files.delete_file
_canonical_files = sys.modules[write_file.__module__]


@pytest.fixture
def temp_storage(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("TENANT_STORAGE_PATH", tmp)
        _test_files.TENANT_STORAGE_ROOT = Path(tmp)
        _canonical_files.TENANT_STORAGE_ROOT = Path(tmp)
        yield Path(tmp)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(tenant_id: str):
    return _FakeRequestContext(tenant_id=tenant_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetTenantId:
    """Tenant ID resolution must fail closed."""

    def test_explicit_context_is_used(self):
        assert _get_tenant_id(_ctx("tenant-explicit")) == "tenant-explicit"

    def test_raises_when_no_context_and_no_ambient(self):
        with pytest.raises(TenantRequiredError):
            _get_tenant_id()

    def test_raises_with_none_tenant_id_in_explicit_context(self):
        with pytest.raises(TenantRequiredError):
            _get_tenant_id(_ctx(""))

    def test_ambient_context_used_when_no_explicit(self):
        ambient = _ctx("tenant-ambient")
        with patch.object(_canonical_files, "require_context", return_value=ambient):
            assert _get_tenant_id() == "tenant-ambient"

    def test_explicit_context_wins_over_ambient(self):
        ambient = _ctx("tenant-ambient")
        explicit = _ctx("tenant-explicit")
        with patch.object(_canonical_files, "require_context", return_value=ambient):
            assert _get_tenant_id(explicit) == "tenant-explicit"


class TestValidatePath:
    """Path traversal and isolation enforcement."""

    def test_rejects_absolute_path(self):
        assert _validate_path("/etc/passwd", "tenant-a") is None

    def test_rejects_traversal_dots(self):
        assert _validate_path("../../etc/passwd", "tenant-a") is None

    def test_rejects_path_escaping_tenant_dir(self, temp_storage):
        assert _validate_path("foo/../../../other-tenant/file.txt", "tenant-a") is None

    def test_accepts_valid_relative_path(self, temp_storage):
        result = _validate_path("documents/report.txt", "tenant-a")
        assert result is not None
        assert str(result).startswith(str(temp_storage / "tenant-a"))

    def test_tenant_directories_are_isolated(self, temp_storage):
        path_a = _validate_path("file.txt", "tenant-a")
        path_b = _validate_path("file.txt", "tenant-b")
        assert path_a != path_b
        assert "tenant-a" in str(path_a)
        assert "tenant-b" in str(path_b)


class TestReadFile:
    """Read operations require tenant context."""

    @pytest.mark.anyio
    async def test_read_file_with_explicit_context(self, temp_storage):
        file_path = _validate_path("doc.txt", "tenant-read")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("hello", encoding="utf-8")

        result = await read_file("doc.txt", context=_ctx("tenant-read"))
        assert result == "hello"

    @pytest.mark.anyio
    async def test_read_file_without_context_raises(self):
        with pytest.raises(TenantRequiredError):
            await read_file("doc.txt")

    @pytest.mark.anyio
    async def test_read_file_invalid_path_returns_none(self, temp_storage):
        result = await read_file("../../etc/passwd", context=_ctx("tenant-read"))
        assert result is None

    @pytest.mark.anyio
    async def test_read_file_not_found_returns_none(self, temp_storage):
        result = await read_file("missing.txt", context=_ctx("tenant-read"))
        assert result is None


class TestWriteFile:
    """Write operations require tenant context."""

    @pytest.mark.anyio
    async def test_write_file_with_explicit_context(self, temp_storage):
        success = await write_file("output.txt", "content", context=_ctx("tenant-write"))
        assert success is True
        assert (temp_storage / "tenant-write" / "output.txt").read_text() == "content"

    @pytest.mark.anyio
    async def test_write_file_without_context_raises(self):
        with pytest.raises(TenantRequiredError):
            await write_file("output.txt", "content")

    @pytest.mark.anyio
    async def test_write_file_invalid_path_returns_false(self, temp_storage):
        success = await write_file("../../etc/passwd", "content", context=_ctx("tenant-write"))
        assert success is False


class TestDeleteFile:
    """Delete operations require tenant context."""

    @pytest.mark.anyio
    async def test_delete_file_with_explicit_context(self, temp_storage):
        file_path = _validate_path("to-delete.txt", "tenant-del")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("bye", encoding="utf-8")

        success = await delete_file("to-delete.txt", context=_ctx("tenant-del"))
        assert success is True
        assert not file_path.exists()

    @pytest.mark.anyio
    async def test_delete_file_without_context_raises(self):
        with pytest.raises(TenantRequiredError):
            await delete_file("to-delete.txt")

    @pytest.mark.anyio
    async def test_delete_file_invalid_path_returns_false(self, temp_storage):
        success = await delete_file("../../etc/passwd", context=_ctx("tenant-del"))
        assert success is False

    @pytest.mark.anyio
    async def test_delete_missing_file_returns_false(self, temp_storage):
        success = await delete_file("missing.txt", context=_ctx("tenant-del"))
        assert success is False


class TestTenantIsolation:
    """Cross-tenant data must never be accessible."""

    @pytest.mark.anyio
    async def test_tenant_a_cannot_read_tenant_b_file(self, temp_storage):
        await write_file("secret.txt", "secret-b", context=_ctx("tenant-b"))

        result = await read_file("secret.txt", context=_ctx("tenant-a"))
        # tenant-a gets None because the file lives under tenant-b's directory
        assert result is None

    @pytest.mark.anyio
    async def test_tenant_a_cannot_write_to_tenant_b_directory_via_traversal(self, temp_storage):
        success = await write_file(
            "../tenant-b/pwned.txt", "evil", context=_ctx("tenant-a")
        )
        assert success is False
        assert not (temp_storage / "tenant-b" / "pwned.txt").exists()

    def test_old_default_fallback_is_removed(self, temp_storage):
        """The 'default' tenant directory must never be created implicitly."""
        with pytest.raises(TenantRequiredError):
            _get_tenant_id()
        assert not (temp_storage / "default").exists()

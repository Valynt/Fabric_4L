"""Tests for the Click-based ``valuepact`` CLI."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import respx
from click.testing import CliRunner
from httpx import Response

from valuefabric.errors import ConnectionError, NotFoundError, ValueFabricError
from valuepact.cli import cli
from valuepact.client import ValuePactApiClient
from valuepact.context import (
    ExecutionContext,
    bind_execution_context,
    get_active_execution_context,
)
from valuepact.errors import map_exception

runner = CliRunner()


@pytest.fixture
def valuepact_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("VALUEPACT_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("VALUEPACT_API_URL", "https://api.example.test")
    monkeypatch.setenv("VALUEPACT_SERVICE_TOKEN", "secret-token")
    monkeypatch.setenv("VALUEPACT_TENANT_ID", "tenant_123")
    monkeypatch.setenv("VALUEPACT_ENVIRONMENT", "staging")
    return tmp_path


class FakeClient:
    instances: list[FakeClient] = []

    def __init__(
        self,
        *,
        api_url: str,
        token: str,
        request_id: str | None = None,
        command_name: str | None = None,
        cli_version: str | None = None,
    ) -> None:
        self.api_url = api_url
        self.token = token
        self.request_id = request_id
        self.command_name = command_name
        self.cli_version = cli_version
        self.closed = False
        self.calls: list[tuple[str, object]] = []
        type(self).instances.append(self)

    def close(self) -> None:
        self.closed = True

    def identity(self) -> dict[str, object]:
        self.calls.append(("identity", None))
        return {
            "actor_id": "svc_123",
            "actor_type": "service_account",
            "scopes": ["valuepact:read", "valuepact:workspace:execute"],
        }

    def verify_tenant_access(self, tenant_id: str, *, scopes: set[str]) -> dict[str, object]:
        self.calls.append(("verify_tenant_access", {"tenant_id": tenant_id, "scopes": scopes}))
        return {"authorized": True, "scopes": sorted(scopes)}

    def list_workspaces(self, tenant_id: str) -> list[dict[str, str]]:
        assert get_active_execution_context() is not None
        self.calls.append(("list_workspaces", tenant_id))
        return [{"workspace_id": "workspace_456", "tenant_id": tenant_id, "status": "ready"}]

    def execute_workspace(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        request_id: str,
        actor_id: str,
        input_payload: dict[str, object],
        dry_run: bool,
    ) -> dict[str, object]:
        assert get_active_execution_context() is not None
        self.calls.append(("execute_workspace", workspace_id))
        return {
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "execution_id": "exec_789",
            "status": "started",
            "request_id": request_id,
            "actor_id": actor_id,
            "dry_run": dry_run,
            "input": input_payload,
        }

    def health(self) -> dict[str, str]:
        return {"status": "ok"}


class DenyingClient(FakeClient):
    instances: list[DenyingClient] = []

    def verify_tenant_access(self, tenant_id: str, *, scopes: set[str]) -> dict[str, object]:
        self.calls.append(("verify_tenant_access", {"tenant_id": tenant_id, "scopes": scopes}))
        return {"authorized": False, "scopes": []}


class InterruptingClient(FakeClient):
    instances: list[InterruptingClient] = []

    def list_workspaces(self, tenant_id: str) -> list[dict[str, str]]:
        assert get_active_execution_context() is not None
        raise KeyboardInterrupt


def test_context_use_stores_non_secret_profile(valuepact_env: Path) -> None:
    result = runner.invoke(
        cli,
        [
            "--json",
            "context",
            "use",
            "--tenant-id",
            "tenant_abc",
            "--environment",
            "production",
            "--api-url",
            "https://api.prod.example",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    config = (valuepact_env / "config.toml").read_text(encoding="utf-8")
    assert "tenant_abc" in config
    assert "https://api.prod.example" in config
    assert "secret-token" not in config
    assert "api_key" not in config


def test_auth_login_verifies_identity_and_stores_only_metadata(valuepact_env: Path) -> None:
    FakeClient.instances = []
    with patch("valuepact.cli.ValuePactApiClient", FakeClient):
        result = runner.invoke(
            cli,
            ["auth", "login", "--api-url", "https://api.login.example", "--json"],
        )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["data"]["actor_id"] == "svc_123"
    config = (valuepact_env / "config.toml").read_text(encoding="utf-8")
    assert "svc_123" in config
    assert "https://api.login.example" in config
    assert "secret-token" not in config
    assert FakeClient.instances[0].command_name == "valuepact auth login"
    assert FakeClient.instances[0].cli_version is not None


def test_workspace_list_verifies_tenant_and_cleans_context(valuepact_env: Path) -> None:
    FakeClient.instances = []
    with patch("valuepact.cli.ValuePactApiClient", FakeClient):
        result = runner.invoke(cli, ["--json", "workspace", "list"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["meta"]["tenant_id"] == "tenant_123"
    assert payload["data"][0]["workspace_id"] == "workspace_456"
    assert get_active_execution_context() is None
    calls = FakeClient.instances[0].calls
    assert calls[0][0] == "identity"
    assert calls[1][0] == "verify_tenant_access"
    assert calls[2] == ("list_workspaces", "tenant_123")
    assert FakeClient.instances[0].closed is True
    assert FakeClient.instances[0].command_name == "valuepact workspace list"
    assert FakeClient.instances[0].cli_version is not None


def test_command_local_json_and_context_options_override_environment(valuepact_env: Path) -> None:
    FakeClient.instances = []
    with patch("valuepact.cli.ValuePactApiClient", FakeClient):
        result = runner.invoke(
            cli,
            [
                "workspace",
                "execute",
                "--workspace-id",
                "workspace_456",
                "--yes",
                "--json",
                "--tenant-id",
                "tenant_cli",
                "--environment",
                "production",
            ],
        )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["meta"]["tenant_id"] == "tenant_cli"
    assert payload["meta"]["environment"] == "production"
    assert payload["data"]["tenant_id"] == "tenant_cli"
    assert FakeClient.instances[0].calls[1] == (
        "verify_tenant_access",
        {"tenant_id": "tenant_cli", "scopes": {"valuepact:workspace:execute"}},
    )


def test_authorization_denied_uses_stable_exit_and_cleans_context(valuepact_env: Path) -> None:
    DenyingClient.instances = []
    with patch("valuepact.cli.ValuePactApiClient", DenyingClient):
        result = runner.invoke(cli, ["workspace", "list", "--json"])

    assert result.exit_code == 4
    payload = json.loads(result.stderr)
    assert payload["error"]["code"] == "AUTHORIZATION_DENIED"
    assert get_active_execution_context() is None


def test_interruption_uses_stable_exit_and_cleans_context(valuepact_env: Path) -> None:
    InterruptingClient.instances = []
    with patch("valuepact.cli.ValuePactApiClient", InterruptingClient):
        result = runner.invoke(cli, ["workspace", "list", "--json"])

    assert result.exit_code == 130
    payload = json.loads(result.stderr)
    assert payload["error"]["code"] == "INTERRUPTED"
    assert get_active_execution_context() is None


def test_workspace_execute_requires_confirmation_for_mutation(valuepact_env: Path) -> None:
    FakeClient.instances = []
    with patch("valuepact.cli.ValuePactApiClient", FakeClient):
        result = runner.invoke(
            cli,
            ["--json", "workspace", "execute", "--workspace-id", "workspace_456"],
        )

    assert result.exit_code == 2
    payload = json.loads(result.stderr)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
    assert get_active_execution_context() is None


def test_workspace_execute_json_success_with_yes_and_input(
    tmp_path: Path,
    valuepact_env: Path,
) -> None:
    input_file = tmp_path / "input.json"
    input_file.write_text('{"answer": 42}', encoding="utf-8")
    FakeClient.instances = []
    with patch("valuepact.cli.ValuePactApiClient", FakeClient):
        result = runner.invoke(
            cli,
            [
                "--json",
                "workspace",
                "execute",
                "--workspace-id",
                "workspace_456",
                "--input",
                str(input_file),
                "--yes",
            ],
        )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["data"]["execution_id"] == "exec_789"
    assert payload["data"]["input"] == {"answer": 42}
    assert payload["data"]["actor_id"] == "svc_123"
    assert payload["meta"]["actor_id"] == "svc_123"
    assert get_active_execution_context() is None


def test_missing_token_uses_stable_authentication_exit(valuepact_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VALUEPACT_SERVICE_TOKEN")

    result = runner.invoke(cli, ["--json", "workspace", "list"])

    assert result.exit_code == 3
    payload = json.loads(result.stderr)
    assert payload["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert "secret-token" not in result.stderr


def test_error_mapping_keeps_stable_exit_codes() -> None:
    assert map_exception(PermissionError("denied")).exit_code == 4
    assert map_exception(NotFoundError("missing")).exit_code == 6
    retryable = map_exception(ConnectionError("network down"))
    assert retryable.exit_code == 7
    assert retryable.retryable is True
    assert map_exception(ValueFabricError("domain rule")).exit_code == 5


@respx.mock
def test_api_adapter_uses_existing_identity_and_workflow_contracts() -> None:
    identity_route = respx.get("https://api.example.test/v1/users/me").mock(
        return_value=Response(
            200,
            json={
                "id": "user_123",
                "tenant_id": "tenant_123",
                "role": "operator",
                "scopes": ["valuepact:read"],
            },
        )
    )
    execute_route = respx.post("https://api.example.test/v1/workflows").mock(
        return_value=Response(200, json={"workflow_instance_id": "wf_123", "status": "scheduled"})
    )

    client = ValuePactApiClient(
        api_url="https://api.example.test",
        token="secret-token",
        request_id="req_123",
        command_name="valuepact workspace execute",
        cli_version="0.1.0",
    )
    try:
        identity = client.identity()
        verification = client.verify_tenant_access("tenant_123", scopes={"valuepact:workspace:execute"})
        result = client.execute_workspace(
            tenant_id="tenant_123",
            workspace_id="roi_calculator",
            request_id="req_123",
            actor_id=identity["actor_id"],
            input_payload={"answer": 42},
            dry_run=False,
        )
    finally:
        client.close()

    assert identity_route.called
    assert execute_route.called
    assert identity["actor_id"] == "user_123"
    assert verification["authorized"] is True
    request = execute_route.calls.last.request
    assert request.headers["x-request-id"] == "req_123"
    assert request.headers["x-valuepact-command"] == "valuepact workspace execute"
    assert request.headers["x-valuepact-cli-version"] == "0.1.0"
    assert json.loads(request.content) == {
        "workflow_type": "roi_calculator",
        "tenant_id": "tenant_123",
        "user_id": "user_123",
        "inputs": {"answer": 42},
        "priority": "NORMAL",
        "input": {"answer": 42},
        "workflow_id": "req_123",
        "request_id": "req_123",
    }
    assert result["workflow_instance_id"] == "wf_123"


@respx.mock
def test_api_adapter_denies_mismatched_tenant_before_workflow_execution() -> None:
    respx.get("https://api.example.test/v1/users/me").mock(
        return_value=Response(
            200,
            json={"id": "user_123", "tenant_id": "tenant_123", "role": "operator"},
        )
    )

    client = ValuePactApiClient(api_url="https://api.example.test", token="secret-token")
    try:
        with pytest.raises(PermissionError):
            client.verify_tenant_access("tenant_other", scopes={"valuepact:workspace:execute"})
    finally:
        client.close()


def test_context_manager_restores_nested_and_failed_contexts() -> None:
    outer = ExecutionContext(
        environment="staging",
        tenant_id="tenant_a",
        actor_id="actor_a",
        actor_type="user",
        scopes=frozenset({"read"}),
        request_id="req_outer",
    )
    inner = ExecutionContext(
        environment="production",
        tenant_id="tenant_b",
        actor_id="actor_b",
        actor_type="service_account",
        scopes=frozenset({"execute"}),
        request_id="req_inner",
    )

    with pytest.raises(RuntimeError), bind_execution_context(outer):
        assert get_active_execution_context() == outer
        with bind_execution_context(inner):
            assert get_active_execution_context() == inner
            raise RuntimeError("boom")

    assert get_active_execution_context() is None


def test_async_contexts_do_not_leak_between_tasks() -> None:
    async def read_context(context: ExecutionContext) -> str:
        with bind_execution_context(context):
            await asyncio.sleep(0)
            active = get_active_execution_context()
            assert active is not None
            return active.tenant_id

    first = ExecutionContext(
        environment="staging",
        tenant_id="tenant_a",
        actor_id="actor_a",
        actor_type="user",
        scopes=frozenset(),
        request_id="req_a",
    )
    second = ExecutionContext(
        environment="staging",
        tenant_id="tenant_b",
        actor_id="actor_b",
        actor_type="user",
        scopes=frozenset(),
        request_id="req_b",
    )

    async def run() -> list[str]:
        return await asyncio.gather(read_context(first), read_context(second))

    assert asyncio.run(run()) == [
        "tenant_a",
        "tenant_b",
    ]
    assert get_active_execution_context() is None

"""Tests for the ``vf`` CLI using ``CliRunner``."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import UUID

import pytest
from typer.testing import CliRunner

from valuefabric.cli import config as config_mod
from valuefabric.cli.auth import _is_jwt
from valuefabric.cli.main import app
from valuefabric.errors import ConfigurationError
from valuefabric.models import (
    APIKey,
    APIKeyCreateResult,
    FeatureFlag,
    HealthResponse,
    ModelVersion,
    Tenant,
    User,
    WorkflowCreateResponse,
    WorkflowTypeInfo,
)

runner = CliRunner()


@pytest.fixture(autouse=True)
def mock_config(tmp_path: Path) -> Iterator[None]:
    """Provide a temporary CLI config so commands can load credentials."""
    config = {
        "active_profile": "default",
        "profiles": {
            "default": {
                "base_url": "https://api.example.com",
                "api_key": "test-key",
            }
        },
    }
    with patch("valuefabric.cli.config.CONFIG_FILE", tmp_path / "config.toml"):
        config_mod._save_config(config)
        yield


class TestAuthCommands:
    @pytest.mark.parametrize(
        ("token", "expected"),
        [
            (
                "eyJhbGciOiJIUzI1NiIsInR5cCI.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
                True,
            ),
            ("eyJhb.eyJzd.SflKxw", True),
            ("header.payload.signature", True),
            ("header.payload", False),
            ("header.payload.signature.extra", False),
            ("", False),
            ("header..signature", False),
            ("just_a_random_string", False),
        ],
    )
    def test_is_jwt(self, token: str, expected: bool) -> None:
        assert _is_jwt(token) is expected


class TestConfigCommands:
    def test_token_expiration_warns_for_expired_timestamp(self) -> None:
        with patch("valuefabric.cli.config.rich_print") as mock_print:
            config_mod._check_token_expiration({"jwt_expires_at": "0"}, "default")

        mock_print.assert_called_once()
        warning = mock_print.call_args.args[0]
        assert "JWT token for profile 'default' has expired" in warning
        assert "vf auth login" in warning

    def test_token_expiration_does_not_warn_for_future_timestamp(self) -> None:
        with patch("valuefabric.cli.config.rich_print") as mock_print:
            config_mod._check_token_expiration({"jwt_expires_at": "99999999999"}, "default")

        mock_print.assert_not_called()

    @pytest.mark.parametrize(
        "profile_config",
        [
            {},
            {"jwt_expires_at": None},
            {"jwt_expires_at": ""},
            {"jwt_expires_at": "not-a-timestamp"},
        ],
    )
    def test_token_expiration_ignores_missing_or_invalid_timestamp(
        self, profile_config: dict[str, str | None]
    ) -> None:
        with patch("valuefabric.cli.config.rich_print") as mock_print:
            config_mod._check_token_expiration(profile_config, "default")

        mock_print.assert_not_called()

    def test_show_config(self, mock_config: None) -> None:
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "Active profile" in result.output

    def test_set_url(self, mock_config: None) -> None:
        result = runner.invoke(app, ["config", "set-url", "https://new.example.com"])
        assert result.exit_code == 0
        assert "Base URL set" in result.output

    def test_use_profile(self, mock_config: None) -> None:
        result = runner.invoke(app, ["config", "use-profile", "prod"])
        assert result.exit_code == 0
        assert "Active profile set to 'prod'" in result.output


class TestTenantCommands:
    def test_list_tenants(self, mock_config: None) -> None:
        tenant = Tenant(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            name="Acme",
            slug="acme",
            status="active",
            created_at=datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
            updated_at=datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
        )
        with patch("valuefabric.cli.tenants.get_client") as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.list_tenants.return_value = [tenant]
            result = runner.invoke(app, ["tenants", "list"])
            assert result.exit_code == 0
            assert "Acme" in result.output

    def test_get_tenant_json(self, mock_config: None) -> None:
        tenant = Tenant(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            name="Acme",
            slug="acme",
            status="active",
            created_at=datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
            updated_at=datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
        )
        with patch("valuefabric.cli.tenants.get_client") as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.get_tenant.return_value = tenant
            result = runner.invoke(
                app, ["tenants", "get", "11111111-1111-1111-1111-111111111111", "--json"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["name"] == "Acme"


class TestUserCommands:
    def test_list_users(self, mock_config: None) -> None:
        user = User(
            id=UUID("22222222-2222-2222-2222-222222222222"),
            tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
            email="alice@example.com",
            role="analyst",
            status="active",
            created_at=datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
            updated_at=datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
        )
        with patch("valuefabric.cli.users.get_client") as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.list_users.return_value = [user]
            result = runner.invoke(app, ["users", "list"])
            assert result.exit_code == 0
            assert "alice@examp" in result.output

    def test_invite_user(self, mock_config: None) -> None:
        user = User(
            id=UUID("33333333-3333-3333-3333-333333333333"),
            tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
            email="bob@example.com",
            role="analyst",
            status="invited",
            created_at=datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
            updated_at=datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
        )
        with patch("valuefabric.cli.users.get_client") as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.invite_user.return_value = user
            result = runner.invoke(app, ["users", "invite", "bob@example.com", "--role", "analyst"])
            assert result.exit_code == 0
            assert "bob@example.com" in result.output


class TestApiKeyCommands:
    def test_list_api_keys(self, mock_config: None) -> None:
        key = APIKey(
            key_id="vf_abc",
            tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
            name="test-key",
            prefix="vf_ab",
            role="analyst",
            permissions=frozenset(),
            enabled=True,
            created_at=datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
        )
        with patch("valuefabric.cli.api_keys.get_client") as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.list_api_keys.return_value = [key]
            result = runner.invoke(app, ["api-keys", "list"])
            assert result.exit_code == 0
            assert "test-key" in result.output

    def test_create_api_key(self, mock_config: None) -> None:
        result_obj = APIKeyCreateResult(
            key_id="vf_def",
            tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
            name="new-key",
            api_key="vf_def_secret",
            prefix="vf_de",
            role="analyst",
            permissions=frozenset(),
            created_at=datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
        )
        with patch("valuefabric.cli.api_keys.get_client") as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.create_api_key.return_value = result_obj
            result = runner.invoke(app, ["api-keys", "create", "new-key"])
            assert result.exit_code == 0
            assert "new-key" in result.output


class TestWorkflowCommands:
    def test_list_workflows(self, mock_config: None) -> None:
        wf = WorkflowTypeInfo(
            type="roi_calculator",
            name="ROI Calculator",
            description="Calculate ROI",
        )
        with patch("valuefabric.cli.workflows.get_client") as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.list_workflow_types.return_value = [wf]
            result = runner.invoke(app, ["workflows", "list"])
            assert result.exit_code == 0
            assert "roi_calculator" in result.output

    def test_execute_workflow(self, mock_config: None) -> None:
        with patch("valuefabric.cli.workflows.get_client") as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.execute_workflow.return_value = WorkflowCreateResponse(
                workflow_instance_id="wf-2", status="scheduled"
            )
            result = runner.invoke(
                app,
                [
                    "workflows",
                    "execute",
                    "roi_calculator",
                ],
            )
            assert result.exit_code == 0
            assert "wf-2" in result.output


class TestModelCommands:
    def test_list_models(self, mock_config: None) -> None:
        model = ModelVersion(
            id=UUID("44444444-4444-4444-4444-444444444444"),
            tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
            provider="openai",
            model_name="gpt-4",
            model_version="1.0",
            stage="dev",
            config={},
            created_at="2024-01-01T00:00:00Z",
        )
        with patch("valuefabric.cli.models.get_client") as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.list_models.return_value = [model]
            result = runner.invoke(app, ["models", "list"])
            assert result.exit_code == 0
            assert "gpt-4" in result.output

    def test_promote_model(self, mock_config: None) -> None:
        model = ModelVersion(
            id=UUID("44444444-4444-4444-4444-444444444444"),
            tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
            provider="openai",
            model_name="gpt-4",
            model_version="1.0",
            stage="staging",
            config={},
            created_at="2024-01-01T00:00:00Z",
        )
        with patch("valuefabric.cli.models.get_client") as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.promote_model.return_value = model
            result = runner.invoke(
                app,
                ["models", "promote", "44444444-4444-4444-4444-444444444444", "--to", "staging"],
            )
            assert result.exit_code == 0
            assert "staging" in result.output


class TestFeatureFlagCommands:
    def test_list_flags(self, mock_config: None) -> None:
        flag = FeatureFlag(
            id=UUID("55555555-5555-5555-5555-555555555555"),
            flag_key="new_ui",
            enabled=True,
            rollout_percentage=100,
            metadata={},
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        with patch("valuefabric.cli.flags.get_client") as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.list_feature_flags.return_value = [flag]
            result = runner.invoke(app, ["feature-flags", "list"])
            assert result.exit_code == 0
            assert "new_ui" in result.output

    def test_list_flags_with_options(self, mock_config: None) -> None:
        flag = FeatureFlag(
            id=UUID("55555555-5555-5555-5555-555555555555"),
            flag_key="new_ui",
            enabled=True,
            rollout_percentage=100,
            metadata={},
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        with patch("valuefabric.cli.flags.get_client") as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.list_feature_flags.return_value = [flag]
            result = runner.invoke(
                app, ["feature-flags", "list", "--limit", "50", "--offset", "10", "--json"]
            )
            assert result.exit_code == 0
            mock_client.list_feature_flags.assert_called_once_with(limit=50, offset=10)
            data = json.loads(result.output)
            assert isinstance(data, list)
            assert data[0]["flag_key"] == "new_ui"

    def test_set_flag(self, mock_config: None) -> None:
        flag = FeatureFlag(
            id=UUID("55555555-5555-5555-5555-555555555555"),
            flag_key="new_ui",
            enabled=False,
            rollout_percentage=0,
            metadata={},
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        with patch("valuefabric.cli.flags.get_client") as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.set_feature_flag.return_value = flag
            result = runner.invoke(
                app, ["feature-flags", "set", "new_ui", "--disabled", "--rollout", "0"]
            )
            assert result.exit_code == 0
            assert "False" in result.output

    def test_set_flag_json(self, mock_config: None) -> None:
        flag = FeatureFlag(
            id=UUID("55555555-5555-5555-5555-555555555555"),
            flag_key="new_ui",
            enabled=False,
            rollout_percentage=0,
            metadata={},
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        with patch("valuefabric.cli.flags.get_client") as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.set_feature_flag.return_value = flag
            result = runner.invoke(app, ["feature-flags", "set", "new_ui", "--disabled", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["flag_key"] == "new_ui"
            assert data["enabled"] is False


class TestHealthCommand:
    def test_health(self, mock_config: None) -> None:
        health = HealthResponse(
            status="healthy",
            service="layer4-agents",
            version="0.2.0",
            timestamp="2024-01-01T00:00:00Z",
            executor_ready=True,
            uptime_seconds=123.0,
            dependencies=[],
            metrics={},
        )
        with patch("valuefabric.cli.health.get_client") as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.health.return_value = health
            result = runner.invoke(app, ["health"])
            assert result.exit_code == 0
            assert "healthy" in result.output


class TestConfigErrorHandling:
    def test_parse_toml_value_string_fallback(self) -> None:
        assert config_mod._parse_toml_value("not_a_number") == "not_a_number"

    def test_load_profile_toml_invalid_profiles(self) -> None:
        with pytest.raises(ValueError, match="profiles must be a table"):
            config_mod._load_profile_toml("profiles = 1\n[profiles.default]")

    def test_load_profile_toml_missing_equals(self) -> None:
        with pytest.raises(ValueError, match="invalid syntax at line 1"):
            config_mod._load_profile_toml("invalid_line")

    def test_load_config_corrupted_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        corrupted_file = tmp_path / "corrupted.toml"
        corrupted_file.write_text("invalid_line", encoding="utf-8")
        monkeypatch.setattr(config_mod, "CONFIG_FILE", corrupted_file)
        with pytest.raises(ConfigurationError, match="Config file is corrupted"):
            config_mod._load_config()

    def test_load_config_missing_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        missing_file = tmp_path / "missing.toml"
        monkeypatch.setattr(config_mod, "CONFIG_FILE", missing_file)
        assert config_mod._load_config() == {}

    def test_load_config_read_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        error_file = tmp_path / "error.toml"
        error_file.write_text("", encoding="utf-8")
        monkeypatch.setattr(config_mod, "CONFIG_FILE", error_file)

        def mock_load_profile_toml(*args: Any, **kwargs: Any) -> Any:
            raise ValueError("mock error")

        monkeypatch.setattr(config_mod, "_load_profile_toml", mock_load_profile_toml)

        with pytest.raises(ConfigurationError) as exc_info:
            config_mod._load_config()

        assert "Config file is corrupted" in str(exc_info.value)
        assert "mock error" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, ValueError)

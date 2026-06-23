"""Security regression tests for P1-004: Sentry Integration.

Validates that:
- sentry-sdk is declared in all service pyproject.toml files
- create_fabric_app initializes Sentry when SENTRY_DSN is present
- Frontend main.tsx imports and initializes Sentry
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest


class TestServiceDependencies:
    """All Python services must declare sentry-sdk in dependencies."""

    def test_all_services_have_sentry_sdk(self) -> None:
        services_dir = Path("services")
        missing: list[str] = []
        for pyproject in sorted(services_dir.glob("*/pyproject.toml")):
            content = pyproject.read_text(encoding="utf-8")
            if "sentry-sdk" not in content:
                missing.append(pyproject.parent.name)
        assert not missing, f"Missing sentry-sdk in: {missing}"


class TestFabricAppSentryInitialization:
    """create_fabric_app must conditionally initialize Sentry."""

    def _source(self) -> str:
        return Path(
            "packages/shared/src/value_fabric/shared/fastapi_framework/app.py"
        ).read_text(encoding="utf-8")

    def test_uses_shared_scrubbed_initializer(self) -> None:
        src = self._source()
        assert "from value_fabric.shared.observability.sentry_init import init_sentry" in src
        assert "app.state.sentry_enabled = init_sentry(" in src
        assert "service_name=service_name" in src
        assert "release=version" in src

    def test_shared_initializer_reads_sentry_dsn_from_env(self) -> None:
        src = Path(
            "packages/shared/src/value_fabric/shared/observability/sentry_init.py"
        ).read_text(encoding="utf-8")
        assert 'os.environ.get("SENTRY_DSN"' in src
        assert "before_send=_scrub_event" in src
        assert "before_send_transaction=_scrub_event" in src
        assert "send_default_pii=False" in src

    def test_shared_initializer_configures_sample_rates_and_tags(self) -> None:
        src = Path(
            "packages/shared/src/value_fabric/shared/observability/sentry_init.py"
        ).read_text(encoding="utf-8")
        assert "sample_rate = 0.1 if environment == \"production\" else 1.0" in src
        assert "traces_sample_rate=sample_rate" in src
        assert "profiles_sample_rate=min(sample_rate, 0.1)" in src
        assert 'sentry_sdk.set_tag("service", service_name)' in src

    def test_sets_release_and_environment(self) -> None:
        app_src = self._source()
        src = Path(
            "packages/shared/src/value_fabric/shared/observability/sentry_init.py"
        ).read_text(encoding="utf-8")
        assert "release=version" in app_src
        assert "release=release" in src
        assert 'os.environ.get("ENVIRONMENT"' in src

    def test_shared_initializer_noops_without_dsn(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from value_fabric.shared.observability.sentry_init import init_sentry

        monkeypatch.delenv("SENTRY_DSN", raising=False)
        assert init_sentry(service_name="test-service", release="test-release") is False

    def test_shared_initializer_scrubs_dummy_sdk_event(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from value_fabric.shared.observability.sentry_init import init_sentry

        captured: dict[str, object] = {}

        sentry_sdk = types.ModuleType("sentry_sdk")
        sentry_sdk.init = lambda **kwargs: captured.update(kwargs)  # type: ignore[attr-defined]

        def set_tag(key: str, value: object) -> None:
            tags = captured.setdefault("tags", {})
            assert isinstance(tags, dict)
            tags[key] = value

        sentry_sdk.set_tag = set_tag  # type: ignore[attr-defined]

        fastapi_mod = types.ModuleType("sentry_sdk.integrations.fastapi")
        fastapi_mod.FastApiIntegration = type("FastApiIntegration", (), {})
        starlette_mod = types.ModuleType("sentry_sdk.integrations.starlette")
        starlette_mod.StarletteIntegration = type("StarletteIntegration", (), {})
        sqlalchemy_mod = types.ModuleType("sentry_sdk.integrations.sqlalchemy")
        sqlalchemy_mod.SqlalchemyIntegration = type("SqlalchemyIntegration", (), {})

        monkeypatch.setitem(sys.modules, "sentry_sdk", sentry_sdk)
        monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.fastapi", fastapi_mod)
        monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.starlette", starlette_mod)
        monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.sqlalchemy", sqlalchemy_mod)
        monkeypatch.setenv("SENTRY_DSN", "https://public@example.invalid/1")
        monkeypatch.setenv("ENVIRONMENT", "production")

        assert init_sentry(service_name="test-service", release="test-release") is True
        assert captured["dsn"] == "https://public@example.invalid/1"
        assert captured["release"] == "test-release"
        assert captured["tags"] == {"service": "test-service"}
        assert captured["send_default_pii"] is False

        scrub = captured["before_send"]
        scrubbed = scrub(  # type: ignore[operator]
            {"tenant_id": "tenant-a", "nested": {"password": "secret", "safe": "value"}},
            None,
        )
        assert scrubbed == {
            "tenant_id": "[REDACTED]",
            "nested": {"password": "[REDACTED]", "safe": "value"},
        }

    def test_direct_service_entrypoints_do_not_duplicate_sentry_init(self) -> None:
        entrypoints = [
            Path("services/layer1-ingestion/src/layer1_ingestion/api/main.py"),
            Path("services/layer2-extraction/src/layer2_extraction/api/main.py"),
            Path("services/layer3-knowledge/src/api/main.py"),
            Path("services/layer4-agents/src/layer4_agents/api/main.py"),
        ]
        offenders = [
            str(path)
            for path in entrypoints
            if "sentry_sdk.init(" in path.read_text(encoding="utf-8")
        ]
        assert not offenders, f"Direct sentry_sdk.init calls remain in: {offenders}"


class TestFrontendSentry:
    """Frontend must import and initialize Sentry."""

    def _source(self) -> str:
        return Path("apps/web/src/main.tsx").read_text(encoding="utf-8")

    def test_imports_sentry_react(self) -> None:
        src = self._source()
        assert 'import * as Sentry from "@sentry/react"' in src

    def test_initializes_sentry_conditionally(self) -> None:
        src = self._source()
        assert "Sentry.init(" in src
        assert "import.meta.env.VITE_SENTRY_DSN" in src

    def test_configures_sample_rates(self) -> None:
        src = self._source()
        assert "sampleRate: 0.1" in src
        assert "tracesSampleRate: 0.01" in src

    def test_package_json_has_sentry_react(self) -> None:
        package_json = Path("apps/web/package.json").read_text(encoding="utf-8")
        assert "@sentry/react" in package_json


class TestEnvExample:
    """.env.example must document Sentry DSN variables."""

    def test_has_sentry_dsn(self) -> None:
        env_example = Path(".env.example").read_text(encoding="utf-8")
        assert "SENTRY_DSN=" in env_example
        assert "VITE_SENTRY_DSN=" in env_example

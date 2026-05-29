"""Security regression tests for P1-004: Sentry Integration.

Validates that:
- sentry-sdk is declared in all service pyproject.toml files
- create_fabric_app initializes Sentry when SENTRY_DSN is present
- Frontend main.tsx imports and initializes Sentry
"""

from __future__ import annotations

import ast
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

    def test_imports_sentry_sdk(self) -> None:
        src = self._source()
        assert "import sentry_sdk" in src
        assert "FastApiIntegration" in src
        assert "StarletteIntegration" in src

    def test_reads_sentry_dsn_from_env(self) -> None:
        src = self._source()
        assert 'os.getenv("SENTRY_DSN"' in src

    def test_configures_sample_rates(self) -> None:
        src = self._source()
        assert "sample_rate=0.1" in src
        assert "traces_sample_rate=0.01" in src
        assert "profiles_sample_rate=0.0" in src

    def test_sets_service_tag(self) -> None:
        src = self._source()
        assert '"service": service_name' in src

    def test_sets_release_and_environment(self) -> None:
        src = self._source()
        assert "release=version" in src
        assert 'os.getenv("ENVIRONMENT"' in src


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

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "check_deployable_service_images.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_deployable_service_images", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_file(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def write_service(
    root: Path,
    service_name: str,
    *,
    deployable: bool | None = None,
    dockerfile: bool = True,
) -> Path:
    value_fabric = ""
    if deployable is not None:
        value_fabric = f"""
[tool.value_fabric]
deployable = {str(deployable).lower()}
"""
    service_dir = root / "services" / service_name
    write_file(
        service_dir / "pyproject.toml",
        f"""
[project]
name = "{service_name}"
version = "0.1.0"
{value_fabric}
""",
    )
    if dockerfile:
        write_file(service_dir / "Dockerfile", "FROM python:3.11-slim\n")
    return service_dir


@pytest.fixture()
def checker_module(monkeypatch, tmp_path):
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    return module


def test_current_repository_gate_passes(capsys) -> None:
    module = load_module()

    assert module.main() == 0

    out = capsys.readouterr().out
    assert "deployable services have Dockerfiles and compose build definitions" in out


def test_legacy_billing_service_is_not_counted_as_deployable() -> None:
    module = load_module()

    deployable = module.deployable_service_dirs()

    assert "layer7-billing" in deployable
    assert "billing" not in deployable


def test_legacy_billing_package_is_removed_and_not_reintroduced() -> None:
    # COMPAT-BILL-001: legacy services/billing package deleted 2026-08-27.
    # Billing is split between layer7 (plans/usage/invoices/payment-state) and
    # layer4 (membership/subscription webhook domain). This ratchet fails if a
    # parallel `services/billing/` package is ever reintroduced.
    assert not (REPO_ROOT / "services" / "billing" / "pyproject.toml").exists()
    assert not (REPO_ROOT / "services" / "billing" / "Dockerfile").exists()


def test_layer7_readme_declares_canonical_billing_ownership() -> None:
    readme = (REPO_ROOT / "services" / "layer7-billing" / "README.md").read_text(
        encoding="utf-8"
    )

    assert "canonical deployable billing runtime" in readme
    assert "services/billing/ was removed" in readme
    assert "COMPAT-BILL-001" in readme


def test_non_deployable_service_is_excluded_from_gate(checker_module, tmp_path) -> None:
    write_service(tmp_path, "legacy-billing", deployable=False, dockerfile=False)
    write_file(tmp_path / "docker-compose.full.yml", "services: {}\n")

    assert checker_module.deployable_service_dirs() == set()
    assert checker_module.main() == 0


def test_missing_dockerfile_is_reported(checker_module, tmp_path, capsys) -> None:
    write_service(tmp_path, "layer7-billing", dockerfile=False)
    write_file(
        tmp_path / "docker-compose.full.yml",
        """
services:
  layer7-billing:
    build:
      context: .
      dockerfile: ./services/layer7-billing/Dockerfile
""",
    )

    assert checker_module.main() == 1

    out = capsys.readouterr().out
    assert "Dockerfile mismatch" in out
    assert "missing=['layer7-billing']" in out


def test_missing_compose_build_is_reported(checker_module, tmp_path, capsys) -> None:
    write_service(tmp_path, "layer7-billing")
    write_file(tmp_path / "docker-compose.full.yml", "services: {}\n")

    assert checker_module.main() == 1

    out = capsys.readouterr().out
    assert "Compose build mismatch" in out
    assert "missing=['layer7-billing']" in out


def test_compose_parser_accepts_supported_build_shapes(checker_module, tmp_path) -> None:
    write_file(
        tmp_path / "docker-compose.full.yml",
        """
services:
  api:
    build: ./services/api
  layer1:
    build:
      context: ./services/layer1-ingestion
      dockerfile: Dockerfile
  layer7:
    build:
      context: .
      dockerfile: ./services/layer7-billing/Dockerfile
""",
    )

    assert checker_module.compose_defined_services() == {
        "api",
        "layer1-ingestion",
        "layer7-billing",
    }

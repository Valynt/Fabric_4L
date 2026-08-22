"""P0-012: Frontend Dockerfile Lockfile Fix

Ensures all frontend Dockerfiles use --frozen-lockfile for reproducible,
tamper-evident builds and never use --no-frozen-lockfile.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = REPO_ROOT / "apps" / "web"

DOCKERFILES = [
    WEB_ROOT / "Dockerfile",
    WEB_ROOT / "Dockerfile.dev",
    WEB_ROOT / "Dockerfile.playwright",
]


@pytest.mark.security
@pytest.mark.contract_static
@pytest.mark.parametrize("dockerfile", DOCKERFILES, ids=[p.name for p in DOCKERFILES])
def test_dockerfile_uses_frozen_lockfile(dockerfile: Path):
    """Every frontend Dockerfile must use --frozen-lockfile."""
    assert dockerfile.exists(), f"{dockerfile} does not exist"
    content = dockerfile.read_text(encoding="utf-8")
    assert "--frozen-lockfile" in content, (
        f"{dockerfile.name} missing --frozen-lockfile flag"
    )


@pytest.mark.security
@pytest.mark.contract_static
@pytest.mark.parametrize("dockerfile", DOCKERFILES, ids=[p.name for p in DOCKERFILES])
def test_dockerfile_never_uses_no_frozen_lockfile(dockerfile: Path):
    """No frontend Dockerfile may use --no-frozen-lockfile."""
    assert dockerfile.exists(), f"{dockerfile} does not exist"
    content = dockerfile.read_text(encoding="utf-8")
    assert "--no-frozen-lockfile" not in content, (
        f"{dockerfile.name} contains forbidden --no-frozen-lockfile flag"
    )


@pytest.mark.security
@pytest.mark.contract_static
def test_dockerfile_production_uses_frozen_lockfile_in_both_stages():
    """Production Dockerfile must use --frozen-lockfile in both builder and runtime stages."""
    dockerfile = WEB_ROOT / "Dockerfile"
    lines = dockerfile.read_text(encoding="utf-8").splitlines()

    install_lines = [line for line in lines if line.strip().startswith("RUN") and "pnpm install" in line]
    assert len(install_lines) >= 2, (
        "Expected at least 2 RUN pnpm install lines (builder + runtime)"
    )

    for line in install_lines:
        assert "--frozen-lockfile" in line, (
            f"pnpm install missing --frozen-lockfile: {line.strip()}"
        )


@pytest.mark.security
@pytest.mark.contract_static
@pytest.mark.parametrize("dockerfile", DOCKERFILES, ids=[p.name for p in DOCKERFILES])
def test_dockerfile_copies_patched_dependencies_before_each_install(
    dockerfile: Path,
) -> None:
    """Each install stage must receive patch files declared by package.json."""
    stages = [
        stage
        for stage in dockerfile.read_text(encoding="utf-8").split("\nFROM ")
        if "pnpm install" in stage
    ]
    assert stages, f"{dockerfile.name} has no pnpm install stage"

    for stage in stages:
        patch_copy = stage.find("COPY patches ./patches")
        install = stage.find("pnpm install")
        assert 0 <= patch_copy < install, (
            f"{dockerfile.name} must copy canonical patch files before pnpm install"
        )


@pytest.mark.security
@pytest.mark.contract_static
def test_playwright_compose_uses_repository_root_build_context() -> None:
    compose = (
        REPO_ROOT / "infra" / "compose" / "docker-compose.playwright.yml"
    ).read_text(encoding="utf-8")

    assert "context: ../.." in compose
    assert "dockerfile: ./apps/web/Dockerfile.playwright" in compose


@pytest.mark.security
@pytest.mark.contract_static
def test_dockerfile_healthcheck_evaluates_port_env() -> None:
    """Production web Dockerfile healthcheck must evaluate process.env.PORT with 3000 fallback."""
    dockerfile = WEB_ROOT / "Dockerfile"
    assert dockerfile.exists(), f"{dockerfile} does not exist"
    content = dockerfile.read_text(encoding="utf-8")

    assert "process.env.PORT" in content, "Healthcheck should evaluate process.env.PORT"
    assert "3000" in content, "Healthcheck should retain fallback port 3000"
    assert "http://localhost:3000/" not in content, "Healthcheck should not contain hard-coded http://localhost:3000/ URL"
    assert "http://localhost:3000" not in content, "Healthcheck should not contain hard-coded http://localhost:3000 URL"


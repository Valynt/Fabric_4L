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

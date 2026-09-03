from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_penetration_workflows_do_not_raw_install_requests_or_aiohttp() -> None:
    for relative_path in (
        ".github/workflows/penetration-testing.yml",
        ".depot/workflows/penetration-testing.yml",
    ):
        text = _text(relative_path)
        assert "pip install requests aiohttp" not in text


def test_chaos_workflows_do_not_raw_install_aiohttp_pytest_or_asyncio() -> None:
    for relative_path in (
        ".github/workflows/chaos-testing.yml",
        ".depot/workflows/chaos-testing.yml",
    ):
        text = _text(relative_path)
        assert "pip install aiohttp pytest asyncio" not in text

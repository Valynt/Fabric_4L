from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "check_model_provider_boundaries.py"
SPEC = importlib.util.spec_from_file_location("model_provider_boundary_gate", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_detects_sdk_import_and_provider_hostname(tmp_path: Path) -> None:
    _write(tmp_path, "services/a.py", "from openai import AsyncOpenAI\n")
    _write(tmp_path, "packages/b.py", 'URL = "https://api.thesys.dev/v1"\n')
    _write(tmp_path, "packages/c.py", "import together\n")
    _write(tmp_path, "services/tests/test_allowed.py", "import anthropic\n")
    _write(tmp_path, "services/.venv/lib/site-packages/vendor.py", "import openai\n")

    assert MODULE.find_direct_provider_access(tmp_path) == {
        "services/a.py",
        "packages/b.py",
        "packages/c.py",
    }


def test_ignores_unrelated_http_clients(tmp_path: Path) -> None:
    _write(tmp_path, "services/a.py", "import httpx\nURL = 'https://example.com'\n")
    assert MODULE.find_direct_provider_access(tmp_path) == set()

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_pnpm_is_managed_only_by_the_root_corepack_pin() -> None:
    root_package = json.loads((ROOT / "package.json").read_text())
    web_package = json.loads((ROOT / "apps/web/package.json").read_text())

    assert root_package["packageManager"] == "pnpm@10.18.1"
    assert "pnpm" not in web_package.get("dependencies", {})
    assert "pnpm" not in web_package.get("devDependencies", {})

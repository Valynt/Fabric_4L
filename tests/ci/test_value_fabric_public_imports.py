from __future__ import annotations

import importlib.util
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "ci"
    / "check_value_fabric_public_imports.py"
)
SPEC = spec_from_file_location("check_value_fabric_public_imports", MODULE_PATH)
check_value_fabric_public_imports = module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["check_value_fabric_public_imports"] = check_value_fabric_public_imports
SPEC.loader.exec_module(check_value_fabric_public_imports)


def test_public_import_scanner_passes_clean_repo() -> None:
    assert check_value_fabric_public_imports.main([]) == 0


def test_public_import_scanner_blocks_runtime_public_api_imports(tmp_path: Path) -> None:
    sample_dir = tmp_path / "services" / "demo" / "src" / "adapters"
    sample_dir.mkdir(parents=True)
    (sample_dir / "value_fabric_api.py").write_text(
        "from value_fabric.public_api import shared\n",
        encoding="utf-8",
    )

    assert check_value_fabric_public_imports.main(["--repo-root", str(tmp_path)]) == 1


def test_value_fabric_public_api_package_removed() -> None:
    assert importlib.util.find_spec("value_fabric.public_api") is None

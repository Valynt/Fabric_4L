from __future__ import annotations

import shutil
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "check_compatibility_launch_freeze.py"
SPEC = spec_from_file_location("check_compatibility_launch_freeze", MODULE_PATH)
module = module_from_spec(SPEC)
sys.modules[SPEC.name] = module
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def test_launch_freeze_accepts_current_repo_state() -> None:
    assert module.main([]) == 0


def _make_temp_repo(name: str) -> Path:
    root = Path(__file__).resolve().parents[2] / "artifacts" / "test-tmp" / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


def test_launch_freeze_rejects_missing_registry_metadata(monkeypatch) -> None:
    tmp_path = _make_temp_repo("launch-freeze-metadata")
    registry = tmp_path / "docs" / "governance" / "compatibility-debt-registry.md"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        "\n".join(
            [
                "# Compatibility Debt Registry",
                "",
                "| ID | Runtime path | Type | Owner | Reason | Target removal date | Review metadata | Post-launch removal ticket |",
                "|---|---|---|---|---|---|---|---|",
                "| COMPAT-T-001 | `value_fabric/layer1/api/routes/compatibility.py` | Route wrapper | layer1 | test | 2026-08-31 |  |  |",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    canonical_root = tmp_path / "value_fabric" / "layer1"
    canonical_root.mkdir(parents=True)

    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "REGISTRY_PATH", registry)
    monkeypatch.setattr(module, "CANONICAL_RUNTIME_ROOTS", (canonical_root,))

    violations = module.check_launch_freeze()
    messages = [item.message for item in violations]
    assert any("missing review metadata" in message for message in messages)
    assert any("missing post-launch removal ticket" in message for message in messages)


def test_launch_freeze_rejects_unregistered_canonical_shim_path(monkeypatch) -> None:
    tmp_path = _make_temp_repo("launch-freeze-new-shim")
    registry = tmp_path / "docs" / "governance" / "compatibility-debt-registry.md"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        "\n".join(
            [
                "# Compatibility Debt Registry",
                "",
                "| ID | Runtime path | Type | Owner | Reason | Target removal date | Review metadata | Post-launch removal ticket |",
                "|---|---|---|---|---|---|---|---|",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    canonical_root = tmp_path / "value_fabric" / "layer3" / "api" / "routes"
    canonical_root.mkdir(parents=True)
    (canonical_root / "new_compat_surface.py").write_text("VALUE = 1\n", encoding="utf-8")

    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "REGISTRY_PATH", registry)
    monkeypatch.setattr(module, "CANONICAL_RUNTIME_ROOTS", (tmp_path / "value_fabric" / "layer3",))

    violations = module.check_launch_freeze()
    assert any(item.path == "value_fabric/layer3/api/routes/new_compat_surface.py" for item in violations)

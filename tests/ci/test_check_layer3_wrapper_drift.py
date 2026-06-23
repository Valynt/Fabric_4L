from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "check_layer3_wrapper_drift.py"
SPEC = importlib.util.spec_from_file_location("check_layer3_wrapper_drift", MODULE_PATH)
check_layer3_wrapper_drift = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(check_layer3_wrapper_drift)


def test_layer3_compatibility_namespace_check_passes_current_repo() -> None:
    assert check_layer3_wrapper_drift.main() == 0


def test_layer3_compatibility_namespace_rejects_runtime_file(tmp_path, monkeypatch) -> None:
    service_src = tmp_path / "services" / "layer3-knowledge" / "src"
    compat_namespace = tmp_path / "value_fabric" / "layer3"
    service_src.mkdir(parents=True)
    compat_namespace.mkdir(parents=True)
    (compat_namespace / "__init__.py").write_text("# placeholder\n", encoding="utf-8")
    (compat_namespace / "runtime.py").write_text("VALUE = 1\n", encoding="utf-8")

    monkeypatch.setattr(check_layer3_wrapper_drift, "SERVICE_SRC", service_src)
    monkeypatch.setattr(check_layer3_wrapper_drift, "COMPAT_NAMESPACE", compat_namespace)

    assert check_layer3_wrapper_drift.main() == 1

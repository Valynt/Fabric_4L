from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "check_layer5_shim_integrity.py"
SPEC = spec_from_file_location("check_layer5_shim_integrity", MODULE_PATH)
check_layer5_shim_integrity = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(check_layer5_shim_integrity)


CONTRACT = check_layer5_shim_integrity._layer5_source_contract


def test_layer5_compatibility_tree_is_shim_only() -> None:
    # Pass argv=[] to prevent argparse from consuming pytest's own CLI arguments.
    assert check_layer5_shim_integrity.main(argv=[]) == 0


def test_contract_accepts_removed_compatibility_tree(tmp_path, monkeypatch) -> None:
    canonical = tmp_path / "canonical"
    shim = tmp_path / "shim"
    canonical.mkdir()
    (canonical / "config.py").write_text("VALUE = 1\n", encoding="utf-8")

    monkeypatch.setattr(CONTRACT, "CANONICAL_ROOT", canonical)
    monkeypatch.setattr(CONTRACT, "SHIM_ROOT", shim)

    assert CONTRACT._shim_violations() == []


def test_contract_rejects_non_shim_compatibility_file(tmp_path, monkeypatch) -> None:
    canonical = tmp_path / "canonical"
    shim = tmp_path / "shim"
    canonical.mkdir()
    shim.mkdir()
    (canonical / "config.py").write_text("VALUE = 1\n", encoding="utf-8")
    (shim / "config.py").write_text("VALUE = 2\n", encoding="utf-8")

    monkeypatch.setattr(CONTRACT, "CANONICAL_ROOT", canonical)
    monkeypatch.setattr(CONTRACT, "SHIM_ROOT", shim)

    violations = CONTRACT._shim_violations()
    assert any("non-shim implementation" in item for item in violations)


def test_contract_accepts_importlib_shim_for_numeric_revision(tmp_path, monkeypatch) -> None:
    canonical = tmp_path / "canonical"
    shim = tmp_path / "shim"
    rel = Path("migrations/versions/002_add_rls.py")
    (canonical / rel.parent).mkdir(parents=True)
    (shim / rel.parent).mkdir(parents=True)
    (canonical / rel).write_text("revision = '002'\n", encoding="utf-8")
    (shim / rel).write_text(
        '"""Compatibility shim for canonical `layer5_ground_truth.migrations.versions.002_add_rls`."""\n\n'
        "from importlib import import_module as _import_module\n\n"
        '_CANONICAL_MODULE = "layer5_ground_truth.migrations.versions.002_add_rls"\n'
        "_module = _import_module(_CANONICAL_MODULE)\n"
        "for _name in dir(_module):\n"
        "    if not _name.startswith('_'):\n"
        "        globals()[_name] = getattr(_module, _name)\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(CONTRACT, "CANONICAL_ROOT", canonical)
    monkeypatch.setattr(CONTRACT, "SHIM_ROOT", shim)

    assert CONTRACT._shim_violations() == []


def test_contract_rejects_sys_path_mutation_in_canonical_tree(tmp_path, monkeypatch) -> None:
    canonical = tmp_path / "canonical"
    shim = tmp_path / "shim"
    canonical.mkdir()
    shim.mkdir()
    (canonical / "shared_bootstrap.py").write_text("import sys\nsys.path.append('x')\n", encoding="utf-8")
    (shim / "shared_bootstrap.py").write_text(
        '"""Compatibility shim."""\n\nfrom layer5_ground_truth.shared_bootstrap import *  # noqa: F401,F403\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(CONTRACT, "CANONICAL_ROOT", canonical)
    monkeypatch.setattr(CONTRACT, "SHIM_ROOT", shim)

    violations = CONTRACT._shim_violations()
    assert any("must not mutate sys.path" in item for item in violations)

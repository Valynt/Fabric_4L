import importlib
import importlib.util
import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "check_deprecated_namespace_imports.py"
SPEC = spec_from_file_location("check_deprecated_namespace_imports", MODULE_PATH)
check_deprecated_namespace_imports = module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["check_deprecated_namespace_imports"] = check_deprecated_namespace_imports
SPEC.loader.exec_module(check_deprecated_namespace_imports)


def test_namespace_scanner_passes_clean_repo() -> None:
    assert check_deprecated_namespace_imports.main([]) == 0


def test_namespace_scanner_detects_deprecated_import(tmp_path: Path) -> None:
    (tmp_path / "services/demo").mkdir(parents=True)
    sample = tmp_path / "services/demo/sample.py"
    sample.write_text("from value_fabric.layer1_ingestion.src import api\n", encoding="utf-8")
    assert check_deprecated_namespace_imports.main(["--repo-root", str(tmp_path), "--strict"]) == 1


def test_namespace_scanner_allows_baseline_findings(tmp_path: Path) -> None:
    (tmp_path / "services/demo").mkdir(parents=True)
    sample = tmp_path / "services/demo/sample.py"
    statement = "from value_fabric.layer1_ingestion.src import api"
    sample.write_text(statement + "\n", encoding="utf-8")
    baseline_dir = tmp_path / "docs/reference"
    baseline_dir.mkdir(parents=True)
    (baseline_dir / "deprecated-namespace-import-baseline.json").write_text(
        "["
        '{"path":"services/demo/sample.py","line":1,'
        '"statement":"from value_fabric.layer1_ingestion.src import api",'
        '"deprecated_namespace":"value_fabric.layer1_ingestion"}'
        "]",
        encoding="utf-8",
    )
    assert check_deprecated_namespace_imports.main(["--repo-root", str(tmp_path), "--strict", "--use-baseline"]) == 0


def test_namespace_scanner_categorizes_production_and_docs_comments_tests(tmp_path: Path, capsys) -> None:
    (tmp_path / "services/demo").mkdir(parents=True)
    (tmp_path / "tests/demo").mkdir(parents=True)
    (tmp_path / "services/demo/sample.py").write_text("import value_fabric.layer3_knowledge\n", encoding="utf-8")
    (tmp_path / "tests/demo/sample_test.py").write_text("import value_fabric.layer1_ingestion\n", encoding="utf-8")
    rc = check_deprecated_namespace_imports.main(["--repo-root", str(tmp_path), "--strict"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "production: 1" in out
    assert "docs_comments_tests: 1" in out


def test_namespace_scanner_enforce_ratchet_blocks_growth(tmp_path: Path) -> None:
    (tmp_path / "services/demo").mkdir(parents=True)
    (tmp_path / "docs/reference").mkdir(parents=True)
    (tmp_path / "services/demo/sample.py").write_text("import value_fabric.layer3_knowledge\n", encoding="utf-8")
    (tmp_path / "docs/reference/deprecated-namespace-import-baseline.json").write_text(json.dumps([]), encoding="utf-8")
    rc = check_deprecated_namespace_imports.main(["--repo-root", str(tmp_path), "--strict", "--enforce-ratchet", "--baseline-path", "docs/reference/deprecated-namespace-import-baseline.json"])
    assert rc == 1


def test_deleted_namespaces_no_longer_importable() -> None:
    for dead in ("value_fabric.layer1_ingestion", "value_fabric.layer3_knowledge"):
        spec = importlib.util.find_spec(dead)
        assert spec is None, f"Expected {dead} to be unimportable after cleanup"

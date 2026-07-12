from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "legacy_path_guard.py"
SPEC = spec_from_file_location("legacy_path_guard", MODULE_PATH)
assert SPEC and SPEC.loader
legacy_path_guard = module_from_spec(SPEC)
SPEC.loader.exec_module(legacy_path_guard)


def test_should_scan_skips_archives_and_allowlist(tmp_path: Path) -> None:
    repo = tmp_path
    archive_file = repo / "docs" / "archive" / "legacy.md"
    archive_file.parent.mkdir(parents=True)
    archive_file.write_text("value-fabric/foo", encoding="utf-8")

    allowed = repo / "MIGRATION_REPORT.md"
    allowed.write_text("value-fabric/foo", encoding="utf-8")

    active = repo / "scripts" / "check.sh"
    active.parent.mkdir(parents=True)
    active.write_text("echo ok", encoding="utf-8")

    assert not legacy_path_guard.should_scan(archive_file, repo)
    assert not legacy_path_guard.should_scan(allowed, repo)
    assert legacy_path_guard.should_scan(active, repo)


def test_detects_legacy_value_fabric_fs_token(tmp_path: Path) -> None:
    repo = tmp_path
    active = repo / "scripts" / "bad.sh"
    active.parent.mkdir(parents=True)
    active.write_text("cd value-fabric/service", encoding="utf-8")

    violations = []
    for path in repo.rglob("*"):
        if legacy_path_guard.should_scan(path, repo):
            for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if legacy_path_guard.LEGACY_TOKEN in line:
                    violations.append((path.relative_to(repo).as_posix(), idx))

    assert violations == [("scripts/bad.sh", 1)]

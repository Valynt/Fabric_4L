import importlib.util
from pathlib import Path


MODULE_PATH = Path("scripts/ci/check_dependabot_coverage.py")
SPEC = importlib.util.spec_from_file_location("check_dependabot_coverage", MODULE_PATH)
check_dependabot_coverage = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(check_dependabot_coverage)


def test_discovery_prunes_repo_tmp_manifests(tmp_path: Path) -> None:
    generated_package = tmp_path / ".tmp" / "generated-package"
    generated_package.mkdir(parents=True)
    (generated_package / "package.json").write_text('{"name":"generated"}\n', encoding="utf-8")
    (generated_package / "requirements.txt").write_text("generated==1.0\n", encoding="utf-8")
    (generated_package / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

    real_package = tmp_path / "services" / "api"
    real_package.mkdir(parents=True)
    (real_package / "requirements.txt").write_text("fastapi==0.1\n", encoding="utf-8")

    pip_dirs, npm_dirs, docker_dirs = check_dependabot_coverage.discover_manifest_dirs(tmp_path)

    assert pip_dirs == {"/services/api"}
    assert npm_dirs == set()
    assert docker_dirs == set()

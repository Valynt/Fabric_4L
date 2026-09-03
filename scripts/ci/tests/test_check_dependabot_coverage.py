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
    (generated_package / "package.json").write_text(
        '{"name":"generated"}\n', encoding="utf-8"
    )
    (generated_package / "requirements.txt").write_text(
        "generated==1.0\n", encoding="utf-8"
    )
    (generated_package / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

    real_package = tmp_path / "services" / "api"
    real_package.mkdir(parents=True)
    (real_package / "requirements.txt").write_text("fastapi==0.1\n", encoding="utf-8")

    pip_dirs, npm_dirs, docker_dirs = check_dependabot_coverage.discover_manifest_dirs(
        tmp_path
    )

    assert pip_dirs == {"/services/api"}
    assert npm_dirs == set()
    assert docker_dirs == set()


def test_discovery_prunes_archived_dependency_snapshots(tmp_path: Path) -> None:
    archived_package = tmp_path / "docs" / "archive" / "frontend-snapshot"
    archived_package.mkdir(parents=True)
    (archived_package / "package.json").write_text(
        '{"name":"historical-frontend"}\n', encoding="utf-8"
    )
    (archived_package / "requirements.txt").write_text(
        "historical==1.0\n", encoding="utf-8"
    )
    (archived_package / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

    live_package = tmp_path / "apps" / "web"
    live_package.mkdir(parents=True)
    (live_package / "package.json").write_text('{"name":"web"}\n', encoding="utf-8")

    pip_dirs, npm_dirs, docker_dirs = check_dependabot_coverage.discover_manifest_dirs(
        tmp_path
    )

    assert pip_dirs == set()
    assert npm_dirs == {"/apps/web"}
    assert docker_dirs == set()


def test_discovery_prunes_agent_skill_templates(tmp_path: Path) -> None:
    for skill_root in (".agents", ".claude"):
        template = tmp_path / skill_root / "skills" / "example" / "template"
        template.mkdir(parents=True)
        (template / "package.json").write_text(
            '{"name":"template"}\n', encoding="utf-8"
        )

    live_package = tmp_path / "packages" / "config"
    live_package.mkdir(parents=True)
    (live_package / "package.json").write_text('{"name":"config"}\n', encoding="utf-8")

    _, npm_dirs, _ = check_dependabot_coverage.discover_manifest_dirs(tmp_path)

    assert npm_dirs == {"/packages/config"}

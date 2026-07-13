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


def test_load_entries_expands_multi_directory_configuration(tmp_path: Path) -> None:
    config = tmp_path / "dependabot.yml"
    config.write_text(
        """
version: 2
updates:
  - package-ecosystem: npm
    directories:
      - /
      - /apps/web
  - package-ecosystem: pip
    directory: /services/api
""".lstrip(),
        encoding="utf-8",
    )

    covered = check_dependabot_coverage.load_dependabot_entries(config)

    assert covered == {
        "npm": {"/", "/apps/web"},
        "pip": {"/services/api"},
    }


def test_discovery_prunes_bundled_agent_skill_templates(tmp_path: Path) -> None:
    for root in (".agents", ".claude"):
        template = tmp_path / root / "skills" / "example" / "template"
        template.mkdir(parents=True)
        (template / "package.json").write_text(
            '{"name":"skill-template"}\n', encoding="utf-8"
        )

    real_package = tmp_path / "apps" / "web"
    real_package.mkdir(parents=True)
    (real_package / "package.json").write_text('{"name":"web"}\n', encoding="utf-8")

    _, npm_dirs, _ = check_dependabot_coverage.discover_manifest_dirs(tmp_path)

    assert npm_dirs == {"/apps/web"}

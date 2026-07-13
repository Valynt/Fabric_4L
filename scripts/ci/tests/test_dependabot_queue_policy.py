from pathlib import Path

import yaml


CONFIG = Path(".github/dependabot.yml")


def test_dependabot_queue_is_consolidated_and_capped() -> None:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    entries = data["updates"]

    assert [entry["package-ecosystem"] for entry in entries] == [
        "npm",
        "pip",
        "docker",
        "github-actions",
    ]
    assert sum(entry["open-pull-requests-limit"] for entry in entries) == 12
    assert {
        entry["package-ecosystem"]: entry["open-pull-requests-limit"]
        for entry in entries
    } == {"npm": 4, "pip": 4, "docker": 2, "github-actions": 2}


def test_dependabot_ecosystems_are_staggered_and_archives_are_excluded() -> None:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    entries = {entry["package-ecosystem"]: entry for entry in data["updates"]}

    assert {name: entry["schedule"]["day"] for name, entry in entries.items()} == {
        "npm": "monday",
        "pip": "tuesday",
        "docker": "wednesday",
        "github-actions": "thursday",
    }
    assert entries["npm"]["exclude-paths"] == ["docs/archive/**", "archive/**"]
    assert "/docs/archive/frontend-root-2026-05-02/source-snapshot" not in entries[
        "npm"
    ]["directories"]


def test_dependabot_multi_directory_groups_reduce_duplicate_prs() -> None:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    entries = {entry["package-ecosystem"]: entry for entry in data["updates"]}

    for ecosystem in ("npm", "pip", "docker"):
        groups = entries[ecosystem]["groups"]
        assert groups
        assert groups["routine-minor-patch"]["group-by"] == "dependency-name"
        assert groups["major-upgrades"]["group-by"] == "dependency-name"
        assert "group-by" not in groups["security-updates"]

    assert "/apps/web" in entries["npm"]["directories"]
    assert "/services/layer4-agents" in entries["pip"]["directories"]
    assert "/services/layer6-benchmarks" in entries["docker"]["directories"]

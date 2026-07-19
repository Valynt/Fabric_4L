from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FLEET_REGISTRY = REPO_ROOT / ".windsurf" / "AGENTS.md"


def test_referenced_agent_fleet_registry_exists() -> None:
    root_guidance = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert ".windsurf/AGENTS.md" in root_guidance
    assert FLEET_REGISTRY.is_file()


def test_agent_fleet_registry_defers_to_canonical_instructions() -> None:
    registry = FLEET_REGISTRY.read_text(encoding="utf-8")

    assert "../AGENTS.md" in registry
    assert "../docs/AGENTS.md" in registry
    assert "canonical" in registry.lower()

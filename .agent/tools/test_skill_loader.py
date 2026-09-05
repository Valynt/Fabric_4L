"""Regression tests for the portable-brain skill loader.

Verifies that skill context loading resolves from the canonical
``agents/skills/`` location (with a legacy ``.agent/skills/`` fallback),
per COMPAT-SKILLS-001.

Run with:  python -m pytest .agent/tools/test_skill_loader.py -v
"""
import os
import sys

# Ensure the tools directory is importable regardless of the CWD.
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import skill_loader  # noqa: E402


def test_skills_dir_prefers_canonical_location():
    """SKILLS_DIR should resolve to agents/skills when it exists."""
    repo_root = os.path.dirname(os.path.dirname(TOOLS_DIR))
    canonical = os.path.join(repo_root, "agents", "skills")
    if os.path.isdir(canonical):
        assert os.path.normpath(skill_loader.SKILLS_DIR) == os.path.normpath(canonical)


def test_load_manifest_returns_skills():
    """load_manifest() should return the registered skills."""
    manifest = skill_loader.load_manifest()
    assert len(manifest) > 0
    names = {s.get("name") for s in manifest}
    # repo-audit is a first-party skill that must be loadable.
    assert "repo-audit" in names


def test_progressive_load_finds_repo_audit():
    """progressive_load() should match repo-audit on an audit trigger."""
    loaded = skill_loader.progressive_load("audit repo")
    names = [s["name"] for s in loaded]
    assert "repo-audit" in names

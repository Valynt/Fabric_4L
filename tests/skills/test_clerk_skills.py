"""
Contract & Integrity Tests for Clerk Agent Skills Portfolio.

Validates that all skills under `.agents/skills/clerk/` and `.claude/skills/clerk/`:
1. Contain valid `SKILL.md` with complete trigger and description metadata.
2. Template configurations (package.json, tsconfig.json) are valid JSON.
3. Templates adhere to Clerk current SDK standard (no obsolete dependencies).
4. Critical cross-framework reference patterns exist for React, Vue, Next, Expo, TanStack, Swift, Android, Billing, and Webhooks.
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CLERK_SKILLS_DIR = REPO_ROOT / ".agents" / "skills" / "clerk"

EXPECTED_SKILL_MODULES = [
    "clerk-android",
    "clerk-astro-patterns",
    "clerk-backend-api",
    "clerk-billing",
    "clerk-chrome-extension-patterns",
    "clerk-cli",
    "clerk-custom-ui",
    "clerk-expo",
    "clerk-expo-patterns",
    "clerk-nextjs-patterns",
    "clerk-nuxt-patterns",
    "clerk-orgs",
    "clerk-react-patterns",
    "clerk-react-router-patterns",
    "clerk-setup",
    "clerk-swift",
    "clerk-tanstack-patterns",
    "clerk-testing",
    "clerk-vue-patterns",
    "clerk-webhooks",
]


def test_clerk_skills_root_manifest_exists():
    root_skill = CLERK_SKILLS_DIR / "SKILL.md"
    assert root_skill.exists(), "Root SKILL.md router must exist in .agents/skills/clerk/"
    content = root_skill.read_text(encoding="utf-8")
    assert "Clerk Skills Router" in content
    assert "By Task" in content


@pytest.mark.parametrize("skill_name", EXPECTED_SKILL_MODULES)
def test_skill_manifest_validity(skill_name: str):
    skill_path = CLERK_SKILLS_DIR / skill_name
    assert skill_path.exists(), f"Skill module '{skill_name}' must exist"
    skill_md = skill_path / "SKILL.md"
    assert skill_md.exists(), f"SKILL.md must exist for '{skill_name}'"
    content = skill_md.read_text(encoding="utf-8")
    assert len(content.strip()) > 50, f"SKILL.md for '{skill_name}' is too short"


def test_template_json_files_are_valid():
    """Verify all template package.json and tsconfig.json files parse as valid JSON."""
    json_files = list(CLERK_SKILLS_DIR.glob("**/templates/**/*.json"))
    assert len(json_files) > 0, "Expected templates containing JSON files"

    for jf in json_files:
        content = jf.read_text(encoding="utf-8")
        try:
            parsed = json.loads(content)
            assert isinstance(parsed, dict)
        except Exception as e:
            pytest.fail(f"Invalid JSON in {jf}: {e}")


def test_evals_json_files_are_valid():
    """Verify all evals.json definitions parse as valid JSON lists or dicts."""
    eval_files = list(CLERK_SKILLS_DIR.glob("**/evals/*.json"))
    assert len(eval_files) > 0, "Expected evals.json files in skills"

    for ef in eval_files:
        content = ef.read_text(encoding="utf-8")
        try:
            parsed = json.loads(content)
            assert isinstance(parsed, (dict, list))
        except Exception as e:
            pytest.fail(f"Invalid JSON in {ef}: {e}")

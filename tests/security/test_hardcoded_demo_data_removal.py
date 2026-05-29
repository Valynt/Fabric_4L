"""Security regression tests for P1-006: Hardcoded Demo Data Removal.

Validates that:
- Real customer names are extracted into src/lib/demoData.ts
- ProspectPromptBuilder.tsx no longer contains inline real customer names
- ESLint blocks hardcoded customer names outside demoData.ts
- Production gets generic placeholders (import.meta.env.DEV guard)
"""

from __future__ import annotations

from pathlib import Path


class TestDemoDataExtracted:
    """Demo data must live in the canonical module."""

    def test_demo_data_file_exists(self) -> None:
        assert Path("apps/web/src/lib/demoData.ts").exists()

    def test_prompt_builder_imports_demo_data(self) -> None:
        src = Path("apps/web/src/components/workspace/ProspectPromptBuilder.tsx").read_text(
            encoding="utf-8"
        )
        assert 'from "@/lib/demoData"' in src or "from '@/lib/demoData'" in src

    def test_prompt_builder_has_no_inline_medtronic(self) -> None:
        src = Path("apps/web/src/components/workspace/ProspectPromptBuilder.tsx").read_text(
            encoding="utf-8"
        )
        assert "Medtronic" not in src

    def test_prompt_builder_has_no_inline_goldman(self) -> None:
        src = Path("apps/web/src/components/workspace/ProspectPromptBuilder.tsx").read_text(
            encoding="utf-8"
        )
        assert "Goldman Sachs" not in src

    def test_demo_data_contains_real_names(self) -> None:
        src = Path("apps/web/src/lib/demoData.ts").read_text(encoding="utf-8")
        assert "Medtronic" in src
        assert "Goldman Sachs" in src

    def test_demo_data_has_dev_guard(self) -> None:
        src = Path("apps/web/src/lib/demoData.ts").read_text(encoding="utf-8")
        assert "import.meta.env.DEV" in src

    def test_production_placeholders_are_generic(self) -> None:
        src = Path("apps/web/src/lib/demoData.ts").read_text(encoding="utf-8")
        # Production placeholder company should not contain real customer names
        prod_section = src.split("_PROD_COMPANIES")[1]
        assert "Medtronic" not in prod_section
        assert "Stryker" not in prod_section
        assert "Goldman Sachs" not in prod_section


class TestEslintEnforcement:
    """ESLint must block hardcoded customer names outside demoData.ts."""

    def test_eslint_config_has_restricted_syntax(self) -> None:
        eslint = Path("apps/web/.eslintrc.cjs").read_text(encoding="utf-8")
        assert "no-restricted-syntax" in eslint
        assert "Medtronic" in eslint
        assert "demoData.ts" in eslint

    def test_eslint_allows_demo_data_file(self) -> None:
        eslint = Path("apps/web/.eslintrc.cjs").read_text(encoding="utf-8")
        assert 'files: ["src/lib/demoData.ts"]' in eslint
        assert '"no-restricted-syntax": "off"' in eslint


class TestTestsUseImports:
    """Tests must import demo data instead of hardcoding strings."""

    def test_submission_test_imports_demo_data(self) -> None:
        src = Path("apps/web/src/workflow/pages/ProspectSetup.submission.test.tsx").read_text(
            encoding="utf-8"
        )
        assert "@/lib/demoData" in src
        assert "DEFAULT_ACTIVITIES" in src
        assert "DEFAULT_COMPANIES" in src

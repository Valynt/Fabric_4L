import json
from pathlib import Path


def test_formula_metadata_alias_has_deprecation_metadata() -> None:
    spec = json.loads(Path("contracts/openapi/layer3-knowledge.json").read_text(encoding="utf-8"))
    props = spec["components"]["schemas"]["FormulaMetadata"]["properties"]

    assert "id" in props
    assert "formula_id" in props
    assert props["formula_id"]["deprecated"] is True
    assert props["formula_id"]["x-deprecation-target-version"] == "v2.5"
    assert props["formula_id"]["x-deprecation-target-date"] == "2026-10-01"


def test_formula_pages_use_canonical_id_navigation() -> None:
    formula_list = Path("apps/web/src/pages/FormulaList.tsx").read_text(encoding="utf-8")
    formula_builder = Path("apps/web/src/pages/FormulaBuilder.tsx").read_text(encoding="utf-8")

    assert "formulaId: formula.id" in formula_list
    assert "formulaId: data.id ?? data.formula_id" in formula_builder


def test_generated_types_include_formula_alias_deprecation_notice() -> None:
    generated = Path("packages/platform-contract/src/typescript/generated/layer3_knowledge.ts").read_text(encoding="utf-8")
    assert "Deprecated alias of id. Removal target: v2.5 (2026-10-01)." in generated

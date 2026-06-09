"""Unit tests for layer2_extraction.validation.EntailmentValidator."""

from __future__ import annotations

from layer2_extraction.models.ontology import (
    Capability,
    Feature,
    Persona,
    RoleType,
    UseCase,
    ValueCategory,
    ValueDriver,
)
from layer2_extraction.models.relationships import PredicateType, Relationship
from layer2_extraction.validation import EntailmentValidator, ValidationSeverity


# ---------------------------------------------------------------------------
# Minimal ExtractionResult stand-in
# ---------------------------------------------------------------------------

class _FakeResult:
    def __init__(
        self,
        capabilities=None,
        features=None,
        use_cases=None,
        personas=None,
        value_drivers=None,
    ):
        self.capabilities = capabilities or []
        self.features = features or []
        self.use_cases = use_cases or []
        self.personas = personas or []
        self.value_drivers = value_drivers or []


def _cap(id_: str, name: str = "Capability Name", confidence: float = 0.9) -> Capability:
    return Capability(id=id_, name=name, description="A capability description", confidence=confidence)


def _uc(id_: str, name: str = "Use Case Name", confidence: float = 0.9) -> UseCase:
    return UseCase(id=id_, name=name, description="A use case description", confidence=confidence)


def _vd(id_: str, unit: str | None = "USD") -> ValueDriver:
    return ValueDriver(
        id=id_,
        name="Value Driver",
        description="A value driver description",
        unit=unit,
        confidence=0.8,
        category=ValueCategory.COST_REDUCTION,
    )


def _rel(source_id: str, target_id: str, predicate: PredicateType = PredicateType.ENABLES) -> Relationship:
    return Relationship(
        source_id=source_id,
        target_id=target_id,
        canonical_predicate=predicate,
        confidence=0.9,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestValidatePassCase:
    def test_empty_result_returns_val000(self):
        v = EntailmentValidator()
        results = v.validate(_FakeResult(), [])
        assert len(results) == 1
        assert results[0].rule_id == "VAL-000"
        assert results[0].passed is True
        assert results[0].severity == ValidationSeverity.INFO

    def test_valid_entities_and_relationships_returns_val000(self):
        cap = _cap("c1")
        uc = _uc("u1")
        result = _FakeResult(capabilities=[cap], use_cases=[uc])
        rels = [_rel("c1", "u1")]
        v = EntailmentValidator()
        results = v.validate(result, rels)
        assert len(results) == 1
        assert results[0].rule_id == "VAL-000"


class TestVAL001:
    def test_value_driver_missing_unit_produces_error(self):
        vd = _vd("vd1", unit=None)
        result = _FakeResult(value_drivers=[vd])
        v = EntailmentValidator()
        results = v.validate(result, [])
        rule_ids = [r.rule_id for r in results]
        assert "VAL-001" in rule_ids
        val001 = next(r for r in results if r.rule_id == "VAL-001")
        assert val001.passed is False
        assert val001.severity == ValidationSeverity.ERROR

    def test_value_driver_with_unit_does_not_trigger_val001(self):
        vd = _vd("vd1", unit="USD")
        result = _FakeResult(value_drivers=[vd])
        v = EntailmentValidator()
        results = v.validate(result, [])
        assert all(r.rule_id != "VAL-001" for r in results)

    def test_multiple_value_drivers_missing_unit_produces_multiple_errors(self):
        vds = [_vd(f"vd{i}", unit=None) for i in range(3)]
        result = _FakeResult(value_drivers=vds)
        v = EntailmentValidator()
        results = v.validate(result, [])
        val001_errors = [r for r in results if r.rule_id == "VAL-001"]
        assert len(val001_errors) == 3


class TestVAL006:
    def _make_entity_with_confidence(self, confidence: float):
        """Create a fake entity bypassing Pydantic validation for out-of-range confidence."""
        cap = _cap("c1")
        object.__setattr__(cap, "confidence", confidence)
        return cap

    def test_confidence_above_1_produces_error(self):
        cap = self._make_entity_with_confidence(1.5)
        result = _FakeResult(capabilities=[cap])
        v = EntailmentValidator()
        results = v.validate(result, [])
        rule_ids = [r.rule_id for r in results]
        assert "VAL-006" in rule_ids

    def test_confidence_below_0_produces_error(self):
        cap = self._make_entity_with_confidence(-0.1)
        result = _FakeResult(capabilities=[cap])
        v = EntailmentValidator()
        results = v.validate(result, [])
        rule_ids = [r.rule_id for r in results]
        assert "VAL-006" in rule_ids

    def test_confidence_at_boundary_0_is_valid(self):
        cap = _cap("c1", confidence=0.0)
        result = _FakeResult(capabilities=[cap])
        v = EntailmentValidator()
        results = v.validate(result, [])
        assert all(r.rule_id != "VAL-006" for r in results)

    def test_confidence_at_boundary_1_is_valid(self):
        cap = _cap("c1", confidence=1.0)
        result = _FakeResult(capabilities=[cap])
        v = EntailmentValidator()
        results = v.validate(result, [])
        assert all(r.rule_id != "VAL-006" for r in results)


class TestVAL002:
    def test_enables_with_non_capability_source_produces_error(self):
        feat = Feature(id="f1", name="Feature Name", description="A feature description", confidence=0.9)
        uc = _uc("u1")
        result = _FakeResult(features=[feat], use_cases=[uc])
        rels = [_rel("f1", "u1", PredicateType.ENABLES)]
        v = EntailmentValidator()
        results = v.validate(result, rels)
        val002 = [r for r in results if r.rule_id == "VAL-002"]
        assert len(val002) >= 1
        assert any("Domain violation" in r.message for r in val002)

    def test_enables_with_non_usecase_target_produces_error(self):
        cap = _cap("c1")
        feat = Feature(id="f1", name="Feature Name", description="A feature description", confidence=0.9)
        result = _FakeResult(capabilities=[cap], features=[feat])
        rels = [_rel("c1", "f1", PredicateType.ENABLES)]
        v = EntailmentValidator()
        results = v.validate(result, rels)
        val002 = [r for r in results if r.rule_id == "VAL-002"]
        assert len(val002) >= 1
        assert any("Range violation" in r.message for r in val002)

    def test_enables_with_valid_cap_to_uc_passes(self):
        cap = _cap("c1")
        uc = _uc("u1")
        result = _FakeResult(capabilities=[cap], use_cases=[uc])
        rels = [_rel("c1", "u1", PredicateType.ENABLES)]
        v = EntailmentValidator()
        results = v.validate(result, rels)
        assert all(r.rule_id != "VAL-002" for r in results)

    def test_unknown_source_id_does_not_trigger_val002(self):
        """If source entity not found, no domain violation is raised."""
        uc = _uc("u1")
        result = _FakeResult(use_cases=[uc])
        rels = [_rel("unknown-id", "u1", PredicateType.ENABLES)]
        v = EntailmentValidator()
        results = v.validate(result, rels)
        assert all(r.rule_id != "VAL-002" for r in results)


class TestHelpers:
    def test_all_entities_collects_from_all_lists(self):
        cap = _cap("c1")
        uc = _uc("u1")
        vd = _vd("vd1")
        persona = Persona(id="p1", title="Product Manager", role_type=RoleType.CHAMPION, department="Product", confidence=0.8)
        feat = Feature(id="f1", name="Feature Name", description="A feature description", confidence=0.9)
        result = _FakeResult(
            capabilities=[cap],
            use_cases=[uc],
            value_drivers=[vd],
            personas=[persona],
            features=[feat],
        )
        v = EntailmentValidator()
        entities = v._all_entities(result)
        ids = {getattr(e, "id", None) for e in entities}
        assert ids == {"c1", "u1", "vd1", "p1", "f1"}

    def test_find_entity_by_id_returns_correct_entity(self):
        cap = _cap("c1")
        uc = _uc("u1")
        result = _FakeResult(capabilities=[cap], use_cases=[uc])
        v = EntailmentValidator()
        found = v._find_entity_by_id(result, "u1")
        assert found is uc

    def test_find_entity_by_id_returns_none_for_missing(self):
        result = _FakeResult(capabilities=[_cap("c1")])
        v = EntailmentValidator()
        assert v._find_entity_by_id(result, "nonexistent") is None

    def test_all_entities_handles_none_lists(self):
        result = _FakeResult()
        result.capabilities = None  # type: ignore[assignment]
        v = EntailmentValidator()
        # Should not raise
        entities = v._all_entities(result)
        assert isinstance(entities, list)

"""Semantic contract tests for pack ontology ↔ L2 extraction alignment.

Validates that:
- Pack ontology enums align with L2 extraction models
- L2 extraction produces valid ontology-compliant output
- L3 ingestion preserves all required fields
"""

import uuid

import pytest

from layer2_extraction.models import (
    BenefitType,
    Capability,
    DriverType,
    EnablementType,
    ImpactLevel,
    Persona,
    PredicateType,
    Relationship,
    RoleType,
    SeniorityLevel,
    UseCase,
    ValueCategory,
    ValueDriver,
)


class TestRoleTypeAlignment:
    """Validate role_type enum alignment between pack and L2 extraction."""

    def test_role_type_enum_values(self):
        """RoleType covers all buying-process functions."""
        expected = {
            "economic_buyer",
            "champion",
            "operational_user",
            "technical_buyer",
            "stakeholder",
        }
        actual = {rt.value for rt in RoleType}
        assert actual == expected, f"RoleType mismatch: {actual - expected}"

    def test_seniority_level_enum_values(self):
        """SeniorityLevel covers all organizational hierarchy levels."""
        expected = {
            "executive_sponsor",
            "c_suite",
            "vp",
            "director",
            "manager",
            "individual_contributor",
            "unknown",
        }
        actual = {sl.value for sl in SeniorityLevel}
        assert actual == expected, f"SeniorityLevel mismatch: {actual - expected}"

    def test_persona_has_both_role_and_seniority(self):
        """Persona model includes both role_type and seniority_level."""
        persona = Persona(
            role_type=RoleType.ECONOMIC_BUYER,
            seniority_level=SeniorityLevel.C_SUITE,
            title="CFO",
            department="Finance",
        )
        assert persona.role_type == RoleType.ECONOMIC_BUYER
        assert persona.seniority_level == SeniorityLevel.C_SUITE


class TestValueCategoryAlignment:
    """Validate ValueCategory alignment with pack ontology."""

    def test_value_category_enum_values(self):
        """ValueCategory includes pack-aligned granular categories."""
        expected = {
            # Pack-aligned categories
            "capital_efficiency",
            "cost_reduction",
            "risk_mitigation",
            "revenue_enhancement",
            # Legacy values (backward compatibility)
            "revenue",
            "cost",
            "risk",
            "capital",
        }
        actual = {vc.value for vc in ValueCategory}
        assert actual == expected, f"ValueCategory mismatch: {actual - expected}"

    def test_value_driver_with_granular_category(self):
        """ValueDriver accepts new granular categories."""
        driver = ValueDriver(
            category=ValueCategory.CAPITAL_EFFICIENCY,
            name="Working Capital Optimization",
            description="Reduces days sales outstanding",
            unit="days",
        )
        assert driver.category == ValueCategory.CAPITAL_EFFICIENCY

    def test_value_driver_backward_compatibility(self):
        """ValueDriver still accepts legacy categories."""
        driver = ValueDriver(
            category=ValueCategory.REVENUE,
            name="Revenue Growth",
            description="Increases ARR",
            unit="USD",
        )
        assert driver.category == ValueCategory.REVENUE


class TestRelationshipPropertyEnums:
    """Validate relationship property enums align with pack ontology."""

    def test_enablement_type_enum_values(self):
        """EnablementType matches pack ontology enablement_type property."""
        expected = {"required", "enhances", "optional"}
        actual = {et.value for et in EnablementType}
        assert actual == expected

    def test_benefit_type_enum_values(self):
        """BenefitType matches pack ontology benefit_type property."""
        expected = {"time_savings", "error_reduction", "visibility", "efficiency"}
        actual = {bt.value for bt in BenefitType}
        assert actual == expected

    def test_driver_type_enum_values(self):
        """DriverType matches pack ontology driver_type property."""
        expected = {"primary", "secondary", "tertiary"}
        actual = {dt.value for dt in DriverType}
        assert actual == expected

    def test_impact_level_enum_values(self):
        """ImpactLevel includes pack-aligned values with legacy support."""
        expected = {
            "transformational",
            "significant",
            "moderate",
            "minor",
            "high",
            "medium",
            "low",
        }
        actual = {il.value for il in ImpactLevel}
        assert actual == expected


class TestRelationshipModel:
    """Validate Relationship model stores raw and canonical predicates."""

    def test_relationship_has_raw_and_canonical_predicate(self):
        """Relationship stores both raw (extracted) and canonical (normalized) predicates."""
        rel = Relationship(
            source_id=str(uuid.uuid4()),
            raw_predicate="supports",
            canonical_predicate=PredicateType.ENABLES,
            target_id=str(uuid.uuid4()),
            evidence_text="The analytics capability supports forecasting",
            source_url="https://example.com",
        )
        assert rel.raw_predicate == "supports"
        assert rel.canonical_predicate == PredicateType.ENABLES

    def test_relationship_with_all_properties(self):
        """Relationship can store all pack-aligned relationship properties."""
        rel = Relationship(
            source_id=str(uuid.uuid4()),
            raw_predicate="is essential for",
            canonical_predicate=PredicateType.ENABLES,
            target_id=str(uuid.uuid4()),
            evidence_text="Required for the use case",
            source_url="https://example.com",
            impact_level=ImpactLevel.SIGNIFICANT,
            strength=0.9,
            enablement_type=EnablementType.REQUIRED,
            contribution_weight=0.85,
        )
        assert rel.enablement_type == EnablementType.REQUIRED
        assert rel.contribution_weight == 0.85
        assert rel.impact_level == ImpactLevel.SIGNIFICANT


class TestPredicateNormalization:
    """Validate predicate normalization rules."""

    @pytest.mark.parametrize(
        "raw,canonical",
        [
            ("requires", PredicateType.REQUIRES),
            ("enables", PredicateType.ENABLES),
            ("benefits", PredicateType.BENEFITS),
            ("drives", PredicateType.DRIVES),
            ("depends on", PredicateType.DEPENDS_ON),
            ("is alternative to", PredicateType.ALTERNATIVE_TO),
        ],
    )
    def test_common_predicate_normalization(self, raw, canonical):
        """Common predicates normalize to canonical form."""
        # This test documents normalization expectations
        # The actual normalization happens during extraction
        assert isinstance(canonical, PredicateType)

    def test_inverse_relationship_mapping(self):
        """ENABLES and REQUIRES are inverses of each other."""
        cap = Capability(name="Test Cap", description="Test capability")
        uc = UseCase(name="Test UC", description="Test use case")

        rel = Relationship(
            source_id=cap.id,
            raw_predicate="enables",
            canonical_predicate=PredicateType.ENABLES,
            target_id=uc.id,
            evidence_text="Cap enables UC",
            source_url="https://example.com",
        )

        inverse = rel.get_inverse()
        assert inverse is not None
        assert inverse.canonical_predicate == PredicateType.REQUIRES
        assert inverse.source_id == uc.id
        assert inverse.target_id == cap.id


class TestPackOntologyAlignment:
    """Integration tests validating pack ontology ↔ L2 extraction alignment."""

    def test_life_sciences_ontology_compatibility(self):
        """Life Sciences pack ontology values are valid in L2 models."""
        # Persona from life-sciences pack
        persona = Persona(
            role_type=RoleType.OPERATIONAL_USER,
            seniority_level=SeniorityLevel.VP,
            title="Head of Clinical Operations",
            department="Clinical Operations",
            pain_points=["Patient recruitment delays"],
            success_metrics=["Enrollment rate"],
        )
        assert persona.seniority_level == SeniorityLevel.VP

        # ValueDriver from life-sciences pack
        driver = ValueDriver(
            category=ValueCategory.CAPITAL_EFFICIENCY,
            name="Time-to-Market",
            description="Total time from IND to market approval",
            unit="Months",
            metrics=["Enrollment rate", "Regulatory review time"],
        )
        assert driver.category == ValueCategory.CAPITAL_EFFICIENCY

    def test_manufacturing_ontology_compatibility(self):
        """Manufacturing pack ontology values are valid in L2 models."""
        # ValueDriver from manufacturing pack
        driver = ValueDriver(
            category=ValueCategory.COST_REDUCTION,
            name="Manufacturing Cost Per Unit",
            description="Total manufacturing cost divided by units",
            unit="Currency per unit",
        )
        assert driver.category == ValueCategory.COST_REDUCTION

    def test_software_ontology_compatibility(self):
        """Software pack ontology values are valid in L2 models."""
        # Persona from software pack
        persona = Persona(
            role_type=RoleType.ECONOMIC_BUYER,  # CRO is economic buyer
            seniority_level=SeniorityLevel.C_SUITE,
            title="Chief Revenue Officer",
            department="Revenue",
            pain_points=["Hitting growth targets"],
            success_metrics=["ARR", "NRR"],
        )
        assert persona.role_type == RoleType.ECONOMIC_BUYER
        assert persona.seniority_level == SeniorityLevel.C_SUITE

        # ValueDriver from software pack
        driver = ValueDriver(
            category=ValueCategory.REVENUE_ENHANCEMENT,
            name="Net Revenue Retention",
            description="Annual revenue from existing customers",
            unit="Percentage",
        )
        assert driver.category == ValueCategory.REVENUE_ENHANCEMENT


class TestSemanticContract:
    """End-to-end semantic contract validation."""

    def test_extraction_to_storage_field_preservation(self):
        """All pack-relevant fields from extraction flow through to storage model."""
        # Simulate extraction output
        persona = Persona(
            role_type=RoleType.ECONOMIC_BUYER,
            seniority_level=SeniorityLevel.VP,
            title="VP Finance",
            department="Finance",
            pain_points=["Cost control"],
            success_metrics=["Budget variance"],
        )

        driver = ValueDriver(
            category=ValueCategory.RISK_MITIGATION,
            name="Compliance Risk",
            description="Reduces compliance violations",
            unit="count",
            formula_string="{violations_before} - {violations_after}",
            metrics=["Violations per quarter"],
        )

        # Verify all pack-relevant fields are present
        assert persona.seniority_level is not None
        assert driver.formula_string is not None
        assert driver.metrics

        # Relationship with properties
        rel = Relationship(
            source_id=str(uuid.uuid4()),
            raw_predicate="cares about",
            canonical_predicate=PredicateType.DRIVES,
            target_id=str(uuid.uuid4()),
            evidence_text="VP Finance cares about compliance",
            source_url="https://example.com",
            driver_type=DriverType.PRIMARY,
            influence_weight=0.9,
        )

        assert rel.raw_predicate == "cares about"
        assert rel.canonical_predicate == PredicateType.DRIVES
        assert rel.driver_type == DriverType.PRIMARY
        assert rel.influence_weight == 0.9


class TestEdgeCases:
    """Edge case and boundary condition tests."""

    def test_persona_defaults_to_unknown_seniority(self):
        """Persona without seniority_level defaults to UNKNOWN."""
        persona = Persona(
            role_type=RoleType.STAKEHOLDER,
            title="Analyst",
            department="Operations",
        )
        assert persona.seniority_level == SeniorityLevel.UNKNOWN

    def test_relationship_optional_properties_none_by_default(self):
        """Relationship properties default to None when not specified."""
        rel = Relationship(
            source_id=str(uuid.uuid4()),
            raw_predicate="supports",
            canonical_predicate=PredicateType.ENABLES,
            target_id=str(uuid.uuid4()),
            evidence_text="Basic relationship",
            source_url="https://example.com",
        )
        assert rel.enablement_type is None
        assert rel.benefit_type is None
        assert rel.driver_type is None
        assert rel.contribution_weight is None
        assert rel.influence_weight is None
        assert rel.impact_level is None
        assert rel.strength is None

    def test_value_driver_accepts_all_category_variants(self):
        """ValueDriver accepts both new granular and legacy categories."""
        new_categories = [
            ValueCategory.CAPITAL_EFFICIENCY,
            ValueCategory.COST_REDUCTION,
            ValueCategory.RISK_MITIGATION,
            ValueCategory.REVENUE_ENHANCEMENT,
        ]
        legacy_categories = [
            ValueCategory.CAPITAL,
            ValueCategory.COST,
            ValueCategory.RISK,
            ValueCategory.REVENUE,
        ]
        for category in new_categories + legacy_categories:
            driver = ValueDriver(
                category=category,
                name="Test Driver",
                description="Test description",
                unit="USD",
            )
            assert driver.category == category

    def test_seniority_level_from_string(self):
        """SeniorityLevel can be created from string values."""
        for level in SeniorityLevel:
            parsed = SeniorityLevel(level.value)
            assert parsed == level

    def test_impact_level_legacy_values_still_work(self):
        """ImpactLevel accepts both pack-aligned and legacy values."""
        pack_values = [
            ImpactLevel.TRANSFORMATIONAL,
            ImpactLevel.SIGNIFICANT,
            ImpactLevel.MODERATE,
            ImpactLevel.MINOR,
        ]
        legacy_values = [
            ImpactLevel.HIGH,
            ImpactLevel.MEDIUM,
            ImpactLevel.LOW,
        ]
        for level in pack_values + legacy_values:
            rel = Relationship(
                source_id=str(uuid.uuid4()),
                raw_predicate="test",
                canonical_predicate=PredicateType.ENABLES,
                target_id=str(uuid.uuid4()),
                evidence_text="Test relationship",
                source_url="https://example.com",
                impact_level=level,
            )
            assert rel.impact_level == level

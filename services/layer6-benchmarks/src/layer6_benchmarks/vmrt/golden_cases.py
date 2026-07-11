"""VMRT golden test cases.

Each case is derived from the built-in seed datasets
(:data:`layer6_benchmarks.models.benchmark_dataset.MANUFACTURING_BENCHMARK_SEED`,
etc.) so the expected outputs can be computed deterministically from the same
statistical engine the production service uses.

Golden cases cover:
- compare: multiple percentile buckets (below p10, between brackets, above p90)
- compare: ``is_higher_better=False`` metrics (percentile is inverted)
- validate: within-tolerance, boundary, and out-of-range inputs
- validate: different severity tiers (info / warning / error)

Dataset IDs match the canonical seed dataset IDs so the VMRT runner can look
them up via the in-process seed builder without a live Neo4j connection.
"""

from __future__ import annotations

from decimal import Decimal

from .models import VMRTCase, VMRTCaseKind

# ---------------------------------------------------------------------------
# Manufacturing – OEE (is_higher_better=True, sample_size=1250 → confidence=high)
# ---------------------------------------------------------------------------
_MFG_DATASET = "manufacturing-efficiency-2024"
_MFG_OEE = "oee_overall_equipment_effectiveness"
_MFG_DEFECT = "defect_rate_percent"
_MFG_ENERGY = "energy_consumption_per_unit_kwh"

# ---------------------------------------------------------------------------
# SaaS / B2B (is_higher_better varies, sample_size varies)
# ---------------------------------------------------------------------------
_SAAS_DATASET = "saas-b2b-efficiency-2024"
_SAAS_NRR = "net_revenue_retention_percent"
_SAAS_CHURN = "annual_churn_rate_percent"
_SAAS_GM = "gross_margin_percent"

GOLDEN_CASES: list[VMRTCase] = [
    # ── Manufacturing OEE compare ───────────────────────────────────────────
    VMRTCase(
        id="mfg-oee-compare-below-p10",
        kind=VMRTCaseKind.COMPARE,
        dataset_id=_MFG_DATASET,
        metric=_MFG_OEE,
        company_value=Decimal("40"),
        expected_percentile=5,
        expected_assessment="needs_improvement",
        expected_confidence="high",
        is_higher_better=True,
        description="OEE below p10 maps to percentile=5, needs_improvement",
    ),
    VMRTCase(
        id="mfg-oee-compare-between-p25-p50",
        kind=VMRTCaseKind.COMPARE,
        dataset_id=_MFG_DATASET,
        metric=_MFG_OEE,
        company_value=Decimal("60"),
        expected_percentile=37,
        expected_assessment="below_average",
        expected_confidence="high",
        is_higher_better=True,
        description="OEE between p25 and p50 maps to percentile=37, below_average",
    ),
    VMRTCase(
        id="mfg-oee-compare-at-p50",
        kind=VMRTCaseKind.COMPARE,
        dataset_id=_MFG_DATASET,
        metric=_MFG_OEE,
        company_value=Decimal("65"),
        expected_percentile=37,
        expected_assessment="below_average",
        expected_confidence="high",
        is_higher_better=True,
        description="OEE exactly at p50 (≤p50 bucket) maps to percentile=37",
    ),
    VMRTCase(
        id="mfg-oee-compare-between-p75-p90",
        kind=VMRTCaseKind.COMPARE,
        dataset_id=_MFG_DATASET,
        metric=_MFG_OEE,
        company_value=Decimal("80"),
        expected_percentile=82,
        expected_assessment="top_performer",
        expected_confidence="high",
        is_higher_better=True,
        description="OEE between p75 and p90 maps to percentile=82, top_performer",
    ),
    VMRTCase(
        id="mfg-oee-compare-above-p90",
        kind=VMRTCaseKind.COMPARE,
        dataset_id=_MFG_DATASET,
        metric=_MFG_OEE,
        company_value=Decimal("90"),
        expected_percentile=95,
        expected_assessment="top_performer",
        expected_confidence="high",
        is_higher_better=True,
        description="OEE above p90 maps to percentile=95, top_performer",
    ),
    # ── Manufacturing defect rate compare (is_higher_better=False) ──────────
    VMRTCase(
        id="mfg-defect-compare-below-p10-inverted",
        kind=VMRTCaseKind.COMPARE,
        dataset_id=_MFG_DATASET,
        metric=_MFG_DEFECT,
        company_value=Decimal("0.05"),
        expected_percentile=95,
        expected_assessment="top_performer",
        expected_confidence="high",
        is_higher_better=False,
        description=(
            "Defect rate below p10 is excellent; lower-is-better inversion "
            "gives percentile=95, top_performer"
        ),
    ),
    VMRTCase(
        id="mfg-defect-compare-between-p50-p75-inverted",
        kind=VMRTCaseKind.COMPARE,
        dataset_id=_MFG_DATASET,
        metric=_MFG_DEFECT,
        company_value=Decimal("2.0"),
        expected_percentile=38,
        expected_assessment="below_average",
        expected_confidence="high",
        is_higher_better=False,
        description=(
            "Defect rate between p50 and p75; inverted gives percentile=38, below_average"
        ),
    ),
    VMRTCase(
        id="mfg-defect-compare-above-p90-inverted",
        kind=VMRTCaseKind.COMPARE,
        dataset_id=_MFG_DATASET,
        metric=_MFG_DEFECT,
        company_value=Decimal("6.0"),
        expected_percentile=5,
        expected_assessment="needs_improvement",
        expected_confidence="high",
        is_higher_better=False,
        description=(
            "Defect rate above p90 is very poor; inverted gives percentile=5, needs_improvement"
        ),
    ),
    # ── SaaS NRR compare (is_higher_better=True, sample_size=980 → medium) ─
    VMRTCase(
        id="saas-nrr-compare-between-p10-p25",
        kind=VMRTCaseKind.COMPARE,
        dataset_id=_SAAS_DATASET,
        metric=_SAAS_NRR,
        company_value=Decimal("95"),
        expected_percentile=17,
        expected_assessment="needs_improvement",
        expected_confidence="medium",
        is_higher_better=True,
        description="NRR between p10 and p25; sample_size=980 yields confidence=medium",
    ),
    VMRTCase(
        id="saas-nrr-compare-between-p50-p75",
        kind=VMRTCaseKind.COMPARE,
        dataset_id=_SAAS_DATASET,
        metric=_SAAS_NRR,
        company_value=Decimal("112"),
        expected_percentile=62,
        expected_assessment="above_average",
        expected_confidence="medium",
        is_higher_better=True,
        description="NRR between p50 and p75 maps to above_average",
    ),
    VMRTCase(
        id="saas-nrr-compare-above-p90",
        kind=VMRTCaseKind.COMPARE,
        dataset_id=_SAAS_DATASET,
        metric=_SAAS_NRR,
        company_value=Decimal("145"),
        expected_percentile=95,
        expected_assessment="top_performer",
        expected_confidence="medium",
        is_higher_better=True,
        description="NRR above p90 maps to top_performer",
    ),
    # ── SaaS churn rate compare (is_higher_better=False, sample_size=1200 → high)
    VMRTCase(
        id="saas-churn-compare-at-p50-inverted",
        kind=VMRTCaseKind.COMPARE,
        dataset_id=_SAAS_DATASET,
        metric=_SAAS_CHURN,
        company_value=Decimal("15"),
        expected_percentile=63,
        expected_assessment="above_average",
        expected_confidence="high",
        is_higher_better=False,
        description="Churn at p50; lower-is-better inversion gives percentile=63, above_average",
    ),
    # ── Manufacturing OEE validate ──────────────────────────────────────────
    VMRTCase(
        id="mfg-oee-validate-at-median",
        kind=VMRTCaseKind.VALIDATE,
        dataset_id=_MFG_DATASET,
        metric=_MFG_OEE,
        company_value=Decimal("65"),
        expected_is_valid=True,
        expected_severity="info",
        tolerance_percent=10,
        description="OEE at median is always valid, severity=info",
    ),
    VMRTCase(
        id="mfg-oee-validate-at-upper-boundary",
        kind=VMRTCaseKind.VALIDATE,
        dataset_id=_MFG_DATASET,
        metric=_MFG_OEE,
        company_value=Decimal("93.5"),
        expected_is_valid=True,
        expected_severity="info",
        tolerance_percent=10,
        description="OEE at upper tolerance boundary (p90=85 × 1.10=93.5) is still valid",
    ),
    VMRTCase(
        id="mfg-oee-validate-far-below-range",
        kind=VMRTCaseKind.VALIDATE,
        dataset_id=_MFG_DATASET,
        metric=_MFG_OEE,
        company_value=Decimal("10"),
        expected_is_valid=False,
        expected_severity="error",
        tolerance_percent=10,
        description="OEE=10 is well below p10*(1-0.1)=40.5; deviation >50% → error",
    ),
    # ── SaaS churn validate ─────────────────────────────────────────────────
    VMRTCase(
        id="saas-churn-validate-at-median",
        kind=VMRTCaseKind.VALIDATE,
        dataset_id=_SAAS_DATASET,
        metric=_SAAS_CHURN,
        company_value=Decimal("15"),
        expected_is_valid=True,
        expected_severity="info",
        tolerance_percent=10,
        description="Churn at median is always valid, severity=info",
    ),
    VMRTCase(
        id="saas-churn-validate-above-range",
        kind=VMRTCaseKind.VALIDATE,
        dataset_id=_SAAS_DATASET,
        metric=_SAAS_CHURN,
        company_value=Decimal("50"),
        expected_is_valid=False,
        expected_severity="error",
        tolerance_percent=10,
        description="Churn=50 exceeds p90*(1.1)=38.5; deviation >50% from median → error",
    ),
    # ── SaaS gross margin validate ──────────────────────────────────────────
    VMRTCase(
        id="saas-gm-validate-within-range",
        kind=VMRTCaseKind.VALIDATE,
        dataset_id=_SAAS_DATASET,
        metric=_SAAS_GM,
        company_value=Decimal("78"),
        expected_is_valid=True,
        expected_severity="info",
        tolerance_percent=10,
        description="Gross margin at p50=78 is within range, severity=info",
    ),
]

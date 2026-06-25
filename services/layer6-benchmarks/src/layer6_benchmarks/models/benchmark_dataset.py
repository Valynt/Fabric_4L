"""Benchmark dataset models for Layer 6.

Storage model aligned with Neo4j + provenance tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from value_fabric.shared.models.typed_dict import TypedDictModel


class StatisticalProfile_to_dictResult(TypedDictModel):
    mean: Any
    p10: Any
    p25: Any
    p50: Any
    p75: Any
    p90: Any
    sample_size: Any
    std_dev: Any


@dataclass
class StatisticalProfile:
    """Statistical profile for a benchmark metric."""

    p10: Decimal
    p25: Decimal
    p50: Decimal
    p75: Decimal
    p90: Decimal
    mean: Decimal
    std_dev: Decimal
    sample_size: int

    def to_dict(self) -> dict[str, Any]:
        return StatisticalProfile_to_dictResult.model_validate(
            {
                "p10": str(self.p10),
                "p25": str(self.p25),
                "p50": str(self.p50),
                "p75": str(self.p75),
                "p90": str(self.p90),
                "mean": str(self.mean),
                "std_dev": str(self.std_dev),
                "sample_size": self.sample_size,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StatisticalProfile":
        return cls(
            p10=Decimal(data["p10"]),
            p25=Decimal(data["p25"]),
            p50=Decimal(data["p50"]),
            p75=Decimal(data["p75"]),
            p90=Decimal(data["p90"]),
            mean=Decimal(data["mean"]),
            std_dev=Decimal(data["std_dev"]),
            sample_size=data["sample_size"],
        )


@dataclass
class BenchmarkMetric:
    """Individual metric within a benchmark dataset."""

    name: str
    unit: str  # e.g., "USD", "hours", "percent"
    description: str
    profile: StatisticalProfile

    # Validation rules
    lower_bound: Decimal | None = None
    upper_bound: Decimal | None = None
    is_higher_better: bool = True  # For comparison direction

    # ValueOS governance/provenance metadata. These are optional so existing
    # tenant-created benchmark datasets keep their current shape.
    display_name: str | None = None
    functional_domain: str | None = None
    category: str | None = None
    lifecycle_stage: str | None = None
    value_type: str | None = None
    company_size_band: str | None = None
    maturity_band: str | None = None
    revenue_band: str | None = None
    distribution_shape: str = "unknown"
    source_name: str | None = None
    source_type: str | None = None
    source_count: int = 0
    source_publication_year: int | None = None
    license_class: str = "unspecified"
    confidence_score: float | None = None
    caveats: list[str] = field(default_factory=list)
    vintage: str | None = None
    governance_status: str | None = None
    stale_after: str | None = None


@dataclass
class BenchmarkDataset:
    """Benchmark dataset for an industry/segment.

    Curated dataset (not validated claims) for peer comparison
    and statistical validation.
    """

    dataset_id: str
    name: str
    description: str

    # Classification
    industry: str
    segment: str | None  # e.g., "enterprise", "mid-market", "small"
    geography: str | None  # e.g., "US", "EU", "global"

    # Metrics
    metrics: dict[str, BenchmarkMetric] = field(default_factory=dict)

    # Metadata
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None
    data_source: str | None = None  # e.g., "Gartner 2024", "Internal Study"

    # Provenance
    provenance_id: str | None = None  # Links to L4 provenance tracking
    is_public: bool = False

    # Isolation
    tenant_id: str = "system"
    ownership_mode: Literal["tenant", "global_system"] = "tenant"

    def get_metric(self, name: str) -> BenchmarkMetric | None:
        """Get metric by name."""
        return self.metrics.get(name)

    def add_metric(self, metric: BenchmarkMetric) -> None:
        """Add metric to dataset."""
        self.metrics[metric.name] = metric
        self.updated_at = datetime.now(timezone.utc)


@dataclass
class ComparisonRequest:
    """Request for peer comparison."""

    dataset_id: str
    metric: str
    company_value: Decimal
    industry: str
    segment: str | None = None


@dataclass
class ComparisonResult:
    """Result of peer comparison with statistical profile."""

    percentile: int  # 0-100
    peer_median: Decimal
    peer_range: tuple[Decimal, Decimal]  # (p10, p90)
    sample_size: int
    confidence: str  # high, medium, low

    # Detailed breakdown
    statistical_profile: StatisticalProfile | None = None

    # Interpretation
    assessment: str = ""  # e.g., "above_average", "top_performer"


@dataclass
class RangeValidationRequest:
    """Request for range validation."""

    dataset_id: str
    metric: str
    value: Decimal
    tolerance_percent: int = 10


@dataclass
class RangeValidationResult:
    """Result of range validation."""

    is_valid: bool
    expected_range: tuple[Decimal, Decimal]
    actual_value: Decimal
    deviation_percent: float | None
    severity: str  # info, warning, error

    # Guidance
    message: str = ""
    recommended_action: str | None = None


# Manufacturing benchmark reference dataset (seed data)
MANUFACTURING_BENCHMARK_SEED = {
    "dataset_id": "manufacturing-efficiency-2024",
    "name": "Manufacturing Efficiency Benchmarks 2024",
    "description": "Peer benchmarks for manufacturing efficiency metrics",
    "industry": "manufacturing",
    "segment": "enterprise",
    "geography": "global",
    "version": "1.0.0",
    "data_source": "Industry Consortium 2024",
    "is_public": True,
    "metrics": {
        "oee_overall_equipment_effectiveness": {
            "name": "oee_overall_equipment_effectiveness",
            "unit": "percent",
            "description": "Overall Equipment Effectiveness",
            "profile": {
                "p10": "45.0",
                "p25": "55.0",
                "p50": "65.0",
                "p75": "75.0",
                "p90": "85.0",
                "mean": "65.0",
                "std_dev": "12.5",
                "sample_size": 1250,
            },
            "lower_bound": "30.0",
            "upper_bound": "95.0",
            "is_higher_better": True,
        },
        "production_cycle_time_minutes": {
            "name": "production_cycle_time_minutes",
            "unit": "minutes",
            "description": "Average production cycle time",
            "profile": {
                "p10": "15.0",
                "p25": "25.0",
                "p50": "45.0",
                "p75": "75.0",
                "p90": "120.0",
                "mean": "56.0",
                "std_dev": "28.0",
                "sample_size": 890,
            },
            "is_higher_better": False,
        },
        "defect_rate_percent": {
            "name": "defect_rate_percent",
            "unit": "percent",
            "description": "Manufacturing defect rate",
            "profile": {
                "p10": "0.1",
                "p25": "0.5",
                "p50": "1.5",
                "p75": "3.0",
                "p90": "5.0",
                "mean": "2.1",
                "std_dev": "1.4",
                "sample_size": 1100,
            },
            "lower_bound": "0.0",
            "upper_bound": "10.0",
            "is_higher_better": False,
        },
        "energy_consumption_per_unit_kwh": {
            "name": "energy_consumption_per_unit_kwh",
            "unit": "kWh",
            "description": "Energy consumption per unit produced",
            "profile": {
                "p10": "0.5",
                "p25": "1.2",
                "p50": "2.5",
                "p75": "4.0",
                "p90": "6.5",
                "mean": "2.8",
                "std_dev": "1.8",
                "sample_size": 675,
            },
            "is_higher_better": False,
        },
    },
}

# SaaS / B2B benchmark reference dataset (seed data)
SAAS_B2B_BENCHMARK_SEED = {
    "dataset_id": "saas-b2b-efficiency-2024",
    "name": "SaaS / B2B Efficiency Benchmarks 2024",
    "description": "Peer benchmarks for SaaS and B2B operational metrics",
    "industry": "technology",
    "segment": "enterprise",
    "geography": "global",
    "version": "1.0.0",
    "data_source": "Gartner / OpenView 2024",
    "is_public": True,
    "metrics": {
        "customer_acquisition_cost_usd": {
            "name": "customer_acquisition_cost_usd",
            "unit": "USD",
            "description": "Average customer acquisition cost",
            "profile": {
                "p10": "5000.0",
                "p25": "12000.0",
                "p50": "28000.0",
                "p75": "55000.0",
                "p90": "95000.0",
                "mean": "35000.0",
                "std_dev": "22000.0",
                "sample_size": 850,
            },
            "lower_bound": "1000.0",
            "upper_bound": "150000.0",
            "is_higher_better": False,
        },
        "annual_churn_rate_percent": {
            "name": "annual_churn_rate_percent",
            "unit": "percent",
            "description": "Annual customer churn rate",
            "profile": {
                "p10": "3.0",
                "p25": "8.0",
                "p50": "15.0",
                "p75": "25.0",
                "p90": "35.0",
                "mean": "16.5",
                "std_dev": "8.5",
                "sample_size": 1200,
            },
            "lower_bound": "0.0",
            "upper_bound": "50.0",
            "is_higher_better": False,
        },
        "net_revenue_retention_percent": {
            "name": "net_revenue_retention_percent",
            "unit": "percent",
            "description": "Net revenue retention rate",
            "profile": {
                "p10": "90.0",
                "p25": "100.0",
                "p50": "110.0",
                "p75": "125.0",
                "p90": "140.0",
                "mean": "112.0",
                "std_dev": "14.0",
                "sample_size": 980,
            },
            "lower_bound": "70.0",
            "upper_bound": "160.0",
            "is_higher_better": True,
        },
        "gross_margin_percent": {
            "name": "gross_margin_percent",
            "unit": "percent",
            "description": "Gross margin percentage",
            "profile": {
                "p10": "55.0",
                "p25": "68.0",
                "p50": "78.0",
                "p75": "85.0",
                "p90": "92.0",
                "mean": "76.5",
                "std_dev": "10.5",
                "sample_size": 1100,
            },
            "lower_bound": "30.0",
            "upper_bound": "95.0",
            "is_higher_better": True,
        },
        "sales_cycle_days": {
            "name": "sales_cycle_days",
            "unit": "days",
            "description": "Average enterprise sales cycle length",
            "profile": {
                "p10": "30.0",
                "p25": "60.0",
                "p50": "120.0",
                "p75": "210.0",
                "p90": "365.0",
                "mean": "145.0",
                "std_dev": "85.0",
                "sample_size": 720,
            },
            "lower_bound": "7.0",
            "upper_bound": "540.0",
            "is_higher_better": False,
        },
        "se_hours_per_opportunity": {
            "name": "se_hours_per_opportunity",
            "unit": "hours",
            "description": "Sales engineering hours spent per qualified opportunity",
            "profile": {
                "p10": "1.5",
                "p25": "2.5",
                "p50": "4.0",
                "p75": "6.0",
                "p90": "8.5",
                "mean": "4.2",
                "std_dev": "2.1",
                "sample_size": 850,
            },
            "lower_bound": "0.5",
            "upper_bound": "20.0",
            "is_higher_better": False,
        },
    },
}

# Healthcare benchmark reference dataset (seed data)
HEALTHCARE_BENCHMARK_SEED = {
    "dataset_id": "healthcare-operational-2024",
    "name": "Healthcare Operational Metrics 2024",
    "description": "Peer benchmarks for healthcare operational efficiency",
    "industry": "healthcare",
    "segment": "enterprise",
    "geography": "US",
    "version": "1.0.0",
    "data_source": "HFMA / AHA 2024",
    "is_public": True,
    "metrics": {
        "patient_throughput_per_hour": {
            "name": "patient_throughput_per_hour",
            "unit": "patients",
            "description": "Average patient throughput per hour",
            "profile": {
                "p10": "1.5",
                "p25": "2.5",
                "p50": "4.0",
                "p75": "6.0",
                "p90": "8.5",
                "mean": "4.3",
                "std_dev": "2.1",
                "sample_size": 650,
            },
            "lower_bound": "0.5",
            "upper_bound": "12.0",
            "is_higher_better": True,
        },
        "claim_denial_rate_percent": {
            "name": "claim_denial_rate_percent",
            "unit": "percent",
            "description": "Insurance claim denial rate",
            "profile": {
                "p10": "2.0",
                "p25": "4.0",
                "p50": "7.0",
                "p75": "11.0",
                "p90": "16.0",
                "mean": "7.5",
                "std_dev": "3.8",
                "sample_size": 800,
            },
            "lower_bound": "0.0",
            "upper_bound": "25.0",
            "is_higher_better": False,
        },
        "average_length_of_stay_days": {
            "name": "average_length_of_stay_days",
            "unit": "days",
            "description": "Average inpatient length of stay",
            "profile": {
                "p10": "2.5",
                "p25": "3.5",
                "p50": "5.0",
                "p75": "7.0",
                "p90": "10.0",
                "mean": "5.2",
                "std_dev": "2.0",
                "sample_size": 920,
            },
            "lower_bound": "1.0",
            "upper_bound": "15.0",
            "is_higher_better": False,
        },
        "readmission_rate_percent": {
            "name": "readmission_rate_percent",
            "unit": "percent",
            "description": "30-day hospital readmission rate",
            "profile": {
                "p10": "5.0",
                "p25": "8.0",
                "p50": "12.0",
                "p75": "16.0",
                "p90": "21.0",
                "mean": "12.5",
                "std_dev": "4.0",
                "sample_size": 1050,
            },
            "lower_bound": "2.0",
            "upper_bound": "30.0",
            "is_higher_better": False,
        },
        "cost_per_discharge_usd": {
            "name": "cost_per_discharge_usd",
            "unit": "USD",
            "description": "Average cost per patient discharge",
            "profile": {
                "p10": "4500.0",
                "p25": "7500.0",
                "p50": "12000.0",
                "p75": "18500.0",
                "p90": "28000.0",
                "mean": "13500.0",
                "std_dev": "6500.0",
                "sample_size": 780,
            },
            "lower_bound": "2000.0",
            "upper_bound": "50000.0",
            "is_higher_better": False,
        },
    },
}

# Financial Services benchmark reference dataset (seed data)
FINANCIAL_SERVICES_BENCHMARK_SEED = {
    "dataset_id": "financial-services-performance-2024",
    "name": "Financial Services Performance Benchmarks 2024",
    "description": "Peer benchmarks for financial services operational and risk metrics",
    "industry": "financial_services",
    "segment": "enterprise",
    "geography": "global",
    "version": "1.0.0",
    "data_source": "McKinsey / Deloitte 2024",
    "is_public": True,
    "metrics": {
        "cost_to_income_ratio_percent": {
            "name": "cost_to_income_ratio_percent",
            "unit": "percent",
            "description": "Cost-to-income ratio (efficiency)",
            "profile": {
                "p10": "35.0",
                "p25": "48.0",
                "p50": "58.0",
                "p75": "68.0",
                "p90": "78.0",
                "mean": "57.5",
                "std_dev": "11.0",
                "sample_size": 700,
            },
            "lower_bound": "25.0",
            "upper_bound": "90.0",
            "is_higher_better": False,
        },
        "return_on_equity_percent": {
            "name": "return_on_equity_percent",
            "unit": "percent",
            "description": "Return on equity",
            "profile": {
                "p10": "4.0",
                "p25": "8.0",
                "p50": "12.0",
                "p75": "16.0",
                "p90": "22.0",
                "mean": "12.5",
                "std_dev": "5.0",
                "sample_size": 850,
            },
            "lower_bound": "0.0",
            "upper_bound": "30.0",
            "is_higher_better": True,
        },
        "non_performing_loan_ratio_percent": {
            "name": "non_performing_loan_ratio_percent",
            "unit": "percent",
            "description": "Non-performing loan ratio",
            "profile": {
                "p10": "0.5",
                "p25": "1.2",
                "p50": "2.5",
                "p75": "4.5",
                "p90": "7.0",
                "mean": "2.8",
                "std_dev": "1.8",
                "sample_size": 900,
            },
            "lower_bound": "0.0",
            "upper_bound": "15.0",
            "is_higher_better": False,
        },
        "customer_acquisition_cost_usd": {
            "name": "customer_acquisition_cost_usd",
            "unit": "USD",
            "description": "Average customer acquisition cost for financial products",
            "profile": {
                "p10": "150.0",
                "p25": "350.0",
                "p50": "750.0",
                "p75": "1500.0",
                "p90": "3000.0",
                "mean": "950.0",
                "std_dev": "800.0",
                "sample_size": 680,
            },
            "lower_bound": "50.0",
            "upper_bound": "5000.0",
            "is_higher_better": False,
        },
        "digital_adoption_rate_percent": {
            "name": "digital_adoption_rate_percent",
            "unit": "percent",
            "description": "Customer digital channel adoption rate",
            "profile": {
                "p10": "45.0",
                "p25": "58.0",
                "p50": "72.0",
                "p75": "82.0",
                "p90": "90.0",
                "mean": "70.5",
                "std_dev": "12.0",
                "sample_size": 950,
            },
            "lower_bound": "20.0",
            "upper_bound": "95.0",
            "is_higher_better": True,
        },
    },
}

"""
Tests for Data Intelligence Layer Phase 1 — Layer 3 Components.

Covers:
  Task 1.1 — Product Portfolio Graph (product_service.py, products.py routes)
  Task 1.3 — Evidence Library (case_study_service.py, evidence.py routes)

All Neo4j interactions are mocked; these are unit/contract tests that verify
service logic and API endpoint contracts without requiring a live database.
"""

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


# ---------------------------------------------------------------------------
# Async-compatible mock helpers
# ---------------------------------------------------------------------------


class _FakeRecord:
    """Minimal Neo4j record mock."""

    def __init__(self, data: dict[str, Any]):
        self._data = data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def data(self) -> dict[str, Any]:
        return self._data


class _AsyncIterResult:
    """Async-iterable result mock for Neo4j session.run()."""

    def __init__(self, records: list[_FakeRecord]):
        self._records = records
        self._idx = 0

    async def single(self):
        return self._records[0] if self._records else None

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._idx >= len(self._records):
            raise StopAsyncIteration
        record = self._records[self._idx]
        self._idx += 1
        return record


def _make_mock_driver(records: list[dict[str, Any]] | None = None):
    """Build a mock Neo4j async driver with session → run → records chain."""
    if records is None:
        records = []

    fake_records = [_FakeRecord(r) for r in records]
    result_mock = _AsyncIterResult(fake_records)

    session_mock = AsyncMock()
    session_mock.run = AsyncMock(return_value=result_mock)
    session_mock.__aenter__ = AsyncMock(return_value=session_mock)
    session_mock.__aexit__ = AsyncMock(return_value=None)

    driver = AsyncMock()
    driver.session = MagicMock(return_value=session_mock)

    return driver, session_mock, result_mock


def _make_multi_query_driver(query_results: list[list[dict[str, Any]]]):
    """Build a mock driver that returns different results for sequential queries."""
    results = []
    for records in query_results:
        fake_records = [_FakeRecord(r) for r in records]
        results.append(_AsyncIterResult(fake_records))

    session_mock = AsyncMock()
    session_mock.run = AsyncMock(side_effect=results)
    session_mock.__aenter__ = AsyncMock(return_value=session_mock)
    session_mock.__aexit__ = AsyncMock(return_value=None)

    driver = AsyncMock()
    driver.session = MagicMock(return_value=session_mock)

    return driver, session_mock


# ---------------------------------------------------------------------------
# Task 1.1 — Product Portfolio Graph: Service Tests
# ---------------------------------------------------------------------------


class TestProductService:
    """Unit tests for ProductService (Task 1.1)."""

    @pytest.mark.asyncio
    async def test_create_product_returns_id(self):
        """ProductService.create_product stores node and returns its id."""
        from src.services.product_service import ProductCreate, ProductService

        driver, session, result = _make_mock_driver(
            [{"product": {"id": "p1", "name": "TestProduct", "category": "SaaS"}}]
        )

        svc = ProductService(driver)
        pc = ProductCreate(
            name="TestProduct",
            description="A test product for unit testing",
            category="SaaS",
        )
        res = await svc.create_product("tenant-1", pc)

        assert "id" in res
        assert res["name"] == "TestProduct"
        session.run.assert_called()

    @pytest.mark.asyncio
    async def test_get_product_not_found(self):
        """ProductService.get_product returns None for missing product."""
        from src.services.product_service import ProductService

        driver, session, result = _make_mock_driver([])

        svc = ProductService(driver)
        res = await svc.get_product("tenant-1", "nonexistent-id")

        assert res is None

    @pytest.mark.asyncio
    async def test_get_product_found(self):
        """ProductService.get_product returns product dict when found."""
        from src.services.product_service import ProductService

        product_data = {
            "product": {
                "id": "prod-1",
                "name": "ValueEngine",
                "description": "Value selling platform",
                "category": "SaaS",
            },
            "features": [{"id": "f1", "name": "Feature A"}],
            "capabilities": [{"id": "c1", "name": "Cap 1"}],
        }
        driver, session, result = _make_mock_driver([product_data])

        svc = ProductService(driver)
        res = await svc.get_product("tenant-1", "prod-1")

        assert res is not None

    @pytest.mark.asyncio
    async def test_list_products_pagination(self):
        """ProductService.list_products returns paginated results."""
        from src.services.product_service import ProductService

        driver, session = _make_multi_query_driver([
            # Count query result
            [{"total": 5}],
            # List query result
            [
                {"product": {"id": "p1", "name": "P1"}, "feature_count": 2, "capability_count": 1},
                {"product": {"id": "p2", "name": "P2"}, "feature_count": 3, "capability_count": 0},
            ],
        ])

        svc = ProductService(driver)
        res = await svc.list_products("tenant-1", limit=2, skip=0)

        assert res["total"] == 5
        assert len(res["products"]) == 2

    @pytest.mark.asyncio
    async def test_delete_product(self):
        """ProductService.delete_product returns True when node is deleted."""
        from src.services.product_service import ProductService

        driver, session, result = _make_mock_driver([{"deleted": 1}])

        svc = ProductService(driver)
        res = await svc.delete_product("tenant-1", "prod-1")

        assert res is True

    @pytest.mark.asyncio
    async def test_delete_product_not_found(self):
        """ProductService.delete_product returns False when node not found."""
        from src.services.product_service import ProductService

        driver, session, result = _make_mock_driver([{"deleted": 0}])

        svc = ProductService(driver)
        res = await svc.delete_product("tenant-1", "nonexistent")

        assert res is False

    @pytest.mark.asyncio
    async def test_add_feature(self):
        """ProductService.add_feature creates feature node and relationship."""
        from src.services.product_service import FeatureCreate, ProductService

        driver, session, result = _make_mock_driver(
            [{"feature": {"id": "feat-1", "name": "Auto-Discovery", "feature_type": "core"}}]
        )

        svc = ProductService(driver)
        fc = FeatureCreate(name="Auto-Discovery", description="Automatic discovery feature")
        res = await svc.add_feature("tenant-1", "prod-1", fc)

        assert res is not None
        assert res["name"] == "Auto-Discovery"

    @pytest.mark.asyncio
    async def test_match_signals_to_products(self):
        """ProductService.match_signals_to_products returns matched products."""
        from src.services.product_service import ProductService

        driver, session, result = _make_mock_driver([
            {
                "product": {"id": "prod-1", "name": "ValueEngine", "category": "SaaS"},
                "total_score": 3.5,
                "signal_count": 3,
                "top_matches": [
                    {"signal_name": "slow sales cycle", "capability_name": "deal acceleration", "score": 1.5},
                ],
            }
        ])

        svc = ProductService(driver)
        res = await svc.match_signals_to_products("tenant-1")

        assert len(res) == 1
        assert res[0]["product"]["name"] == "ValueEngine"
        assert res[0]["signal_count"] == 3

    @pytest.mark.asyncio
    async def test_get_portfolio_summary(self):
        """ProductService.get_portfolio_summary returns aggregate stats."""
        from src.services.product_service import ProductService

        driver, session, result = _make_mock_driver([{
            "total_products": 10,
            "total_features": 45,
            "total_capabilities": 20,
            "categories": ["SaaS", "Platform", None],
            "avg_features_per_product": 4.5,
            "avg_capabilities_per_product": 2.0,
        }])

        svc = ProductService(driver)
        res = await svc.get_portfolio_summary("tenant-1")

        assert res["total_products"] == 10
        assert res["total_features"] == 45
        assert "SaaS" in res["categories"]
        assert None not in res["categories"]  # Nulls filtered out

    @pytest.mark.asyncio
    async def test_get_capability_coverage(self):
        """ProductService.get_capability_coverage returns coverage list."""
        from src.services.product_service import ProductService

        driver, session, result = _make_mock_driver([
            {
                "capability": {"id": "c1", "name": "Deal Acceleration"},
                "products": [{"id": "p1", "name": "ValueEngine"}],
                "signal_demand": 5,
                "status": "covered",
            },
            {
                "capability": {"id": "c2", "name": "ROI Calculation"},
                "products": [],
                "signal_demand": 3,
                "status": "gap",
            },
        ])

        svc = ProductService(driver)
        res = await svc.get_capability_coverage("tenant-1")

        assert len(res) == 2
        assert res[0]["status"] == "covered"
        assert res[1]["status"] == "gap"


# ---------------------------------------------------------------------------
# Task 1.3 — Evidence Library: Service Tests
# ---------------------------------------------------------------------------


class TestCaseStudyService:
    """Unit tests for CaseStudyService (Task 1.3)."""

    @pytest.mark.asyncio
    async def test_create_case_study(self):
        """CaseStudyService.create stores Evidence node and returns result."""
        from src.services.case_study_service import CaseStudy, CaseStudyService

        cs_id = str(uuid.uuid4())
        driver, session, result = _make_mock_driver(
            [{"id": cs_id, "title": "Healthcare Win", "industry": "healthcare"}]
        )

        svc = CaseStudyService(driver)
        cs = CaseStudy(
            tenant_id="tenant-1",
            title="Healthcare Win",
            content="A major healthcare provider reduced costs by 40% using our platform." * 3,
            industry="healthcare",
            company_name="MedCorp",
            company_size="enterprise",
            outcomes=[{"metric": "cost_reduction", "improvement_pct": 40.0}],
            time_to_value_days=90,
            deal_size_usd=500000.0,
        )
        res = await svc.create(cs)

        assert res["status"] == "created"
        assert res["title"] == "Healthcare Win"
        session.run.assert_called()

    @pytest.mark.asyncio
    async def test_create_case_study_rejects_tenant_mismatch(self):
        """CaseStudyService.create fails closed when caller tenant does not match case study tenant."""
        from value_fabric.shared.error_handling.exceptions import AuthorizationError
        from src.services.case_study_service import CaseStudy, CaseStudyService

        driver, _session, _result = _make_mock_driver([])
        svc = CaseStudyService(driver)
        cs = CaseStudy(
            tenant_id="tenant-1",
            title="Healthcare Win",
            content="A major healthcare provider reduced costs by 40% using our platform." * 3,
            industry="healthcare",
        )

        with pytest.raises(AuthorizationError):
            await svc.create(cs, tenant_id="tenant-2")

    @pytest.mark.asyncio
    async def test_get_case_study_found(self):
        """CaseStudyService.get returns case study dict when found."""
        from src.services.case_study_service import CaseStudyService

        driver, session, result = _make_mock_driver([{
            "case_study": {
                "id": "cs-1",
                "title": "Finance Win",
                "industry": "finance",
                "tenant_id": "tenant-1",
                "evidence_type": "case_study",
            },
            "linked_products": ["ValueEngine"],
            "linked_signals": ["slow sales cycle"],
        }])

        svc = CaseStudyService(driver)
        res = await svc.get("tenant-1", "cs-1")

        assert res is not None
        assert res["title"] == "Finance Win"
        assert "ValueEngine" in res["linked_products"]

    @pytest.mark.asyncio
    async def test_get_case_study_not_found(self):
        """CaseStudyService.get returns None when case study doesn't exist."""
        from src.services.case_study_service import CaseStudyService

        driver, session, result = _make_mock_driver([{
            "case_study": None,
            "linked_products": [],
            "linked_signals": [],
        }])

        svc = CaseStudyService(driver)
        res = await svc.get("tenant-1", "nonexistent")

        assert res is None

    @pytest.mark.asyncio
    async def test_update_case_study(self):
        """CaseStudyService.update modifies properties and returns result."""
        from src.services.case_study_service import CaseStudyService

        driver, session, result = _make_mock_driver([{
            "id": "cs-1",
            "title": "Updated Title",
        }])

        svc = CaseStudyService(driver)
        res = await svc.update("tenant-1", "cs-1", {"title": "Updated Title"})

        assert res is not None
        assert res["status"] == "updated"

    @pytest.mark.asyncio
    async def test_update_case_study_not_found(self):
        """CaseStudyService.update returns None for missing case study."""
        from src.services.case_study_service import CaseStudyService

        driver, session, result = _make_mock_driver([])

        svc = CaseStudyService(driver)
        res = await svc.update("tenant-1", "nonexistent", {"title": "X"})

        assert res is None

    @pytest.mark.asyncio
    async def test_update_protects_system_fields(self):
        """CaseStudyService.update strips protected fields (id, tenant_id, etc)."""
        from src.services.case_study_service import CaseStudyService

        driver, session, result = _make_mock_driver([{
            "id": "cs-1",
            "title": "Original",
        }])

        svc = CaseStudyService(driver)
        # Try to update protected fields — they should be stripped
        await svc.update("tenant-1", "cs-1", {
            "id": "hacked-id",
            "tenant_id": "hacked-tenant",
            "evidence_type": "hacked",
            "title": "Safe Update",
        })

        # Verify the Cypher call received only safe updates
        call_args = session.run.call_args
        params_passed = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs
        updates_passed = params_passed.get("updates")
        assert "id" not in updates_passed
        assert "tenant_id" not in updates_passed
        assert "evidence_type" not in updates_passed
        assert "title" in updates_passed

    @pytest.mark.asyncio
    async def test_delete_case_study(self):
        """CaseStudyService.delete returns True when node is removed."""
        from src.services.case_study_service import CaseStudyService

        driver, session, result = _make_mock_driver([{"deleted": 1}])

        svc = CaseStudyService(driver)
        res = await svc.delete("tenant-1", "cs-1")

        assert res is True

    @pytest.mark.asyncio
    async def test_delete_case_study_not_found(self):
        """CaseStudyService.delete returns False for missing case study."""
        from src.services.case_study_service import CaseStudyService

        driver, session, result = _make_mock_driver([{"deleted": 0}])

        svc = CaseStudyService(driver)
        res = await svc.delete("tenant-1", "nonexistent")

        assert res is False

    @pytest.mark.asyncio
    async def test_search_with_industry_filter(self):
        """CaseStudyService.search filters by industry."""
        from src.services.case_study_service import CaseStudyService

        driver, session = _make_multi_query_driver([
            # Count query
            [{"total": 2}],
            # List query
            [
                {
                    "case_study": {"id": "cs-1", "title": "HC Win", "industry": "healthcare", "products_used": [], "tags": []},
                    "linked_products": [],
                },
                {
                    "case_study": {"id": "cs-2", "title": "HC Win 2", "industry": "healthcare", "products_used": [], "tags": []},
                    "linked_products": [],
                },
            ],
        ])

        svc = CaseStudyService(driver)
        res = await svc.search("tenant-1", industry="healthcare")

        assert res["total"] == 2
        assert len(res["items"]) == 2

    @pytest.mark.asyncio
    async def test_get_by_industry(self):
        """CaseStudyService.get_by_industry returns industry→count mapping."""
        from src.services.case_study_service import CaseStudyService

        driver, session, result = _make_mock_driver([
            {"industry": "healthcare", "count": 5},
            {"industry": "finance", "count": 3},
        ])

        svc = CaseStudyService(driver)
        res = await svc.get_by_industry("tenant-1")

        assert res["healthcare"] == 5
        assert res["finance"] == 3

    @pytest.mark.asyncio
    async def test_get_by_product(self):
        """CaseStudyService.get_by_product returns product→count mapping."""
        from src.services.case_study_service import CaseStudyService

        driver, session, result = _make_mock_driver([
            {"product": "ValueEngine", "count": 8},
        ])

        svc = CaseStudyService(driver)
        res = await svc.get_by_product("tenant-1")

        assert res["ValueEngine"] == 8

    @pytest.mark.asyncio
    async def test_bulk_import_success(self):
        """CaseStudyService.bulk_import creates multiple case studies."""
        from src.services.case_study_service import CaseStudyService

        # Each create call returns a single record
        driver, session, result = _make_mock_driver(
            [{"id": "new-id", "title": "Imported", "industry": "tech"}]
        )

        svc = CaseStudyService(driver)
        batch = [
            {
                "title": "Case A",
                "content": "Content for case A that is long enough to pass validation." * 2,
                "industry": "tech",
            },
            {
                "title": "Case B",
                "content": "Content for case B that is long enough to pass validation." * 2,
                "industry": "finance",
            },
        ]
        res = await svc.bulk_import("tenant-1", batch)

        assert res["total"] == 2
        assert res["created"] == 2
        assert len(res["errors"]) == 0


# ---------------------------------------------------------------------------
# Task 1.3 — Evidence Library: Data Model Tests
# ---------------------------------------------------------------------------


class TestCaseStudyModel:
    """Unit tests for the CaseStudy data model."""

    def test_case_study_defaults(self):
        """CaseStudy sets sensible defaults for optional fields."""
        from src.services.case_study_service import CaseStudy

        cs = CaseStudy(
            tenant_id="t1",
            title="Test",
            content="Test content",
            industry="tech",
        )

        assert cs.id is not None  # UUID auto-generated
        assert cs.company_name == "Anonymous"
        assert cs.company_size == "unknown"
        assert cs.products_used == []
        assert cs.outcomes == []

    def test_case_study_to_node_properties(self):
        """CaseStudy.to_node_properties returns complete dict for Neo4j."""
        from src.services.case_study_service import CaseStudy

        cs = CaseStudy(
            tenant_id="t1",
            title="Big Win",
            content="Detailed narrative",
            industry="healthcare",
            company_name="MedCorp",
            outcomes=[{"metric": "cost", "improvement_pct": 30.0}],
        )
        props = cs.to_node_properties()

        assert props["evidence_type"] == "case_study"
        assert props["tenant_id"] == "t1"
        assert props["title"] == "Big Win"
        assert props["industry"] == "healthcare"
        assert "created_at" in props
        assert "updated_at" in props
        assert len(props["outcomes"]) == 1

    def test_case_study_outcome_to_dict(self):
        """CaseStudyOutcome.to_dict serializes all fields."""
        from src.services.case_study_service import CaseStudyOutcome

        outcome = CaseStudyOutcome(
            metric="revenue_increase",
            before_value="$1M",
            after_value="$1.5M",
            improvement_pct=50.0,
            time_to_achieve_days=180,
        )
        d = outcome.to_dict()

        assert d["metric"] == "revenue_increase"
        assert d["improvement_pct"] == 50.0
        assert d["time_to_achieve_days"] == 180

    def test_case_study_with_outcome_objects(self):
        """CaseStudy.to_node_properties handles CaseStudyOutcome objects."""
        from src.services.case_study_service import CaseStudy, CaseStudyOutcome

        outcome = CaseStudyOutcome(metric="cost", improvement_pct=25.0)
        cs = CaseStudy(
            tenant_id="t1",
            title="Test",
            content="Content",
            industry="tech",
            outcomes=[outcome],
        )
        props = cs.to_node_properties()

        assert props["outcomes"][0]["metric"] == "cost"
        assert props["outcomes"][0]["improvement_pct"] == 25.0


# ---------------------------------------------------------------------------
# Task 1.1 — Product Portfolio: Data Model Tests
# ---------------------------------------------------------------------------


class TestProductModels:
    """Unit tests for Product data transfer objects."""

    def test_product_create_defaults(self):
        """ProductCreate sets optional fields to empty lists (not None)."""
        from src.services.product_service import ProductCreate

        pc = ProductCreate(name="TestProd", description="A test product")

        assert pc.name == "TestProd"
        assert pc.category is None
        assert pc.target_personas == []  # Defaults to empty list
        assert pc.industries == []

    def test_product_create_with_all_fields(self):
        """ProductCreate accepts all fields."""
        from src.services.product_service import ProductCreate

        pc = ProductCreate(
            name="ValueEngine",
            description="Value selling platform",
            category="SaaS",
            sku="VE-001",
            pricing_model="subscription",
            target_personas=["VP Sales", "CRO"],
            industries=["technology", "finance"],
        )

        assert pc.name == "ValueEngine"
        assert pc.category == "SaaS"
        assert len(pc.target_personas) == 2
        assert "technology" in pc.industries

    def test_feature_create(self):
        """FeatureCreate captures name and description."""
        from src.services.product_service import FeatureCreate

        fc = FeatureCreate(name="AutoDiscover", description="Auto discovery feature")

        assert fc.name == "AutoDiscover"
        assert fc.description == "Auto discovery feature"
        assert fc.feature_type == "core"  # default
        assert fc.maturity == "ga"  # default

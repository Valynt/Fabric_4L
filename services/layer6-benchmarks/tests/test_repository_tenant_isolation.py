"""Hostile cross-tenant isolation tests for the Neo4j BenchmarkRepository."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from layer6_benchmarks.models.benchmark_dataset import (
    BenchmarkDataset,
    BenchmarkMetric,
    StatisticalProfile,
)
from layer6_benchmarks.repositories.benchmark_repository import BenchmarkRepository
from value_fabric.shared.database import MissingTenantContextError

HOSTILE_TENANT_ID = "00000000-0000-0000-0000-000000000222"
ISOLATED_TENANT_ID = "00000000-0000-0000-0000-000000000111"

@pytest.fixture
def mock_driver():
    driver = MagicMock()
    session = AsyncMock()
    # Support async with
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    driver.session.return_value = session
    return driver

@pytest.fixture
def repo(mock_driver):
    return BenchmarkRepository(mock_driver)

@pytest.fixture
def sample_dataset(request) -> BenchmarkDataset:
    """Create a sample dataset with a given tenant_id."""
    tenant_id = getattr(request, "param", "test-tenant-1")
    dataset = BenchmarkDataset(
        dataset_id=f"ds-{tenant_id}-123",
        tenant_id=tenant_id,
        name="Test Dataset",
        description="For isolation tests",
        industry="Technology",
        segment="Enterprise",
        geography="Global"
    )
    metric = BenchmarkMetric(
        name="revenue_growth",
        unit="percentage",
        description="YoY Growth",
        profile=StatisticalProfile(
            p10=Decimal("5.0"),
            p25=Decimal("10.0"),
            p50=Decimal("15.0"),
            p75=Decimal("20.0"),
            p90=Decimal("25.0"),
            mean=Decimal("16.0"),
            std_dev=Decimal("4.0"),
            sample_size=100
        )
    )
    dataset.add_metric(metric)
    return dataset

@pytest.mark.asyncio
async def test_repository_get_dataset_isolation(
    repo: BenchmarkRepository,
    mock_driver: AsyncMock,
    sample_dataset: BenchmarkDataset
):
    """Verify get_dataset executes with the provided tenant_id."""
    # We mock execute_read to just return None or something, 
    # but more importantly we verify the call arguments of _tx_get_dataset
    
    session = mock_driver.session.return_value
    
    await repo.get_dataset(sample_dataset.dataset_id, tenant_id=HOSTILE_TENANT_ID)
    
    session.execute_read.assert_called_once()
    # execute_read(func, *args, **kwargs)
    args, kwargs = session.execute_read.call_args
    assert args[0] == repo._tx_get_dataset
    assert args[1] == sample_dataset.dataset_id
    assert args[2] == HOSTILE_TENANT_ID  # Ensure tenant_id is correctly passed down

@pytest.mark.asyncio
async def test_repository_list_datasets_isolation(
    repo: BenchmarkRepository,
    mock_driver: AsyncMock
):
    """Verify list_datasets strictly filters by tenant_id in its query building."""
    session = mock_driver.session.return_value
    
    await repo.list_datasets(industry="Retail", tenant_id=ISOLATED_TENANT_ID)
    
    session.execute_read.assert_called_once()
    args, kwargs = session.execute_read.call_args
    assert args[0] == repo._tx_list_datasets
    assert args[1] == "Retail"
    assert args[2] is None  # segment
    assert args[3] == ISOLATED_TENANT_ID
    
    # Let's also test the raw query generation
    mock_tx = AsyncMock()
    mock_tx.run = AsyncMock(return_value=AsyncMock())
    mock_tx.run.return_value.__aiter__.return_value = []
    
    await repo._tx_list_datasets(mock_tx, industry="Retail", segment=None, tenant_id=ISOLATED_TENANT_ID)
    
    mock_tx.run.assert_called_once()
    call_args, call_kwargs = mock_tx.run.call_args
    query = call_args[0]
    
    # Ensure tenant condition is hardcoded as AND condition in the cypher query
    assert "d.tenant_id = $tenant_id" in query
    assert "d.industry = $industry" in query
    assert call_kwargs["tenant_id"] == ISOLATED_TENANT_ID
    assert call_kwargs["industry"] == "Retail"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("industry", "segment"),
    [
        (None, None),
        ("Retail", None),
        (None, "Enterprise"),
        ("Retail", "Enterprise"),
    ],
)
async def test_repository_list_datasets_query_always_contains_tenant_predicate(
    repo: BenchmarkRepository,
    industry: str | None,
    segment: str | None,
):
    """Verify all list filter combinations include tenant isolation in Cypher."""
    mock_tx = AsyncMock()
    mock_tx.run = AsyncMock(return_value=AsyncMock())
    mock_tx.run.return_value.__aiter__.return_value = []

    await repo._tx_list_datasets(
        mock_tx,
        industry=industry,
        segment=segment,
        tenant_id=ISOLATED_TENANT_ID,
    )

    mock_tx.run.assert_called_once()
    (query,), call_kwargs = mock_tx.run.call_args
    # Query allows tenant-scoped OR global_system datasets
    assert "(d.tenant_id = $tenant_id OR d.ownership_mode = 'global_system')" in query
    if industry:
        assert "AND d.industry = $industry" in query
    else:
        assert "d.industry = $industry" not in query
    if segment:
        assert "AND d.segment = $segment" in query
    else:
        assert "d.segment = $segment" not in query
    assert call_kwargs["tenant_id"] == ISOLATED_TENANT_ID


@pytest.mark.asyncio
async def test_repository_delete_dataset_isolation(
    repo: BenchmarkRepository,
    mock_driver: AsyncMock,
    sample_dataset: BenchmarkDataset
):
    """Verify delete_dataset executes with the provided tenant_id."""
    session = mock_driver.session.return_value

    await repo.delete_dataset(sample_dataset.dataset_id, tenant_id=HOSTILE_TENANT_ID)

    session.execute_write.assert_called_once()
    args, kwargs = session.execute_write.call_args
    assert args[0] == repo._tx_delete_dataset
    assert args[1] == sample_dataset.dataset_id
    assert args[2] == HOSTILE_TENANT_ID


@pytest.mark.asyncio
async def test_repository_get_dataset_cypher_requires_tenant_id(repo: BenchmarkRepository):
    """Verify get_dataset's raw Cypher filters by tenant_id."""
    mock_records = AsyncMock()
    mock_records.single = AsyncMock(return_value=None)
    mock_tx = AsyncMock()
    mock_tx.run = AsyncMock(return_value=mock_records)

    result = await repo._tx_get_dataset(mock_tx, "secret-dataset", "hostile-tenant")

    assert result is None
    mock_tx.run.assert_called_once()
    call_args, call_kwargs = mock_tx.run.call_args
    query = call_args[0]
    # Query allows tenant-scoped OR global_system datasets
    assert "WHERE d.tenant_id = $tenant_id OR d.ownership_mode = 'global_system'" in query
    assert call_kwargs["dataset_id"] == "secret-dataset"
    assert call_kwargs["tenant_id"] == "hostile-tenant"


@pytest.mark.asyncio
async def test_repository_delete_dataset_cypher_requires_tenant_id(repo: BenchmarkRepository):
    """Verify delete_dataset's raw Cypher filters by tenant_id."""
    mock_tx = AsyncMock()
    mock_tx.run = AsyncMock()

    await repo._tx_delete_dataset(mock_tx, "secret-dataset", "hostile-tenant")

    mock_tx.run.assert_called_once()
    call_args, call_kwargs = mock_tx.run.call_args
    query = call_args[0]
    assert "tenant_id: $tenant_id" in query
    assert call_kwargs["dataset_id"] == "secret-dataset"
    assert call_kwargs["tenant_id"] == "hostile-tenant"


@pytest.mark.asyncio
async def test_repository_denies_missing_tenant_on_read(repo: BenchmarkRepository):
    with pytest.raises(MissingTenantContextError, match="get_dataset"):
        await repo.get_dataset("secret-dataset", tenant_id=None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_repository_denies_missing_tenant_on_write(repo: BenchmarkRepository):
    dataset = BenchmarkDataset(
        dataset_id="missing-tenant-ds",
        tenant_id="",
        name="Missing Tenant Dataset",
        description="Should fail closed",
        industry="Technology",
        segment="Enterprise",
        geography="Global",
    )

    with pytest.raises(MissingTenantContextError, match="save_dataset"):
        await repo.save_dataset(dataset)

"""CI guardrail for tenant isolation in Layer 6 benchmark dataset queries."""

from pathlib import Path
import re

import pytest

from layer6_benchmarks.repositories.benchmark_repository import BenchmarkRepository


REPO_ROOT = Path(__file__).resolve().parents[2]
LAYER6_REPOSITORY_PATHS = [
    REPO_ROOT / "services" / "layer6-benchmarks" / "src" / "layer6_benchmarks" / "repositories",
]
BENCHMARK_DATASET_MATCH = re.compile(r"MATCH\s*\(d:BenchmarkDataset\)")
TENANT_PREDICATE = re.compile(r"d\.tenant_id\s*=\s*\$tenant_id")


def test_layer6_repository_paths_use_canonical_service_namespace() -> None:
    expected = (
        REPO_ROOT
        / "services"
        / "layer6-benchmarks"
        / "src"
        / "layer6_benchmarks"
        / "repositories"
    )
    assert LAYER6_REPOSITORY_PATHS == [expected]
    assert expected.is_dir()
    assert (expected / "benchmark_repository.py").is_file()


def test_benchmarkdataset_match_always_scopes_tenant() -> None:
    violations: list[str] = []
    for repo_path in LAYER6_REPOSITORY_PATHS:
        for py_file in repo_path.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            if BENCHMARK_DATASET_MATCH.search(text) and not TENANT_PREDICATE.search(text):
                violations.append(
                    f"{py_file.relative_to(REPO_ROOT)} defines BenchmarkDataset match logic without a tenant predicate"
                )

    assert not violations, "Layer 6 tenant-isolation query violations:\n" + "\n".join(violations)


class _DummyRunResult:
    async def single(self):
        return None

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


class _CaptureTx:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def run(self, query: str, **params):
        self.calls.append((query, params))
        return _DummyRunResult()


@pytest.mark.asyncio
async def test_list_datasets_query_uses_bound_tenant_parameter() -> None:
    tx = _CaptureTx()
    attacker_tenant = "tenant-a' OR '1'='1"

    await BenchmarkRepository._tx_list_datasets(tx, industry=None, segment=None, tenant_id=attacker_tenant)

    assert len(tx.calls) == 1
    query, params = tx.calls[0]
    assert "d.tenant_id = $tenant_id" in query
    assert params["tenant_id"] == attacker_tenant


@pytest.mark.asyncio
async def test_get_dataset_query_uses_bound_tenant_parameter() -> None:
    tx = _CaptureTx()
    attacker_tenant = "tenant-a' OR '1'='1"

    await BenchmarkRepository._tx_get_dataset(tx, dataset_id="manufacturing-efficiency-2024", tenant_id=attacker_tenant)

    assert len(tx.calls) == 1
    query, params = tx.calls[0]
    assert "d.tenant_id = $tenant_id" in query
    assert params["tenant_id"] == attacker_tenant


@pytest.mark.asyncio
async def test_delete_dataset_query_uses_bound_tenant_parameter() -> None:
    tx = _CaptureTx()
    attacker_tenant = "tenant-a' OR '1'='1"

    await BenchmarkRepository._tx_delete_dataset(tx, dataset_id="manufacturing-efficiency-2024", tenant_id=attacker_tenant)

    assert len(tx.calls) == 1
    query, params = tx.calls[0]
    assert "tenant_id: $tenant_id" in query
    assert params["tenant_id"] == attacker_tenant

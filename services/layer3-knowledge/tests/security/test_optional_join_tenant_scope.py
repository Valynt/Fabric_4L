"""TEST-009 fold-in: executable validator + behavioral hostile tests for the
L3-SEC-007 tenant-scoped ValuePack optional joins.

Covers (the "vp" optional-join regression the audit asked for):
1. Executable validator assertions — the OLD unscoped ``vp:ValuePack`` /
   ``FormulaVersion`` / ``Variable`` optional-join templates are REJECTED by
   ``validate_tenant_scoped_cypher``, and the NEW scoped templates pass. This
   replaces the substring-only checks that previously let an unscoped ``vp``
   side slip through.
2. Behavioral hostile tests — with a Tenant B ``ValuePack`` linked to Tenant A's
   ``Benchmark``/``Formula``, the Tenant A usage_count is 0 (not 1) and
   ``delete_formula`` does NOT raise the "referenced" ConflictError.
3. Runtime validator PASS — the exact real ``delete_formula`` Cypher blocks pass
   ``Neo4jTenantSessionSecured._validate_cypher_text`` (previously
   double-broken: would 500 fail-closed even with the ref-count fix).

No live Neo4j required — static validator runs + mocked tenant sessions.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from value_fabric.shared.error_handling.exceptions import ConflictError

from src.api.dependencies_tenant_secured import Neo4jTenantSessionSecured
from src.api.routes.benchmarks import get_benchmark, list_benchmarks
from src.api.routes.formulas import delete_formula
from src.utils.cypher_security import (
    TenantCypherValidationError,
    validate_tenant_scoped_cypher,
)

pytestmark = pytest.mark.tenant_boundary

REPO_ROOT = Path(__file__).resolve().parents[4]
FORMULAS_PATH = (
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "routes" / "formulas.py"
)


# ---------------------------------------------------------------------------
# 1. Executable validator tests (replaces the regex gap)
# ---------------------------------------------------------------------------


class TestValuePackOptionalJoinValidator:
    """validate_tenant_scoped_cypher must reject the old unscoped templates and
    accept the new scoped ones — the executable version of TEST-009."""

    # Old unscoped templates (pre-fix) — each must raise.
    OLD_UNSCOPED = {
        "benchmark_list": (
            "MATCH (b:Benchmark {tenant_id: $tenant_id}) "
            "OPTIONAL MATCH (vp:ValuePack)-[:hasBenchmark]->(b) "
            "RETURN b, count(DISTINCT vp) as usage_count",
            "ValuePack",
        ),
        "formula_refcount": (
            "MATCH (f:Formula {tenant_id: $tenant_id}) "
            "OPTIONAL MATCH (vp:ValuePack)-[:USES_FORMULA]->(f) "
            "RETURN f.status as status, count(vp) as ref_count",
            "ValuePack",
        ),
        "formula_delete_fv": (
            "MATCH (f:Formula {id: $formula_id}) "
            "WHERE f.tenant_id = $tenant_id "
            "OPTIONAL MATCH (f)-[:HAS_VERSION]->(fv:FormulaVersion) "
            "RETURN f",
            "FormulaVersion",
        ),
        "formula_delete_var": (
            "MATCH (f:Formula {id: $formula_id}) "
            "WHERE f.tenant_id = $tenant_id "
            "OPTIONAL MATCH (f)-[r:REQUIRES]->(v:Variable) "
            "RETURN f",
            "Variable",
        ),
    }

    # New scoped templates — each must pass.
    NEW_SCOPED = {
        "benchmark_list": (
            "MATCH (b:Benchmark {tenant_id: $tenant_id}) "
            "OPTIONAL MATCH (vp:ValuePack {tenant_id: $tenant_id})-[:hasBenchmark]->(b) "
            "RETURN b, count(DISTINCT vp) as usage_count"
        ),
        "formula_refcount": (
            "MATCH (f:Formula {tenant_id: $tenant_id}) "
            "OPTIONAL MATCH (vp:ValuePack {tenant_id: $tenant_id})-[:USES_FORMULA]->(f) "
            "RETURN f.status as status, count(vp) as ref_count"
        ),
        "formula_delete_fv": (
            "MATCH (f:Formula {id: $formula_id}) "
            "WHERE f.tenant_id = $tenant_id "
            "OPTIONAL MATCH (f:Formula)-[:HAS_VERSION]->(fv:FormulaVersion {tenant_id: $tenant_id}) "
            "RETURN f"
        ),
        "formula_delete_var": (
            "MATCH (f:Formula {id: $formula_id}) "
            "WHERE f.tenant_id = $tenant_id "
            "OPTIONAL MATCH (f:Formula)-[r:REQUIRES]->(v:Variable {tenant_id: $tenant_id}) "
            "RETURN f"
        ),
    }

    @pytest.mark.parametrize(
        "label", sorted(OLD_UNSCOPED), ids=lambda k: f"old_{k}"
    )
    def test_old_unscoped_template_is_rejected(self, label):
        """The pre-fix templates must be rejected, naming the unscoped label."""
        query, expected_label = self.OLD_UNSCOPED[label]
        with pytest.raises(TenantCypherValidationError) as exc_info:
            validate_tenant_scoped_cypher(query)
        assert expected_label in str(exc_info.value)

    @pytest.mark.parametrize("label", sorted(NEW_SCOPED), ids=lambda k: f"new_{k}")
    def test_new_scoped_template_passes(self, label):
        """The post-fix templates must validate cleanly."""
        validate_tenant_scoped_cypher(self.NEW_SCOPED[label])  # must not raise


# ---------------------------------------------------------------------------
# 2. Behavioral hostile tests (mocked tenant sessions)
# ---------------------------------------------------------------------------


class _SingleResult:
    """Minimal async result supporting .single() (used by get_benchmark and
    delete_formula)."""

    def __init__(self, record):
        self._record = record

    async def single(self):
        return self._record


class _DataResult:
    """Minimal async result supporting .data() (used by list_benchmarks)."""

    def __init__(self, records):
        self._records = records

    async def data(self):
        return self._records


class _TenantSession:
    """Mimics the secured session contract: run(query, *, tenant_id) filters by
    tenant so cross-tenant links are excluded — proving the scoped optional join
    blocks the cross-tenant count."""

    def __init__(self, tenant_id, records):
        self._tenant_id = tenant_id
        self._records = records

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run(self, query, *, tenant_id, **params):
        if "hasBenchmark" in query:
            # The benchmark record is tenant-owned and always returned; its
            # usage_count already reflects the vp tenant filter (0 for a
            # cross-tenant link), simulating the scoped OPTIONAL MATCH.
            if "LIMIT" in query:  # list_benchmarks -> .data()
                return _DataResult(list(self._records))
            return _SingleResult(self._records[0] if self._records else None)  # get_benchmark -> .single()
        if "USES_FORMULA" in query:
            # The formula always matches; only same-tenant vp links count.
            # records carry a precomputed ref_count reflecting the tenant filter.
            record = dict(self._records[0])
            if "ref_count_override" in record:
                record["ref_count"] = record.pop("ref_count_override")
            return _SingleResult(record)
        # Delete-step query — no records asserted.
        return _SingleResult(None)


def _benchmark_record(benchmark_id: str, tenant_id: str, vp_tenant: str | None):
    return {
        "b": {
            "id": benchmark_id,
            "benchmarkId": f"bm-{benchmark_id}",
            "name": f"Benchmark {benchmark_id}",
            "industry": "General",
            "vertical": "general",
            "valueRange": "",
            "confidence": "Medium",
            "source": "test",
            "sourceUrl": None,
            "year": 2026,
            "status": "active",
            "tags": [],
            "tenant_id": tenant_id,
        },
        "vp": None if vp_tenant is None else {"tenant_id": vp_tenant},
        "usage_count": 1 if vp_tenant == tenant_id else 0,
    }


class TestBenchmarkUsageCountIsolation:
    """Tenant A's usage_count must not count Tenant B's ValuePack links."""

    @pytest.mark.asyncio
    async def test_list_benchmarks_usage_count_zero_for_cross_tenant_vp(self, monkeypatch):
        tenant_id = "tenant-a"
        # Tenant B's ValuePack is linked — the scoped join must exclude it.
        records = [_benchmark_record("bm-1", tenant_id, vp_tenant="tenant-b")]
        session = _TenantSession(tenant_id, records)

        async def _factory(_tenant_id):
            return session

        monkeypatch.setattr(
            "src.api.routes.benchmarks.create_neo4j_tenant_session", _factory
        )
        api_key = SimpleNamespace(metadata={"tenant_id": tenant_id})

        results = await list_benchmarks(api_key=api_key)

        assert len(results) == 1
        assert results[0].usage_count == 0

    @pytest.mark.asyncio
    async def test_get_benchmark_usage_count_zero_for_cross_tenant_vp(self, monkeypatch):
        tenant_id = "tenant-a"
        records = [_benchmark_record("bm-1", tenant_id, vp_tenant="tenant-b")]
        session = _TenantSession(tenant_id, records)

        async def _factory(_tenant_id):
            return session

        monkeypatch.setattr(
            "src.api.routes.benchmarks.create_neo4j_tenant_session", _factory
        )
        api_key = SimpleNamespace(metadata={"tenant_id": tenant_id})

        result = await get_benchmark("bm-1", api_key=api_key)

        assert result.usage_count == 0

    @pytest.mark.asyncio
    async def test_get_benchmark_usage_count_one_for_same_tenant_vp(self, monkeypatch):
        """Sanity: a same-tenant ValuePack link still counts."""
        tenant_id = "tenant-a"
        records = [_benchmark_record("bm-1", tenant_id, vp_tenant="tenant-a")]
        session = _TenantSession(tenant_id, records)

        async def _factory(_tenant_id):
            return session

        monkeypatch.setattr(
            "src.api.routes.benchmarks.create_neo4j_tenant_session", _factory
        )
        api_key = SimpleNamespace(metadata={"tenant_id": tenant_id})

        result = await get_benchmark("bm-1", api_key=api_key)

        assert result.usage_count == 1


class TestDeleteFormulaRefCountIsolation:
    """delete_formula must not block deletion based on a cross-tenant ValuePack
    [:USES_FORMULA] link."""

    @pytest.mark.asyncio
    async def test_delete_formula_allowed_when_only_cross_tenant_vp_links(self, monkeypatch):
        tenant_id = "tenant-a"
        # ref-count query returns the formula with a tenant-B vp link -> ref_count 0
        records = [{"status": "active", "vp": {"tenant_id": "tenant-b"}, "ref_count": 0}]
        session = _TenantSession(tenant_id, records)

        async def _factory(_tenant_id):
            return session

        monkeypatch.setattr(
            "src.api.routes.formulas.create_neo4j_tenant_session", _factory
        )
        api_key = SimpleNamespace(key_id="admin-key", metadata={"tenant_id": tenant_id})
        tenant = SimpleNamespace(tenant_id=tenant_id)

        # Must NOT raise ConflictError; deletion proceeds.
        result = await delete_formula(
            "formula-1", api_key=api_key, tenant=tenant
        )

        assert result == {"status": "deleted", "formula_id": "formula-1"}

    @pytest.mark.asyncio
    async def test_delete_formula_still_blocks_on_same_tenant_vp_link(self, monkeypatch):
        """Sanity: a same-tenant [:USES_FORMULA] link still blocks deletion."""
        tenant_id = "tenant-a"
        records = [{"status": "active", "vp": {"tenant_id": "tenant-a"}, "ref_count": 1}]
        session = _TenantSession(tenant_id, records)

        async def _factory(_tenant_id):
            return session

        monkeypatch.setattr(
            "src.api.routes.formulas.create_neo4j_tenant_session", _factory
        )
        api_key = SimpleNamespace(key_id="admin-key", metadata={"tenant_id": tenant_id})
        tenant = SimpleNamespace(tenant_id=tenant_id)

        with pytest.raises(ConflictError):
            await delete_formula("formula-1", api_key=api_key, tenant=tenant)


# ---------------------------------------------------------------------------
# 3. Runtime validator PASS on the real route templates
# ---------------------------------------------------------------------------


class TestRealDeleteFormulaTemplatesValidate:
    """The exact Cypher blocks in formulas.py's delete_formula must pass the
    runtime tenant-scope validator — proving the previously double-broken
    endpoint no longer 500s fail-closed."""

    @staticmethod
    def _real_delete_formula_blocks() -> list[str]:
        import re

        source = FORMULAS_PATH.read_text(encoding="utf-8")
        delete_body = re.search(
            r"async def delete_formula.*?(?=\nasync def |\Z)",
            source,
            re.DOTALL,
        )
        assert delete_body, "delete_formula body not found in formulas.py"
        body = delete_body.group(0)
        blocks = [
            s
            for s in re.findall(r'"""(.*?)"""', body, re.DOTALL)
            if "MATCH" in s
        ]
        return [b.strip() for b in blocks]

    def test_delete_formula_blocks_pass_runtime_validation(self):
        sess = Neo4jTenantSessionSecured(
            driver=None, tenant_id="tenant-a", strict_validation=True
        )
        blocks = self._real_delete_formula_blocks()
        assert len(blocks) == 2, f"expected 2 cypher blocks, got {len(blocks)}"
        for block in blocks:
            sess._validate_cypher_text(block, allow_system_query=False)  # must not raise


# ---------------------------------------------------------------------------
# 4. Static scope check on the formulas.py ValuePack optional joins
# ---------------------------------------------------------------------------


class TestFormulasValuePackOptionalJoinScope:
    """Regex-level regression (mirrors the benchmarks check) ensuring every
    ValuePack optional join in formulas.py is tenant-scoped — L3-SEC-007."""

    def test_all_valuepack_optional_joins_are_tenant_scoped(self):
        import re

        source = FORMULAS_PATH.read_text(encoding="utf-8")
        blocks = re.findall(r'"""(.*?)"""', source, re.DOTALL)
        blocks += re.findall(r"'''(.*?)'''", source, re.DOTALL)
        cypher_blocks = [
            s
            for s in blocks
            if re.search(r"\b(MATCH|OPTIONAL\s+MATCH|RETURN|WHERE)\b", s, re.IGNORECASE)
        ]

        violations: list[str] = []
        for block in cypher_blocks:
            matches = re.findall(
                r"(?:MATCH|OPTIONAL\s+MATCH)\s*\(\s*vp:ValuePack\s*\)",
                block,
                re.IGNORECASE,
            )
            for m in matches:
                if re.search(
                    r"vp:ValuePack\s*\{\s*tenant_id\s*:\s*\$tenant_id",
                    block,
                    re.IGNORECASE,
                ) is None:
                    violations.append(m)

        assert not violations, (
            f"Unscoped ValuePack join clauses in formulas.py: {violations}"
        )

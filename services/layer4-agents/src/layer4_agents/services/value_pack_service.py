from __future__ import annotations

"""Value Pack Service implementation for Layer 4 Agents.

Neo4j-backed implementation of the Value Pack domain service.
"""


import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from neo4j import AsyncDriver
from neo4j.exceptions import Neo4jError, ServiceUnavailable

logger = logging.getLogger(__name__)

from layer4_agents.services.tenant_cypher import fetch_tenant_validated_records

from ..interfaces.value_pack_service import (
    BenchmarkRef,
    FormulaRef,
    IValuePackService,
    PackExecutionRequest,
    PackExecutionResult,
    PackStatus,
    ValueDriverRef,
    ValuePack,
)
from ..models.tool_schemas import EvaluateFormulaInput
from ..tools.calculation_tools import EvaluateFormulaTool


class Neo4jValuePackService(IValuePackService):
    """Neo4j-backed Value Pack service implementation."""

    def __init__(self, driver: AsyncDriver):
        self._driver = driver

    async def list_packs(
        self,
        tenant_id: str,
        industry: str | None = None,
        status: PackStatus | None = None,
    ) -> list[ValuePack]:
        """List available Value Packs from Neo4j."""
        query = """
        MATCH (vp:ValuePack {tenant_id: $tenant_id})
        WHERE ($industry IS NULL OR vp.industry = $industry)
          AND ($status IS NULL OR vp.status = $status)
        OPTIONAL MATCH (vp)-[:hasDriver]->(vd:ValueDriver)
        OPTIONAL MATCH (vp)-[:hasFormula]->(f:Formula)
        OPTIONAL MATCH (vp)-[:hasBenchmark]->(b:BenchmarkDataset)
        RETURN vp,
               collect(DISTINCT vd) as drivers,
               collect(DISTINCT f) as formulas,
               collect(DISTINCT b) as benchmarks
        """

        try:
            records = await fetch_tenant_validated_records(
                driver=self._driver,
                query=query,
                params={
                    "industry": industry,
                    "status": status.value if status else None,
                    "tenant_id": tenant_id,
                },
                tenant_id=tenant_id,
                operation="value_pack_service.list_packs",
            )

            packs = []
            for record in records:
                vp = record["vp"]
                drivers = [
                    ValueDriverRef(
                        driver_id=d["id"],
                        name=d.get("name", ""),
                        category=d.get("category", ""),
                        weight=1.0,
                    )
                    for d in record["drivers"]
                    if d
                ]
                formulas = [
                    FormulaRef(
                        formula_id=f["id"],
                        name=f.get("name", ""),
                        version=f.get("version", "1.0.0"),
                        variables=f.get("variables", []),
                    )
                    for f in record["formulas"]
                    if f
                ]
                benchmarks = [
                    BenchmarkRef(
                        dataset_id=b["id"],
                        metric=b.get("metric", ""),
                        industry=b.get("industry", ""),
                    )
                    for b in record["benchmarks"]
                    if b
                ]

                packs.append(
                    ValuePack(
                        pack_id=vp["id"],
                        name=vp.get("name", ""),
                        description=vp.get("description", ""),
                        industry=vp.get("industry", ""),
                        segment=vp.get("segment"),
                        status=PackStatus(vp.get("status", "draft")),
                        version=vp.get("version", "1.0.0"),
                        value_drivers=drivers,
                        formulas=formulas,
                        benchmarks=benchmarks,
                        created_at=datetime.fromisoformat(vp["createdAt"])
                        if "createdAt" in vp
                        else datetime.now(UTC),
                        updated_at=datetime.fromisoformat(vp["updatedAt"])
                        if "updatedAt" in vp
                        else None,
                        created_by=vp.get("createdBy"),
                    )
                )

            return packs
        except ServiceUnavailable as e:
            logger.error("Neo4j service unavailable", exc_info=True)
            raise RuntimeError("Database service unavailable") from e
        except Neo4jError as e:
            logger.error(f"Neo4j query failed: {e}", exc_info=True)
            raise RuntimeError(f"Database query failed: {e.code}") from e

    async def get_pack(self, pack_id: str, tenant_id: str) -> ValuePack | None:
        """Retrieve Value Pack by ID from Neo4j."""
        query = """
        MATCH (vp:ValuePack {id: $pack_id, tenant_id: $tenant_id})
        OPTIONAL MATCH (vp)-[:hasDriver]->(vd:ValueDriver)
        OPTIONAL MATCH (vp)-[:hasFormula]->(f:Formula)
        OPTIONAL MATCH (vp)-[:hasBenchmark]->(b:BenchmarkDataset)
        RETURN vp,
               collect(DISTINCT vd) as drivers,
               collect(DISTINCT f) as formulas,
               collect(DISTINCT b) as benchmarks
        """

        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={"pack_id": pack_id, "tenant_id": tenant_id},
            tenant_id=tenant_id,
            operation="value_pack_service.get_pack",
        )
        record = records[0] if records else None

        if not record:
            return None

        vp = record["vp"]
        drivers = [
            ValueDriverRef(
                driver_id=d["id"],
                name=d.get("name", ""),
                category=d.get("category", ""),
                weight=1.0,
            )
            for d in record["drivers"]
            if d
        ]
        formulas = [
            FormulaRef(
                formula_id=f["id"],
                name=f.get("name", ""),
                version=f.get("version", "1.0.0"),
                variables=f.get("variables", []),
            )
            for f in record["formulas"]
            if f
        ]
        benchmarks = [
            BenchmarkRef(
                dataset_id=b["id"],
                metric=b.get("metric", ""),
                industry=b.get("industry", ""),
            )
            for b in record["benchmarks"]
            if b
        ]

        return ValuePack(
                pack_id=vp["id"],
                name=vp.get("name", ""),
                description=vp.get("description", ""),
                industry=vp.get("industry", ""),
                segment=vp.get("segment"),
                status=PackStatus(vp.get("status", "draft")),
                version=vp.get("version", "1.0.0"),
                value_drivers=drivers,
                formulas=formulas,
                benchmarks=benchmarks,
                created_at=datetime.fromisoformat(vp["createdAt"])
                if "createdAt" in vp
                else datetime.now(UTC),
                updated_at=datetime.fromisoformat(vp["updatedAt"]) if "updatedAt" in vp else None,
                created_by=vp.get("createdBy"),
            )

    async def load_pack_into_workspace(
        self,
        pack_id: str,
        workspace_id: str,
        tenant_id: str,
    ) -> ValuePack:
        """Load pack into workspace for customization/execution."""
        pack = await self.get_pack(pack_id, tenant_id)
        if not pack:
            raise ValueError(f"Pack {pack_id} not found")

        # Mark as loaded in workspace
        query = """
        MATCH (vp:ValuePack {id: $pack_id, tenant_id: $tenant_id})
        SET vp.workspaceId = $workspace_id,
            vp.isLoaded = true,
            vp.loadedAt = $loaded_at
        RETURN vp
        """

        now = datetime.now(UTC).isoformat()
        await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={
                "pack_id": pack_id,
                "workspace_id": workspace_id,
                "tenant_id": tenant_id,
                "loaded_at": now,
            },
            tenant_id=tenant_id,
            operation="value_pack_service.load_pack_into_workspace",
        )

        pack.is_loaded = True
        pack.workspace_id = workspace_id
        return pack

    async def execute_pack(
        self,
        request: PackExecutionRequest,
        tenant_id: str,
    ) -> PackExecutionResult:
        """Execute pack workflow with provided variables."""
        execution_id = str(uuid.uuid4())

        # Get pack
        pack = await self.get_pack(request.pack_id, tenant_id)
        if not pack:
            return PackExecutionResult(
                execution_id=execution_id,
                pack_id=request.pack_id,
                status="failed",
                outputs={},
                errors=[f"Pack {request.pack_id} not found"],
            )

        # Store execution context
        query = """
        MATCH (vp:ValuePack {id: $pack_id, tenant_id: $tenant_id})
        CREATE (pe:PackExecution {
            id: $execution_id,
            packId: $pack_id,
            workspaceId: $workspace_id,
            status: 'running',
            variables: $variables,
            startedAt: $started_at
        })
        CREATE (vp)-[:HAS_EXECUTION]->(pe)
        RETURN pe
        """

        started_at = datetime.now(UTC).isoformat()
        await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={
                "pack_id": request.pack_id,
                "execution_id": execution_id,
                "workspace_id": request.workspace_id,
                "variables": request.variables,
                "started_at": started_at,
                "tenant_id": tenant_id,
            },
            tenant_id=tenant_id,
            operation="value_pack_service.execute_pack.create_execution",
        )

        # Execute formulas using calculation tool
        formula_tool = EvaluateFormulaTool()
        outputs: dict[str, Any] = {"pack_name": pack.name}
        errors: list[str] = []

        for formula in pack.formulas:
            # Build variables dict from request and formula defaults
            eval_vars = dict(request.variables)
            for var in formula.variables:
                if var not in eval_vars:
                    eval_vars[var] = 0.0  # Default value

            # Execute formula
            try:
                result = await formula_tool.execute(
                    EvaluateFormulaInput(
                        formula=formula.formula_id,  # Use formula ID as expression reference
                        variables=eval_vars,
                    )
                )
                if result.success and result.result is not None:
                    outputs[formula.name] = result.result
                else:
                    errors.append(f"Formula {formula.name} failed: {result.error}")
                    outputs[formula.name] = None
            except Exception as e:
                errors.append(f"Formula {formula.name} error: {e}")
                outputs[formula.name] = None

        outputs["formulas_evaluated"] = len(pack.formulas)
        outputs["variables_provided"] = len(request.variables)

        # Determine final status before DB update
        final_status = "success" if not errors else "partial" if outputs else "failed"

        # Update execution status
        complete_query = """
        MATCH (pe:PackExecution {id: $execution_id, tenant_id: $tenant_id})
        SET pe.status = $status,
            pe.outputs = $outputs,
            pe.errors = $errors,
            pe.completedAt = $completed_at
        """

        completed_at = datetime.now(UTC).isoformat()
        await fetch_tenant_validated_records(
            driver=self._driver,
            query=complete_query,
            params={
                "execution_id": execution_id,
                "status": final_status,
                "outputs": outputs,
                "errors": errors,
                "completed_at": completed_at,
                "tenant_id": tenant_id,
            },
            tenant_id=tenant_id,
            operation="value_pack_service.complete_execution",
        )

        return PackExecutionResult(
            execution_id=execution_id,
            pack_id=request.pack_id,
            status=final_status,
            outputs=outputs,
            errors=errors,
            completed_at=datetime.fromisoformat(completed_at),
        )

    async def customize_pack(
        self,
        pack_id: str,
        workspace_id: str,
        tenant_id: str,
        modifications: dict[str, Any],
    ) -> ValuePack:
        """Fork and customize pack for account-specific needs."""
        original = await self.get_pack(pack_id, tenant_id)
        if not original:
            raise ValueError(f"Pack {pack_id} not found")

        # Create new pack ID
        new_pack_id = str(uuid.uuid4())
        new_version = self._increment_version(original.version)

        query = """
        MATCH (old:ValuePack {id: $old_pack_id, tenant_id: $tenant_id})
        CREATE (new:ValuePack {
            id: $new_pack_id,
            name: $name,
            description: $description,
            industry: $industry,
            segment: $segment,
            status: 'draft',
            version: $version,
            workspaceId: $workspace_id,
            isLoaded: true,
            createdAt: $created_at,
            createdBy: $created_by,
            tenant_id: $tenant_id,
            forkedFrom: $old_pack_id
        })
        CREATE (new)-[:SUPERSEDES {type: 'fork'}]->(old)
        WITH new, old
        OPTIONAL MATCH (old)-[:hasDriver]->(vd:ValueDriver)
        FOREACH (d IN CASE WHEN vd IS NOT NULL THEN [vd] ELSE [] END |
            CREATE (new)-[:hasDriver]->(d)
        )
        WITH new, old
        OPTIONAL MATCH (old)-[:hasFormula]->(f:Formula)
        FOREACH (formula IN CASE WHEN f IS NOT NULL THEN [f] ELSE [] END |
            CREATE (new)-[:hasFormula]->(formula)
        )
        RETURN new
        """

        created_at = datetime.now(UTC).isoformat()
        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={
                "old_pack_id": pack_id,
                "new_pack_id": new_pack_id,
                "name": modifications.get("name", f"{original.name} (Custom)"),
                "description": modifications.get("description", original.description),
                "industry": modifications.get("industry", original.industry),
                "segment": modifications.get("segment", original.segment),
                "version": new_version,
                "workspace_id": workspace_id,
                "created_at": created_at,
                "created_by": modifications.get("user_id"),
                "tenant_id": tenant_id,
            },
            tenant_id=tenant_id,
            operation="value_pack_service.customize_pack",
        )
        record = records[0] if records else None

        if not record:
            raise ValueError("Failed to create customized pack")

        new_vp = record["new"]

        return ValuePack(
            pack_id=new_vp["id"],
            name=new_vp["name"],
            description=new_vp["description"],
            industry=new_vp["industry"],
            segment=new_vp.get("segment"),
            status=PackStatus.DRAFT,
            version=new_vp["version"],
            created_at=datetime.fromisoformat(new_vp["createdAt"]),
            workspace_id=workspace_id,
            is_loaded=True,
            created_by=new_vp.get("createdBy"),
        )

    async def save_pack(self, pack: ValuePack, tenant_id: str) -> ValuePack:
        """Save pack (create new version or update draft)."""
        query = """
        MERGE (vp:ValuePack {id: $pack_id, tenant_id: $tenant_id})
        SET vp.name = $name,
            vp.description = $description,
            vp.industry = $industry,
            vp.segment = $segment,
            vp.status = $status,
            vp.version = $version,
            vp.updatedAt = $updated_at
        RETURN vp
        """

        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={
                "pack_id": pack.pack_id,
                "name": pack.name,
                "description": pack.description,
                "industry": pack.industry,
                "segment": pack.segment,
                "status": pack.status.value,
                "version": pack.version,
                "updated_at": datetime.now(UTC).isoformat(),
                "tenant_id": tenant_id,
            },
            tenant_id=tenant_id,
            operation="value_pack_service.update_pack",
        )
        record = records[0] if records else None

        if record:
            vp = record["vp"]
            pack.updated_at = datetime.fromisoformat(vp["updatedAt"])

        return pack

    def _increment_version(self, version: str) -> str:
        """Increment patch version number."""
        parts = version.split(".")
        if len(parts) >= 3:
            try:
                major, minor, patch = parts[0], parts[1], int(parts[2])
                return f"{major}.{minor}.{patch + 1}"
            except ValueError:
                pass
        return "1.0.0"

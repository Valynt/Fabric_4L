from __future__ import annotations

"""Formula Governance Service implementation for Layer 4 Agents.

Neo4j-backed implementation of formula versioning and governance lifecycle.
"""


import re
import uuid
from datetime import UTC, datetime
from typing import Any

from neo4j import AsyncDriver
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..interfaces.formula_governance import (
    ActivationRequest,
    DeprecationRequest,
    FormulaDependency,
    FormulaGovernance,
    FormulaStatus,
    FormulaVersion,
    GovernanceTransitionResult,
    IFormulaApprovalWorkflow,
    IFormulaGovernanceService,
)
from ..metrics import get_metrics


class Neo4jFormulaGovernanceService_validate_activationResult(TypedDictModel):
    can_activate: bool
    errors: list[Any]
    warnings: list[Any]


class Neo4jFormulaGovernanceService(IFormulaGovernanceService, IFormulaApprovalWorkflow):
    """Neo4j-backed Formula Governance service implementation."""

    def __init__(self, driver: AsyncDriver):
        self._driver = driver

    async def _tenant_id_for_formula(self, formula_id: str, tenant_id: str) -> str:
        """Look up the tenant_id for a formula, scoped to the caller's tenant.

        Requires the caller's tenant_id so the lookup is constrained to the
        authenticated tenant's graph partition — prevents cross-tenant ID
        collisions from returning a foreign tenant's ID.
        """
        query = "MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id}) RETURN f.tenant_id as tenant_id"
        async with self._driver.session() as session:
            result = await session.run(query, formula_id=formula_id, tenant_id=tenant_id)
            record = await result.single()
            return record["tenant_id"] if record and record.get("tenant_id") else tenant_id

    async def get_governance(self, formula_id: str, tenant_id: str) -> FormulaGovernance | None:
        """Retrieve governance metadata for formula from Neo4j."""
        query = """
        MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id})
        OPTIONAL MATCH (f)-[:HAS_VERSION]->(fv:FormulaVersion)
        OPTIONAL MATCH (f)-[:DEPENDS_ON]->(dep:Formula {tenant_id: $tenant_id})
        OPTIONAL MATCH (other:Formula {tenant_id: $tenant_id})-[:DEPENDS_ON]->(f)
        RETURN f,
               collect(DISTINCT fv) as versions,
               collect(DISTINCT {id: dep.id, type: 'outgoing'}) as outgoing_deps,
               collect(DISTINCT {id: other.id, type: 'incoming'}) as incoming_deps
        """

        async with self._driver.session() as session:
            result = await session.run(query, formula_id=formula_id, tenant_id=tenant_id)
            record = await result.single()

            if not record or not record["f"]:
                return None

            f = record["f"]
            versions_data = record["versions"]

            versions = []
            for v in versions_data:
                if v:
                    versions.append(
                        FormulaVersion(
                            version=v.get("version", "1.0.0"),
                            formula_id=formula_id,
                            status=FormulaStatus(v.get("status", "draft")),
                            created_at=datetime.fromisoformat(v["createdAt"])
                            if "createdAt" in v
                            else datetime.now(UTC),
                            created_by=v.get("createdBy", "system"),
                            change_summary=v.get("changeSummary", ""),
                            previous_version=v.get("previousVersion"),
                        )
                    )

            # Sort versions by semver
            versions.sort(key=lambda v: self._semver_key(v.version), reverse=True)

            # Build dependencies
            all_deps = []
            for d in record["outgoing_deps"]:
                if d["id"]:
                    all_deps.append(
                        FormulaDependency(
                            source_formula_id=formula_id,
                            target_formula_id=d["id"],
                            dependency_type="uses",
                        )
                    )
            for d in record["incoming_deps"]:
                if d["id"]:
                    all_deps.append(
                        FormulaDependency(
                            source_formula_id=d["id"],
                            target_formula_id=formula_id,
                            dependency_type="uses",
                        )
                    )

            current_version = f.get("version", "1.0.0")
            status = FormulaStatus(f.get("status", "draft"))

            return FormulaGovernance(
                formula_id=formula_id,
                current_version=current_version,
                status=status,
                versions=versions,
                owner=f.get("owner"),
                department=f.get("department"),
                review_cycle_days=f.get("reviewCycleDays", 90),
                approved_by=f.get("approvedBy"),
                approved_at=datetime.fromisoformat(f["approvedAt"]) if "approvedAt" in f else None,
                last_reviewed_at=datetime.fromisoformat(f["lastReviewedAt"])
                if "lastReviewedAt" in f
                else None,
                next_review_at=datetime.fromisoformat(f["nextReviewAt"])
                if "nextReviewAt" in f
                else None,
            )

    async def create_version(
        self,
        formula_id: str,
        tenant_id: str,
        new_version: str,
        change_summary: str,
        created_by: str,
    ) -> FormulaVersion:
        """Create new formula version in Neo4j."""
        # Validate semver format
        if not self._is_valid_semver(new_version):
            raise ValueError(f"Invalid semver format: {new_version}")

        now = datetime.now(UTC).isoformat()

        # Get current version as previous
        get_current_query = """
        MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id})
        RETURN f.version as current_version
        """

        async with self._driver.session() as session:
            result = await session.run(get_current_query, formula_id=formula_id, tenant_id=tenant_id)
            record = await result.single()
            previous_version = record["current_version"] if record else None

        # Create version node
        query = """
        MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id})
        CREATE (fv:FormulaVersion {
            id: $version_id,
            version: $version,
            formulaId: $formula_id,
            status: 'draft',
            createdAt: $created_at,
            createdBy: $created_by,
            changeSummary: $change_summary,
            previousVersion: $previous_version
        })
        CREATE (f)-[:HAS_VERSION]->(fv)
        SET f.version = $version,
            f.status = 'draft',
            f.updatedAt = $created_at
        RETURN fv
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                formula_id=formula_id,
                version_id=str(uuid.uuid4()),
                version=new_version,
                created_at=now,
                created_by=created_by,
                change_summary=change_summary,
                previous_version=previous_version,
            )
            record = await result.single()

            if not record:
                raise ValueError("Failed to create formula version")

            fv = record["fv"]

            return FormulaVersion(
                version=fv["version"],
                formula_id=formula_id,
                status=FormulaStatus.DRAFT,
                created_at=datetime.fromisoformat(fv["createdAt"]),
                created_by=fv["createdBy"],
                change_summary=fv["changeSummary"],
                previous_version=fv.get("previousVersion"),
            )

    async def list_versions(
        self,
        formula_id: str,
        tenant_id: str,
        include_retired: bool = False,
    ) -> list[FormulaVersion]:
        """List all versions of a formula from Neo4j."""
        query = """
        MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id})-[:HAS_VERSION]->(fv:FormulaVersion)
        WHERE $include_retired OR fv.status <> 'retired'
        RETURN fv
        ORDER BY fv.createdAt DESC
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                formula_id=formula_id,
                tenant_id=tenant_id,
                include_retired=include_retired,
            )
            records = await result.data()

            versions = []
            for r in records:
                fv = r["fv"]
                versions.append(
                    FormulaVersion(
                        version=fv["version"],
                        formula_id=formula_id,
                        status=FormulaStatus(fv.get("status", "draft")),
                        created_at=datetime.fromisoformat(fv["createdAt"])
                        if "createdAt" in fv
                        else datetime.now(UTC),
                        created_by=fv.get("createdBy", "system"),
                        change_summary=fv.get("changeSummary", ""),
                        previous_version=fv.get("previousVersion"),
                    )
                )

            return versions

    async def activate(
        self,
        request: ActivationRequest,
        tenant_id: str,
    ) -> GovernanceTransitionResult:
        """Activate a formula version in Neo4j."""
        now = datetime.now(UTC).isoformat()

        # Get current status
        check_query = """
        MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id})
        RETURN f.status as status, f.version as current_version
        """

        async with self._driver.session() as session:
            result = await session.run(check_query, formula_id=request.formula_id, tenant_id=tenant_id)
            record = await result.single()

            if not record:
                return GovernanceTransitionResult(
                    success=False,
                    formula_id=request.formula_id,
                    old_status=FormulaStatus.DRAFT,
                    new_status=FormulaStatus.DRAFT,
                    error_message="Formula not found",
                )

            old_status = FormulaStatus(record["status"] or "draft")
            record["current_version"]

            # Validate transition
            if old_status == FormulaStatus.ACTIVE:
                return GovernanceTransitionResult(
                    success=False,
                    formula_id=request.formula_id,
                    old_status=old_status,
                    new_status=old_status,
                    error_message="Formula is already active",
                )

            if old_status not in [FormulaStatus.APPROVED, FormulaStatus.DRAFT]:
                return GovernanceTransitionResult(
                    success=False,
                    formula_id=request.formula_id,
                    old_status=old_status,
                    new_status=old_status,
                    error_message=f"Cannot activate formula in {old_status.value} status",
                    requires_approval=old_status == FormulaStatus.UNDER_REVIEW,
                )

        # Perform activation
        query = """
        MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id})
        MATCH (f)-[:HAS_VERSION]->(fv:FormulaVersion {version: $version})
        SET f.status = 'active',
            f.version = $version,
            f.activatedAt = $activated_at,
            f.activatedBy = $activated_by,
            f.effectiveDate = $effective_date,
            fv.status = 'active'
        RETURN f
        """

        effective_date = (request.effective_date or datetime.now(UTC)).isoformat()

        async with self._driver.session() as session:
            result = await session.run(
                query,
                formula_id=request.formula_id,
                tenant_id=tenant_id,
                version=request.version,
                activated_at=now,
                activated_by=request.requested_by,
                effective_date=effective_date,
            )
            record = await result.single()

            if not record:
                return GovernanceTransitionResult(
                    success=False,
                    formula_id=request.formula_id,
                    old_status=old_status,
                    new_status=old_status,
                    error_message="Failed to activate formula",
                )

            return GovernanceTransitionResult(
                success=True,
                formula_id=request.formula_id,
                old_status=old_status,
                new_status=FormulaStatus.ACTIVE,
            )

    async def deprecate(
        self,
        request: DeprecationRequest,
        tenant_id: str,
    ) -> GovernanceTransitionResult:
        """Deprecate a formula in Neo4j."""
        datetime.now(UTC).isoformat()

        # Get current status
        check_query = """
        MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id})
        RETURN f.status as status
        """

        async with self._driver.session() as session:
            result = await session.run(check_query, formula_id=request.formula_id, tenant_id=tenant_id)
            record = await result.single()

            if not record:
                return GovernanceTransitionResult(
                    success=False,
                    formula_id=request.formula_id,
                    old_status=FormulaStatus.DRAFT,
                    new_status=FormulaStatus.DRAFT,
                    error_message="Formula not found",
                )

            old_status = FormulaStatus(record["status"] or "draft")

            if old_status in [FormulaStatus.DEPRECATED, FormulaStatus.RETIRED]:
                return GovernanceTransitionResult(
                    success=False,
                    formula_id=request.formula_id,
                    old_status=old_status,
                    new_status=old_status,
                    error_message=f"Formula is already {old_status.value}",
                )

        # Perform deprecation
        query = """
        MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id})
        SET f.status = 'deprecated',
            f.deprecatedAt = $deprecated_at,
            f.deprecatedBy = $deprecated_by,
            f.deprecationReason = $reason,
            f.replacementFormulaId = $replacement_id
        RETURN f
        """

        async with self._driver.session() as session:
            await session.run(
                query,
                formula_id=request.formula_id,
                deprecated_at=request.deprecation_date.isoformat(),
                deprecated_by=request.requested_by,
                reason=request.reason,
                replacement_id=request.replacement_formula_id,
            )

            return GovernanceTransitionResult(
                success=True,
                formula_id=request.formula_id,
                old_status=old_status,
                new_status=FormulaStatus.DEPRECATED,
            )

    async def get_dependencies(
        self,
        formula_id: str,
        tenant_id: str,
        direction: str = "outgoing",
    ) -> list[FormulaDependency]:
        """Get formula dependencies from Neo4j."""
        deps = []

        if direction in ["outgoing", "both"]:
            outgoing_query = """
            MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id})-[:DEPENDS_ON]->(dep:Formula)
            RETURN dep.id as dep_id
            """
            async with self._driver.session() as session:
                result = await session.run(outgoing_query, formula_id=formula_id, tenant_id=tenant_id)
                records = await result.data()
                for r in records:
                    deps.append(
                        FormulaDependency(
                            source_formula_id=formula_id,
                            target_formula_id=r["dep_id"],
                            dependency_type="uses",
                        )
                    )

        if direction in ["incoming", "both"]:
            incoming_query = """
            MATCH (other:Formula {tenant_id: $tenant_id})-[:DEPENDS_ON]->(f:Formula {id: $formula_id, tenant_id: $tenant_id})
            RETURN other.id as other_id
            """
            async with self._driver.session() as session:
                result = await session.run(incoming_query, formula_id=formula_id, tenant_id=tenant_id)
                records = await result.data()
                for r in records:
                    deps.append(
                        FormulaDependency(
                            source_formula_id=r["other_id"],
                            target_formula_id=formula_id,
                            dependency_type="uses",
                        )
                    )

        return deps

    async def validate_activation(
        self,
        formula_id: str,
        tenant_id: str,
        version: str,
    ) -> dict[str, Any]:
        """Validate if formula can be activated."""
        query = """
        MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id})
        OPTIONAL MATCH (f)-[:HAS_VERSION]->(fv:FormulaVersion {version: $version})
        OPTIONAL MATCH (f)-[:DEPENDS_ON]->(dep:Formula {tenant_id: $tenant_id})
        WHERE dep.status <> 'active'
        RETURN f.status as status,
               fv IS NOT NULL as version_exists,
               count(dep) as inactive_deps
        """

        async with self._driver.session() as session:
            result = await session.run(query, formula_id=formula_id, tenant_id=tenant_id, version=version)
            record = await result.single()

            if not record:
                return Neo4jFormulaGovernanceService_validate_activationResult.model_validate({
                    "can_activate": False,
                    "errors": ["Formula not found"],
                    "warnings": [],
                })


            errors = []
            warnings = []

            if not record["version_exists"]:
                errors.append(f"Version {version} does not exist")

            current_status = record["status"] or "draft"
            if current_status == "active":
                warnings.append("Formula is already active")
            elif current_status == "retired":
                errors.append("Cannot activate retired formula")

            inactive_deps = record["inactive_deps"]
            if inactive_deps > 0:
                warnings.append(f"Formula has {inactive_deps} inactive dependencies")

            return Neo4jFormulaGovernanceService_validate_activationResult.model_validate({
                "can_activate": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
            })


    # Approval Workflow Implementation

    async def submit_for_review(
        self,
        formula_id: str,
        tenant_id: str,
        version: str,
        submitted_by: str,
    ) -> GovernanceTransitionResult:
        """Submit formula for review."""
        resolved_tenant_id = await self._tenant_id_for_formula(formula_id, tenant_id)
        metrics = get_metrics()
        if metrics:
            metrics.inc_formula_approval_pending(resolved_tenant_id)
        return await self._transition_status(
            formula_id, version, FormulaStatus.DRAFT, FormulaStatus.UNDER_REVIEW, submitted_by
        )

    async def approve(
        self,
        formula_id: str,
        version: str,
        approved_by: str,
        comments: str | None = None,
    ) -> GovernanceTransitionResult:
        """Approve formula (admin only)."""
        now = datetime.now(UTC).isoformat()

        query = """
        MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id})
        MATCH (f)-[:HAS_VERSION]->(fv:FormulaVersion {version: $version})
        SET f.status = 'approved',
            f.approvedAt = $approved_at,
            f.approvedBy = $approved_by,
            f.approvalComments = $comments,
            fv.status = 'approved'
        RETURN f.tenant_id as tenant_id
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                formula_id=formula_id,
                version=version,
                approved_at=now,
                approved_by=approved_by,
                comments=comments,
            )
            record = await result.single()
            tenant_id = (record.get("tenant_id") or "unknown") if record else "unknown"

            if not record:
                return GovernanceTransitionResult(
                    success=False,
                    formula_id=formula_id,
                    old_status=FormulaStatus.UNDER_REVIEW,
                    new_status=FormulaStatus.UNDER_REVIEW,
                    error_message="Failed to approve formula",
                )

            metrics = get_metrics()
            if metrics:
                metrics.dec_formula_approval_pending(tenant_id)

            return GovernanceTransitionResult(
                success=True,
                formula_id=formula_id,
                old_status=FormulaStatus.UNDER_REVIEW,
                new_status=FormulaStatus.APPROVED,
            )

    async def reject(
        self,
        formula_id: str,
        version: str,
        rejected_by: str,
        reason: str,
    ) -> GovernanceTransitionResult:
        """Reject formula (admin only)."""
        now = datetime.now(UTC).isoformat()

        query = """
        MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id})
        MATCH (f)-[:HAS_VERSION]->(fv:FormulaVersion {version: $version})
        SET f.status = 'draft',
            f.rejectedAt = $rejected_at,
            f.rejectedBy = $rejected_by,
            f.rejectionReason = $reason,
            fv.status = 'draft'
        RETURN f.tenant_id as tenant_id
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                formula_id=formula_id,
                version=version,
                rejected_at=now,
                rejected_by=rejected_by,
                reason=reason,
            )
            record = await result.single()
            tenant_id = (record.get("tenant_id") or "unknown") if record else "unknown"

            if not record:
                return GovernanceTransitionResult(
                    success=False,
                    formula_id=formula_id,
                    old_status=FormulaStatus.UNDER_REVIEW,
                    new_status=FormulaStatus.UNDER_REVIEW,
                    error_message="Failed to reject formula",
                )

            metrics = get_metrics()
            if metrics:
                metrics.dec_formula_approval_pending(tenant_id)

            return GovernanceTransitionResult(
                success=True,
                formula_id=formula_id,
                old_status=FormulaStatus.UNDER_REVIEW,
                new_status=FormulaStatus.DRAFT,
            )

    async def _transition_status(
        self,
        formula_id: str,
        version: str,
        from_status: FormulaStatus,
        to_status: FormulaStatus,
        requested_by: str,
    ) -> GovernanceTransitionResult:
        """Helper for status transitions."""
        now = datetime.now(UTC).isoformat()

        check_query = """
        MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id})
        RETURN f.status as status
        """

        async with self._driver.session() as session:
            result = await session.run(check_query, formula_id=formula_id)
            record = await result.single()

            if not record:
                return GovernanceTransitionResult(
                    success=False,
                    formula_id=formula_id,
                    old_status=from_status,
                    new_status=from_status,
                    error_message="Formula not found",
                )

            current_status = FormulaStatus(record["status"] or "draft")

            if current_status != from_status:
                return GovernanceTransitionResult(
                    success=False,
                    formula_id=formula_id,
                    old_status=current_status,
                    new_status=current_status,
                    error_message=f"Formula is in {current_status.value} status, expected {from_status.value}",
                )

        # Perform transition
        query = """
        MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id})
        MATCH (f)-[:HAS_VERSION]->(fv:FormulaVersion {version: $version})
        SET f.status = $new_status,
            f.updatedAt = $updated_at,
            fv.status = $new_status
        RETURN f
        """

        async with self._driver.session() as session:
            await session.run(
                query,
                formula_id=formula_id,
                version=version,
                new_status=to_status.value,
                updated_at=now,
            )

            return GovernanceTransitionResult(
                success=True,
                formula_id=formula_id,
                old_status=from_status,
                new_status=to_status,
            )

    def _is_valid_semver(self, version: str) -> bool:
        """Validate semver format (X.Y.Z)."""
        pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-[a-zA-Z0-9.-]+)?(?:\+[a-zA-Z0-9.-]+)?$"
        return bool(re.match(pattern, version))

    def _semver_key(self, version: str) -> tuple:
        """Convert semver to sortable tuple."""
        try:
            parts = version.split("-")[0].split("+")[0].split(".")
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            return (0, 0, 0)

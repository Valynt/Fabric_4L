"""
Agent permission service for formula/benchmark application.

Phase 5: Add agent permission checks for formula/benchmark application
Issue: Agent permission checks for applying formulas/benchmarks

Ensures agents can only use approved formulas and benchmarks, and
checks tenant-scoped permissions for governance artifact usage.
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.benchmark_governance import BenchmarkDataset, BenchmarkStatus
from ..models.formula_governance import Formula, FormulaStatus
from ..models.policy_governance import Policy, PolicyApplication

logger = logging.getLogger(__name__)


class AgentPermissionError(PermissionError):
    """Raised when an agent lacks permission to use a governance artifact."""
    pass


class PolicyEvaluationError(RuntimeError):
    """Raised when policy evaluation fails and must fail closed."""


class AgentPermissionService:
    """
    Service for checking agent permissions for formula/benchmark application.

    Enforces that agents can only use approved governance artifacts and
    respects tenant-scoped permissions.
    """

    async def can_use_formula(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        formula_id: UUID,
        agent_id: str | None = None,
    ) -> tuple[bool, str]:
        """
        Check if an agent can use a formula.

        Args:
            db: Database session
            tenant_id: Tenant ID
            formula_id: Formula ID to check
            agent_id: Optional agent ID for logging

        Returns:
            Tuple of (can_use, reason)
        """
        # Get the formula
        result = await db.execute(
            select(Formula).where(
                and_(
                    Formula.id == formula_id,
                    Formula.tenant_id == tenant_id,
                )
            )
        )
        formula = result.scalar_one_or_none()

        if formula is None:
            return False, f"Formula {formula_id} not found in tenant {tenant_id}"

        # Check if formula is deprecated
        if formula.deprecated_at is not None:
            return False, f"Formula {formula_id} is deprecated: {formula.deprecation_reason or 'No reason provided'}"
        if not formula.is_active:
            return False, f"Formula {formula_id} is not active in tenant {tenant_id}"

        # Check if current version is approved
        if formula.current_version is None:
            return False, f"Formula {formula_id} has no approved version"

        # Get the current version
        from ..models.formula_governance import FormulaVersion

        version_result = await db.execute(
            select(FormulaVersion).where(
                and_(
                    FormulaVersion.formula_id == formula_id,
                    FormulaVersion.version == formula.current_version,
                    FormulaVersion.tenant_id == tenant_id,
                )
            )
        )
        version = version_result.scalar_one_or_none()

        if version is None:
            return False, f"Formula version {formula.current_version} not found"

        if version.status != FormulaStatus.APPROVED.value:
            return False, f"Formula version {formula.current_version} is not approved (status: {version.status})"

        logger.info(
            "Agent permission check passed for formula %s (agent: %s)",
            formula_id,
            agent_id or "unknown",
        )

        return True, f"Formula {formula.slug} version {formula.current_version} is approved"

    async def can_use_benchmark(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        benchmark_id: UUID,
        agent_id: str | None = None,
    ) -> tuple[bool, str]:
        """
        Check if an agent can use a benchmark.

        Args:
            db: Database session
            tenant_id: Tenant ID
            benchmark_id: Benchmark ID to check
            agent_id: Optional agent ID for logging

        Returns:
            Tuple of (can_use, reason)
        """
        # Get the benchmark
        result = await db.execute(
            select(BenchmarkDataset).where(
                and_(
                    BenchmarkDataset.id == benchmark_id,
                    BenchmarkDataset.tenant_id == tenant_id,
                )
            )
        )
        benchmark = result.scalar_one_or_none()

        if benchmark is None:
            return False, f"Benchmark {benchmark_id} not found in tenant {tenant_id}"

        # Check if benchmark is deprecated
        if benchmark.deprecated_at is not None:
            return False, f"Benchmark {benchmark_id} is deprecated: {benchmark.deprecation_reason or 'No reason provided'}"
        if not benchmark.is_active:
            return False, f"Benchmark {benchmark_id} is not active in tenant {tenant_id}"

        # Check if current version is approved
        if benchmark.current_version is None:
            return False, f"Benchmark {benchmark_id} has no approved version"

        # Get the current version
        from ..models.benchmark_governance import BenchmarkVersion

        version_result = await db.execute(
            select(BenchmarkVersion).where(
                and_(
                    BenchmarkVersion.benchmark_id == benchmark_id,
                    BenchmarkVersion.version == benchmark.current_version,
                    BenchmarkVersion.tenant_id == tenant_id,
                )
            )
        )
        version = version_result.scalar_one_or_none()

        if version is None:
            return False, f"Benchmark version {benchmark.current_version} not found"

        if version.status != BenchmarkStatus.APPROVED.value:
            return False, f"Benchmark version {benchmark.current_version} is not approved (status: {version.status})"

        # Check effective dates
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        if version.effective_from > now:
            return False, f"Benchmark version {benchmark.current_version} is not yet effective (effective from: {version.effective_from})"

        if version.effective_until is not None and version.effective_until < now:
            return False, f"Benchmark version {benchmark.current_version} has expired (effective until: {version.effective_until})"

        logger.info(
            "Agent permission check passed for benchmark %s (agent: %s)",
            benchmark_id,
            agent_id or "unknown",
        )

        return True, f"Benchmark {benchmark.slug} version {benchmark.current_version} is approved and effective"

    async def check_policy_compliance(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        entity_type: str,
        entity_id: UUID,
        entity_version: str | None = None,
    ) -> tuple[bool, list[dict]]:
        """
        Check if an entity complies with applicable policies.

        Args:
            db: Database session
            tenant_id: Tenant ID
            entity_type: Type of entity (formula, benchmark, assumption)
            entity_id: Entity ID
            entity_version: Optional entity version

        Returns:
            Tuple of (compliant, policy_results)
        """
        # Get active policies for this entity type
        result = await db.execute(
            select(Policy).where(
                and_(
                    Policy.tenant_id == tenant_id,
                    Policy.is_active.is_(True),
                )
            )
        )
        policies = result.scalars().all()

        if not policies:
            return True, []

        import asyncio
        db_lock = asyncio.Lock()

        async def locked_evaluate(p):
            async with db_lock:
                return await self._evaluate_policy(
                    db=db,
                    tenant_id=tenant_id,
                    policy=p,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_version=entity_version,
                )

        tasks = []
        applicable_policies = []

        for policy in policies:
            # Check if policy applies to this entity type
            applies_to = policy.applies_to_entity_types or []
            if entity_type not in applies_to:
                continue

            applicable_policies.append(policy)
            tasks.append(locked_evaluate(policy))

        if not tasks:
            return True, []

        policy_results = await asyncio.gather(*tasks)

        all_passed = True
        for policy, policy_result in zip(applicable_policies, policy_results):
            if policy.is_mandatory and policy_result["result"] != "passed":
                all_passed = False

        return all_passed, policy_results

    async def _evaluate_policy(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        policy: Policy,
        entity_type: str,
        entity_id: UUID,
        entity_version: str | None,
    ) -> dict[str, Any]:
        evaluation_inputs: dict[str, Any] = {
            "tenant_id": str(tenant_id),
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "entity_version": entity_version,
        }
        outcome = "failed"
        message = "Policy evaluation failed"
        try:
            evaluator = self._policy_evaluator(policy.policy_type)
            passed, message = await evaluator(db=db, tenant_id=tenant_id, entity_id=entity_id)
            outcome = "passed" if passed else ("warning" if not policy.is_mandatory else "failed")
        except PolicyEvaluationError as exc:
            message = str(exc) or "policy_evaluation_failed"
            outcome = "warning" if not policy.is_mandatory else "failed"
        except Exception:
            logger.exception("Unexpected policy evaluation error for policy %s", policy.id)
            message = "policy_evaluation_error"
            outcome = "failed"

        result = {
            "policy_id": str(policy.id),
            "policy_name": policy.name,
            "policy_type": policy.policy_type,
            "policy_version": policy.current_version,
            "is_mandatory": policy.is_mandatory,
            "severity": policy.severity,
            "result": outcome,
            "message": message,
            "evaluation_inputs": evaluation_inputs,
        }

        try:
            await self.record_policy_application(
                db=db,
                tenant_id=tenant_id,
                policy_id=policy.id,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_version=entity_version,
                result=result["result"],
                rule_results=[result],
                applied_by="policy_evaluator",
                context=evaluation_inputs,
            )
        except Exception as exc:  # pragma: no cover - defensive handling for audit persistence
            logger.exception("Failed to record policy application for policy %s", policy.id)
            audit_message = f"{result['message']}; audit write failed: {exc}"
            result["message"] = audit_message
            if policy.is_mandatory:
                result["result"] = "failed"

        return result

    def _policy_evaluator(self, policy_type: str):
        evaluators = {
            "formula_approval": self._evaluate_formula_approval_policy,
            "benchmark_approval": self._evaluate_benchmark_approval_policy,
            "assumption_approval": self._evaluate_assumption_approval_policy,
        }
        evaluator = evaluators.get(policy_type)
        if evaluator is None:
            raise PolicyEvaluationError(f"Unknown policy type: {policy_type}")
        return evaluator

    async def _evaluate_formula_approval_policy(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        entity_id: UUID,
    ) -> tuple[bool, str]:
        can_use, reason = await self.can_use_formula(db=db, tenant_id=tenant_id, formula_id=entity_id)
        return can_use, reason

    async def _evaluate_benchmark_approval_policy(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        entity_id: UUID,
    ) -> tuple[bool, str]:
        can_use, reason = await self.can_use_benchmark(db=db, tenant_id=tenant_id, benchmark_id=entity_id)
        return can_use, reason

    async def _evaluate_assumption_approval_policy(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        entity_id: UUID,
    ) -> tuple[bool, str]:
        _ = db, tenant_id, entity_id
        raise PolicyEvaluationError("assumption approval evaluation not implemented")

    async def require_formula_permission(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        formula_id: UUID,
        agent_id: str | None = None,
    ) -> None:
        """
        Require formula permission, raising error if not permitted.

        Args:
            db: Database session
            tenant_id: Tenant ID
            formula_id: Formula ID
            agent_id: Optional agent ID

        Raises:
            AgentPermissionError: If formula cannot be used
        """
        can_use, reason = await self.can_use_formula(db, tenant_id, formula_id, agent_id)
        if not can_use:
            logger.warning(
                "Agent permission denied for formula %s (agent: %s): %s",
                formula_id,
                agent_id or "unknown",
                reason,
            )
            raise AgentPermissionError(reason)

    async def require_benchmark_permission(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        benchmark_id: UUID,
        agent_id: str | None = None,
    ) -> None:
        """
        Require benchmark permission, raising error if not permitted.

        Args:
            db: Database session
            tenant_id: Tenant ID
            benchmark_id: Benchmark ID
            agent_id: Optional agent ID

        Raises:
            AgentPermissionError: If benchmark cannot be used
        """
        can_use, reason = await self.can_use_benchmark(db, tenant_id, benchmark_id, agent_id)
        if not can_use:
            logger.warning(
                "Agent permission denied for benchmark %s (agent: %s): %s",
                benchmark_id,
                agent_id or "unknown",
                reason,
            )
            raise AgentPermissionError(reason)

    async def record_policy_application(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        policy_id: UUID,
        entity_type: str,
        entity_id: UUID,
        entity_version: str | None = None,
        result: str = "passed",
        rule_results: list[dict] | None = None,
        applied_by: str | None = None,
        context: dict | None = None,
    ) -> PolicyApplication:
        """
        Record a policy application for audit purposes.

        Args:
            db: Database session
            tenant_id: Tenant ID
            policy_id: Policy ID
            entity_type: Entity type
            entity_id: Entity ID
            entity_version: Optional entity version
            result: Result of policy evaluation
            rule_results: Detailed rule results
            applied_by: Who applied the policy
            context: Additional context

        Returns:
            The created PolicyApplication record
        """
        application = PolicyApplication(
            tenant_id=tenant_id,
            policy_id=policy_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_version=entity_version,
            result=result,
            rule_results=rule_results,
            applied_by=applied_by or "system",
            context=context,
        )
        db.add(application)
        await db.flush()

        logger.info(
            "Recorded policy application for policy %s on entity %s/%s (result: %s)",
            policy_id,
            entity_type,
            entity_id,
            result,
        )

        return application

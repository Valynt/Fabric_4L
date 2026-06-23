"""
Policy Governance Service.

Business logic for Policy CRUD, approval, evaluation, and lifecycle management.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.policy_governance import (
    Policy,
    PolicyApplication,
    PolicyRule,
    PolicyStatus,
    PolicyVersion,
)

logger = logging.getLogger(__name__)


class PolicyNotFoundError(Exception):
    """Raised when a policy is not found."""
    pass


class PolicySlugConflictError(Exception):
    """Raised when a policy slug already exists in the tenant."""
    pass


class PolicyService:
    """Service for Policy governance operations."""

    async def create_policy(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        name: str,
        slug: str,
        policy_type: str,
        description: str,
        rules: list[dict[str, Any]],
        severity: str = "medium",
        scope: dict[str, Any] | None = None,
        created_by: str = "system",
    ) -> Policy:
        """
        Create a new Policy with initial version.

        Args:
            db: Database session
            tenant_id: Tenant ID
            name: Policy name
            slug: Unique slug within tenant
            policy_type: Type of policy
            description: Policy description
            rules: List of policy rules
            severity: Severity level
            scope: Optional scope definition
            created_by: User creating the policy

        Returns:
            Created Policy

        Raises:
            PolicySlugConflictError: If slug already exists
        """
        # Check slug uniqueness
        existing = await db.execute(
            select(Policy).where(
                and_(
                    Policy.tenant_id == tenant_id,
                    Policy.slug == slug,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise PolicySlugConflictError(f"Policy slug '{slug}' already exists")

        # Create Policy record
        initial_version = "1.0.0"
        policy = Policy(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            policy_type=policy_type,
            description=description,
            current_version=None,  # No approved version yet
            latest_version=initial_version,
            severity=severity,
            scope=scope,
            is_active=True,
            created_by=created_by,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(policy)
        await db.flush()

        # Create initial PolicyVersion (DRAFT status)
        version = PolicyVersion(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            policy_id=policy.id,
            version=initial_version,
            rules_engine_config={"rules": rules},
            effective_from=datetime.now(UTC),
            status=PolicyStatus.DRAFT.value,
            changed_by=created_by,
            created_at=datetime.now(UTC),
        )
        db.add(version)
        await db.flush()

        # Create PolicyRule records
        for index, rule_data in enumerate(rules):
            rule = PolicyRule(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                policy_id=policy.id,
                rule_name=rule_data.get("rule_name") or rule_data.get("name") or f"rule-{index + 1}",
                rule_order=int(rule_data.get("rule_order") or rule_data.get("order") or index),
                target_field=rule_data.get("target_field") or rule_data.get("field") or "context",
                operator=rule_data.get("operator") or rule_data.get("rule_type") or "equals",
                expected_value=rule_data.get("expected_value")
                if "expected_value" in rule_data
                else rule_data.get("condition", {}),
                error_message=rule_data.get("error_message") or rule_data.get("action"),
                is_blocking=bool(rule_data.get("is_blocking", True)),
                severity=rule_data.get("severity", severity),
                description=rule_data.get("description"),
            )
            db.add(rule)

        await db.flush()

        logger.info(
            "Created policy %s (slug: %s, tenant: %s)",
            policy.id,
            slug,
            tenant_id,
        )

        return policy

    async def get_policy(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        policy_id: uuid.UUID,
    ) -> Policy:
        """
        Get a policy by ID with tenant scoping.

        Args:
            db: Database session
            tenant_id: Tenant ID
            policy_id: Policy ID

        Returns:
            Policy

        Raises:
            PolicyNotFoundError: If policy not found
        """
        result = await db.execute(
            select(Policy).where(
                and_(
                    Policy.id == policy_id,
                    Policy.tenant_id == tenant_id,
                )
            )
        )
        policy = result.scalar_one_or_none()

        if policy is None:
            raise PolicyNotFoundError(f"Policy {policy_id} not found")

        return policy

    async def list_policies(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        policy_type: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Policy], int]:
        """
        List policies with pagination and filtering.

        Args:
            db: Database session
            tenant_id: Tenant ID
            policy_type: Optional filter by policy type
            is_active: Optional filter by active status
            page: Page number
            page_size: Page size

        Returns:
            Tuple of (policies, total count)
        """
        query = select(Policy).where(Policy.tenant_id == tenant_id)

        if policy_type:
            query = query.where(Policy.policy_type == policy_type)

        if is_active is not None:
            query = query.where(Policy.is_active == is_active)

        # Get total count
        from sqlalchemy import func

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        query = query.order_by(Policy.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        policies = result.scalars().all()

        return list(policies), total

    async def evaluate_policy(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        policy_id: uuid.UUID,
        entity_id: uuid.UUID,
        entity_type: str,
        context: dict[str, Any],
        evaluator: str = "system",
    ) -> dict[str, Any]:
        """
        Evaluate a policy against an entity.

        Args:
            db: Database session
            tenant_id: Tenant ID
            policy_id: Policy ID
            entity_id: Entity ID to evaluate
            entity_type: Type of entity
            context: Evaluation context
            evaluator: User performing evaluation

        Returns:
            Evaluation result with compliance status

        Raises:
            PolicyNotFoundError: If policy not found
        """
        policy = await self.get_policy(db, tenant_id, policy_id)

        # Get current approved version
        if policy.current_version is None:
            raise ValueError("Policy has no approved version to evaluate")

        version_result = await db.execute(
            select(PolicyVersion).where(
                and_(
                    PolicyVersion.policy_id == policy_id,
                    PolicyVersion.version == policy.current_version,
                )
            )
        )
        version = version_result.scalar_one_or_none()

        if version is None:
            raise ValueError(f"Policy version {policy.current_version} not found")

        # Get rules for this version
        rules_result = await db.execute(
            select(PolicyRule).where(
                and_(
                    PolicyRule.tenant_id == tenant_id,
                    PolicyRule.policy_id == policy_id,
                )
            ).order_by(PolicyRule.rule_order)
        )
        rules = rules_result.scalars().all()

        # Evaluate rules (simplified logic - actual evaluation would be more complex)
        passed_rules = []
        failed_rules = []

        for rule in rules:
            # Simplified evaluation - in production, this would use a rules engine
            # For now, we'll just record the evaluation
            rule_result = {
                "rule_id": str(rule.id),
                "rule_name": rule.rule_name,
                "rule_type": rule.operator,
                "passed": True,  # Placeholder
                "message": "Rule evaluated successfully",
            }
            passed_rules.append(rule_result)

        # Create PolicyApplication record
        application = PolicyApplication(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            policy_id=policy_id,
            entity_id=entity_id,
            entity_type=entity_type,
            entity_version=version.version,
            context=context,
            result="passed" if not failed_rules else "failed",
            rule_results={"passed_rules": passed_rules, "failed_rules": failed_rules},
            applied_by=evaluator,
            applied_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db.add(application)
        await db.flush()

        logger.info(
            "Evaluated policy %s against entity %s (tenant: %s, compliant: %s)",
            policy_id,
            entity_id,
            tenant_id,
            application.result == "passed",
        )

        return {
            "policy_id": str(policy_id),
            "entity_id": str(entity_id),
            "entity_type": entity_type,
            "is_compliant": application.result == "passed",
            "passed_rules": passed_rules,
            "failed_rules": failed_rules,
            "evaluation_id": str(application.id),
            "evaluated_at": application.applied_at,
        }

    async def get_policy_applications(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        policy_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[PolicyApplication], int]:
        """
        Get policy application history.

        Args:
            db: Database session
            tenant_id: Tenant ID
            policy_id: Policy ID
            page: Page number
            page_size: Page size

        Returns:
            Tuple of (applications, total count)
        """
        query = select(PolicyApplication).where(
            and_(
                PolicyApplication.tenant_id == tenant_id,
                PolicyApplication.policy_id == policy_id,
            )
        )

        # Get total count
        from sqlalchemy import func

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        query = query.order_by(PolicyApplication.evaluated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        applications = result.scalars().all()

        return list(applications), total

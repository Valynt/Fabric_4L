"""
Formula Governance Service.

Business logic for Formula CRUD, versioning, approval, and lifecycle management.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.approval_workflow import (
    ApprovalRequest,
    ApprovalStatus,
    EntityType,
)
from ..models.formula_governance import (
    Formula,
    FormulaParameter,
    FormulaStatus,
    FormulaVersion,
)
from ..services.approval_state_machine import ApprovalStateMachine

logger = logging.getLogger(__name__)


class FormulaNotFoundError(Exception):
    """Raised when a formula is not found."""
    pass


class FormulaSlugConflictError(Exception):
    """Raised when a formula slug already exists in the tenant."""
    pass


class FormulaVersionConflictError(Exception):
    """Raised when a formula version already exists."""
    pass


class FormulaService:
    """Service for Formula governance operations."""

    async def create_formula(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        name: str,
        slug: str,
        formula_type: str,
        expression: str,
        expression_language: str,
        input_schema: dict[str, Any],
        output_schema: dict[str, Any],
        parameters: list[dict[str, Any]] | None = None,
        description: str | None = None,
        created_by: str = "system",
    ) -> Formula:
        """
        Create a new Formula with initial version.

        Args:
            db: Database session
            tenant_id: Tenant ID
            name: Formula name
            slug: Unique slug within tenant
            formula_type: Type of formula
            expression: Formula expression
            expression_language: Expression language
            input_schema: JSON Schema for input validation
            output_schema: JSON Schema for output validation
            parameters: List of parameter definitions
            description: Optional description
            created_by: User creating the formula

        Returns:
            Created Formula

        Raises:
            FormulaSlugConflictError: If slug already exists
        """
        # Check slug uniqueness
        existing = await db.execute(
            select(Formula).where(
                and_(
                    Formula.tenant_id == tenant_id,
                    Formula.slug == slug,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise FormulaSlugConflictError(f"Formula slug '{slug}' already exists")

        # Create Formula record
        initial_version = "0.1.0"
        formula = Formula(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            formula_type=formula_type,
            description=description,
            current_version=None,  # No approved version yet
            latest_version=initial_version,
            input_schema=input_schema,
            output_schema=output_schema,
            is_active=True,
            created_by=created_by,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(formula)
        await db.flush()

        # Create initial FormulaVersion (DRAFT status)
        version = FormulaVersion(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            formula_id=formula.id,
            version=initial_version,
            expression=expression,
            expression_language=expression_language,
            status=FormulaStatus.DRAFT.value,
            changed_by=created_by,
            created_at=datetime.now(UTC),
        )
        db.add(version)
        await db.flush()

        # Create FormulaParameter records if provided
        if parameters:
            for param_data in parameters:
                param = FormulaParameter(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    formula_id=formula.id,
                    name=param_data.get("name"),
                    display_name=param_data.get("display_name"),
                    parameter_type=param_data.get("parameter_type"),
                    description=param_data.get("description"),
                    required=param_data.get("required", True),
                    default_value=param_data.get("default_value"),
                    min_value=param_data.get("min_value"),
                    max_value=param_data.get("max_value"),
                    allowed_values=param_data.get("allowed_values"),
                )
                db.add(param)

        await db.flush()

        logger.info(
            "Created formula %s (slug: %s, tenant: %s)",
            formula.id,
            slug,
            tenant_id,
        )

        return formula

    async def get_formula(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        formula_id: uuid.UUID,
    ) -> Formula:
        """
        Get a formula by ID with tenant scoping.

        Args:
            db: Database session
            tenant_id: Tenant ID
            formula_id: Formula ID

        Returns:
            Formula

        Raises:
            FormulaNotFoundError: If formula not found
        """
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
            raise FormulaNotFoundError(f"Formula {formula_id} not found")

        return formula

    async def list_formulas(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        formula_type: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Formula], int]:
        """
        List formulas with pagination and filtering.

        Args:
            db: Database session
            tenant_id: Tenant ID
            formula_type: Optional filter by formula type
            is_active: Optional filter by active status
            page: Page number
            page_size: Page size

        Returns:
            Tuple of (formulas, total count)
        """
        query = select(Formula).where(Formula.tenant_id == tenant_id)

        if formula_type:
            query = query.where(Formula.formula_type == formula_type)

        if is_active is not None:
            query = query.where(Formula.is_active == is_active)

        # Get total count
        from sqlalchemy import func

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        query = query.order_by(Formula.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        formulas = result.scalars().all()

        return list(formulas), total

    async def create_formula_version(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        formula_id: uuid.UUID,
        version: str,
        expression: str,
        expression_language: str,
        change_description: str | None = None,
        changed_by: str = "system",
    ) -> FormulaVersion:
        """
        Create a new version of a formula.

        Args:
            db: Database session
            tenant_id: Tenant ID
            formula_id: Formula ID
            version: Version string (semver)
            expression: Formula expression
            expression_language: Expression language
            change_description: Description of changes
            changed_by: User creating the version

        Returns:
            Created FormulaVersion

        Raises:
            FormulaNotFoundError: If formula not found
            FormulaVersionConflictError: If version already exists
        """
        # Get formula
        formula = await self.get_formula(db, tenant_id, formula_id)

        # Check version uniqueness
        existing = await db.execute(
            select(FormulaVersion).where(
                and_(
                    FormulaVersion.formula_id == formula_id,
                    FormulaVersion.version == version,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise FormulaVersionConflictError(f"Version {version} already exists")

        # Create new version
        new_version = FormulaVersion(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            formula_id=formula_id,
            version=version,
            expression=expression,
            expression_language=expression_language,
            status=FormulaStatus.DRAFT.value,
            change_description=change_description,
            changed_by=changed_by,
            created_at=datetime.now(UTC),
        )
        db.add(new_version)

        # Update Formula.latest_version
        formula.latest_version = version
        formula.updated_at = datetime.now(UTC)

        await db.flush()

        logger.info(
            "Created formula version %s for formula %s (tenant: %s)",
            version,
            formula_id,
            tenant_id,
        )

        return new_version

    async def submit_formula_version(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        formula_id: uuid.UUID,
        version: str,
        submitter: str,
        notes: str | None = None,
    ) -> FormulaVersion:
        """
        Submit a formula version for approval.

        Args:
            db: Database session
            tenant_id: Tenant ID
            formula_id: Formula ID
            version: Version string
            submitter: User submitting
            notes: Optional notes

        Returns:
            Updated FormulaVersion

        Raises:
            FormulaNotFoundError: If formula or version not found
        """
        # Get formula version
        result = await db.execute(
            select(FormulaVersion).where(
                and_(
                    FormulaVersion.formula_id == formula_id,
                    FormulaVersion.version == version,
                    FormulaVersion.tenant_id == tenant_id,
                )
            )
        )
        version_obj = result.scalar_one_or_none()

        if version_obj is None:
            raise FormulaNotFoundError(f"Formula version {version} not found")

        # Check status
        if version_obj.status != FormulaStatus.DRAFT.value:
            raise ValueError(f"Version {version} is not in DRAFT status")

        # Create ApprovalRequest
        approval_request = ApprovalRequest(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            entity_type=EntityType.FORMULA.value,
            entity_id=formula_id,
            entity_version=version,
            status=ApprovalStatus.PENDING.value,
            requested_by=submitter,
            requested_at=datetime.now(UTC),
            request_reason=notes,
        )
        db.add(approval_request)

        # Update version status
        version_obj.status = FormulaStatus.PENDING_APPROVAL.value
        version_obj.approval_request_id = approval_request.id
        version_obj.updated_at = datetime.now(UTC)

        await db.flush()

        logger.info(
            "Submitted formula version %s for approval (formula: %s, tenant: %s)",
            version,
            formula_id,
            tenant_id,
        )

        return version_obj

    async def approve_formula_version(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        formula_id: uuid.UUID,
        version: str,
        approver: str,
        notes: str | None = None,
    ) -> FormulaVersion:
        """
        Approve a formula version.

        Args:
            db: Database session
            tenant_id: Tenant ID
            formula_id: Formula ID
            version: Version string
            approver: User approving
            notes: Optional notes

        Returns:
            Updated FormulaVersion

        Raises:
            FormulaNotFoundError: If formula or version not found
        """
        # Get formula version
        result = await db.execute(
            select(FormulaVersion).where(
                and_(
                    FormulaVersion.formula_id == formula_id,
                    FormulaVersion.version == version,
                    FormulaVersion.tenant_id == tenant_id,
                )
            )
        )
        version_obj = result.scalar_one_or_none()

        if version_obj is None:
            raise FormulaNotFoundError(f"Formula version {version} not found")

        # Get approval request
        if version_obj.approval_request_id:
            approval_result = await db.execute(
                select(ApprovalRequest).where(
                    ApprovalRequest.id == version_obj.approval_request_id
                )
            )
            approval_request = approval_result.scalar_one_or_none()

            if approval_request:
                # Approve via state machine
                sm = ApprovalStateMachine()
                await sm.approve(
                    db=db,
                    request=approval_request,
                    approver=approver,
                    notes=notes,
                )

        # Update version status
        version_obj.status = FormulaStatus.APPROVED.value
        version_obj.approved_by = approver
        version_obj.approved_at = datetime.now(UTC)
        version_obj.updated_at = datetime.now(UTC)

        # Update Formula.current_version
        formula = await self.get_formula(db, tenant_id, formula_id)
        formula.current_version = version
        formula.updated_at = datetime.now(UTC)

        await db.flush()

        logger.info(
            "Approved formula version %s (formula: %s, tenant: %s)",
            version,
            formula_id,
            tenant_id,
        )

        return version_obj

    async def reject_formula_version(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        formula_id: uuid.UUID,
        version: str,
        reviewer: str,
        notes: str | None = None,
    ) -> FormulaVersion:
        """
        Reject a formula version.

        Args:
            db: Database session
            tenant_id: Tenant ID
            formula_id: Formula ID
            version: Version string
            reviewer: User rejecting
            notes: Optional notes

        Returns:
            Updated FormulaVersion

        Raises:
            FormulaNotFoundError: If formula or version not found
        """
        # Get formula version
        result = await db.execute(
            select(FormulaVersion).where(
                and_(
                    FormulaVersion.formula_id == formula_id,
                    FormulaVersion.version == version,
                    FormulaVersion.tenant_id == tenant_id,
                )
            )
        )
        version_obj = result.scalar_one_or_none()

        if version_obj is None:
            raise FormulaNotFoundError(f"Formula version {version} not found")

        # Get approval request
        if version_obj.approval_request_id:
            approval_result = await db.execute(
                select(ApprovalRequest).where(
                    ApprovalRequest.id == version_obj.approval_request_id
                )
            )
            approval_request = approval_result.scalar_one_or_none()

            if approval_request:
                # Reject via state machine
                sm = ApprovalStateMachine()
                await sm.reject(
                    db=db,
                    request=approval_request,
                    reviewer=reviewer,
                    notes=notes,
                )

        # Update version status
        version_obj.status = FormulaStatus.REJECTED.value
        version_obj.updated_at = datetime.now(UTC)

        await db.flush()

        logger.info(
            "Rejected formula version %s (formula: %s, tenant: %s)",
            version,
            formula_id,
            tenant_id,
        )

        return version_obj

    async def deprecate_formula(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        formula_id: uuid.UUID,
        reason: str,
        deprecator: str = "system",
    ) -> Formula:
        """
        Deprecate a formula.

        Args:
            db: Database session
            tenant_id: Tenant ID
            formula_id: Formula ID
            reason: Reason for deprecation
            deprecator: User deprecating

        Returns:
            Updated Formula

        Raises:
            FormulaNotFoundError: If formula not found
        """
        formula = await self.get_formula(db, tenant_id, formula_id)

        if formula.deprecated_at is not None:
            raise ValueError("Formula is already deprecated")

        formula.is_active = False
        formula.deprecated_at = datetime.now(UTC)
        formula.deprecation_reason = reason
        formula.updated_at = datetime.now(UTC)

        await db.flush()

        logger.info(
            "Deprecated formula %s (reason: %s, tenant: %s)",
            formula_id,
            reason,
            tenant_id,
        )

        return formula

    async def archive_formula(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        formula_id: uuid.UUID,
        archiver: str = "system",
    ) -> Formula:
        """
        Archive a formula.

        Args:
            db: Database session
            tenant_id: Tenant ID
            formula_id: Formula ID
            archiver: User archiving

        Returns:
            Updated Formula

        Raises:
            FormulaNotFoundError: If formula not found
        """
        formula = await self.get_formula(db, tenant_id, formula_id)

        if formula.archived_at is not None:
            raise ValueError("Formula is already archived")

        formula.archived_at = datetime.now(UTC)
        formula.updated_at = datetime.now(UTC)

        await db.flush()

        logger.info(
            "Archived formula %s (tenant: %s)",
            formula_id,
            tenant_id,
        )

        return formula

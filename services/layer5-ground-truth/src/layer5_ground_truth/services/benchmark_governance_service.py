"""
Benchmark Governance Service.

Business logic for Benchmark CRUD, versioning, approval, and lifecycle management.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.benchmark_governance import (
    BenchmarkDataset,
    BenchmarkScope,
    BenchmarkStatus,
    BenchmarkType,
    BenchmarkVersion,
)

logger = logging.getLogger(__name__)


class BenchmarkNotFoundError(Exception):
    """Raised when a benchmark is not found."""
    pass


class BenchmarkSlugConflictError(Exception):
    """Raised when a benchmark slug already exists in the tenant."""
    pass


class BenchmarkVersionConflictError(Exception):
    """Raised when a benchmark version already exists."""
    pass


class BenchmarkService:
    """Service for Benchmark governance operations."""

    async def create_benchmark(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        name: str,
        slug: str,
        benchmark_type: str,
        source_name: str,
        source_type: str,
        data: dict[str, Any],
        data_schema: dict[str, Any],
        effective_from: datetime,
        version: str = "1.0.0",
        source_url: str | None = None,
        source_date: datetime | None = None,
        collection_methodology: str | None = None,
        confidence_level: str = "medium",
        sample_size: int | None = None,
        margin_of_error: dict[str, Any] | None = None,
        data_quality_notes: str | None = None,
        description: str | None = None,
        created_by: str = "system",
    ) -> BenchmarkDataset:
        """
        Create a new Benchmark with initial version.

        Args:
            db: Database session
            tenant_id: Tenant ID
            name: Benchmark name
            slug: Unique slug within tenant
            benchmark_type: Type of benchmark
            source_name: Source name
            source_type: Source type
            data: Benchmark data
            data_schema: JSON Schema for data structure
            effective_from: Effective start date
            version: Initial version string
            source_url: Optional source URL
            source_date: Optional source date
            collection_methodology: Optional collection methodology
            confidence_level: Confidence level
            sample_size: Optional sample size
            margin_of_error: Optional margin of error
            data_quality_notes: Optional data quality notes
            description: Optional description
            created_by: User creating the benchmark

        Returns:
            Created BenchmarkDataset

        Raises:
            BenchmarkSlugConflictError: If slug already exists
        """
        # Check slug uniqueness
        existing = await db.execute(
            select(BenchmarkDataset).where(
                and_(
                    BenchmarkDataset.tenant_id == tenant_id,
                    BenchmarkDataset.slug == slug,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise BenchmarkSlugConflictError(f"Benchmark slug '{slug}' already exists")

        # Create BenchmarkDataset record
        benchmark = BenchmarkDataset(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            benchmark_type=benchmark_type,
            description=description,
            current_version=None,  # No approved version yet
            latest_version=version,
            source_name=source_name,
            source_url=source_url,
            source_type=source_type,
            source_date=source_date,
            collection_methodology=collection_methodology,
            confidence_level=confidence_level,
            sample_size=sample_size,
            margin_of_error=margin_of_error,
            data_quality_notes=data_quality_notes,
            is_active=True,
            created_by=created_by,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(benchmark)
        await db.flush()

        # Create initial BenchmarkVersion (DRAFT status)
        benchmark_version = BenchmarkVersion(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            benchmark_id=benchmark.id,
            version=version,
            data=data,
            data_schema=data_schema,
            effective_from=effective_from,
            status=BenchmarkStatus.DRAFT.value,
            changed_by=created_by,
            created_at=datetime.now(UTC),
        )
        db.add(benchmark_version)
        await db.flush()

        logger.info(
            "Created benchmark %s (slug: %s, tenant: %s)",
            benchmark.id,
            slug,
            tenant_id,
        )

        return benchmark

    async def get_benchmark(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        benchmark_id: uuid.UUID,
    ) -> BenchmarkDataset:
        """
        Get a benchmark by ID with tenant scoping.

        Args:
            db: Database session
            tenant_id: Tenant ID
            benchmark_id: Benchmark ID

        Returns:
            BenchmarkDataset

        Raises:
            BenchmarkNotFoundError: If benchmark not found
        """
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
            raise BenchmarkNotFoundError(f"Benchmark {benchmark_id} not found")

        return benchmark

    async def list_benchmarks(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        benchmark_type: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[BenchmarkDataset], int]:
        """
        List benchmarks with pagination and filtering.

        Args:
            db: Database session
            tenant_id: Tenant ID
            benchmark_type: Optional filter by benchmark type
            is_active: Optional filter by active status
            page: Page number
            page_size: Page size

        Returns:
            Tuple of (benchmarks, total count)
        """
        query = select(BenchmarkDataset).where(BenchmarkDataset.tenant_id == tenant_id)

        if benchmark_type:
            query = query.where(BenchmarkDataset.benchmark_type == benchmark_type)

        if is_active is not None:
            query = query.where(BenchmarkDataset.is_active == is_active)

        # Get total count
        from sqlalchemy import func

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        query = query.order_by(BenchmarkDataset.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        benchmarks = result.scalars().all()

        return list(benchmarks), total

    async def create_benchmark_version(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        benchmark_id: uuid.UUID,
        version: str,
        data: dict[str, Any],
        data_schema: dict[str, Any],
        effective_from: datetime,
        effective_until: datetime | None = None,
        change_description: str | None = None,
        changed_by: str = "system",
    ) -> BenchmarkVersion:
        """
        Create a new version of a benchmark.

        Args:
            db: Database session
            tenant_id: Tenant ID
            benchmark_id: Benchmark ID
            version: Version string (semver)
            data: Benchmark data
            data_schema: JSON Schema for data structure
            effective_from: Effective start date
            effective_until: Optional effective end date
            change_description: Description of changes
            changed_by: User creating the version

        Returns:
            Created BenchmarkVersion

        Raises:
            BenchmarkNotFoundError: If benchmark not found
            BenchmarkVersionConflictError: If version already exists
        """
        # Get benchmark
        benchmark = await self.get_benchmark(db, tenant_id, benchmark_id)

        # Check version uniqueness
        existing = await db.execute(
            select(BenchmarkVersion).where(
                and_(
                    BenchmarkVersion.benchmark_id == benchmark_id,
                    BenchmarkVersion.version == version,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise BenchmarkVersionConflictError(f"Version {version} already exists")

        # Create new version
        new_version = BenchmarkVersion(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            benchmark_id=benchmark_id,
            version=version,
            data=data,
            data_schema=data_schema,
            effective_from=effective_from,
            effective_until=effective_until,
            status=BenchmarkStatus.DRAFT.value,
            change_description=change_description,
            changed_by=changed_by,
            created_at=datetime.now(UTC),
        )
        db.add(new_version)

        # Update Benchmark.latest_version
        benchmark.latest_version = version
        benchmark.updated_at = datetime.now(UTC)

        await db.flush()

        logger.info(
            "Created benchmark version %s for benchmark %s (tenant: %s)",
            version,
            benchmark_id,
            tenant_id,
        )

        return new_version

    async def approve_benchmark_version(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        benchmark_id: uuid.UUID,
        version: str,
        approver: str,
        notes: str | None = None,
    ) -> BenchmarkVersion:
        """
        Approve a benchmark version.

        Args:
            db: Database session
            tenant_id: Tenant ID
            benchmark_id: Benchmark ID
            version: Version string
            approver: User approving
            notes: Optional notes

        Returns:
            Updated BenchmarkVersion

        Raises:
            BenchmarkNotFoundError: If benchmark or version not found
        """
        # Get benchmark version
        result = await db.execute(
            select(BenchmarkVersion).where(
                and_(
                    BenchmarkVersion.benchmark_id == benchmark_id,
                    BenchmarkVersion.version == version,
                    BenchmarkVersion.tenant_id == tenant_id,
                )
            )
        )
        version_obj = result.scalar_one_or_none()

        if version_obj is None:
            raise BenchmarkNotFoundError(f"Benchmark version {version} not found")

        # Update version status
        version_obj.status = BenchmarkStatus.APPROVED.value
        version_obj.approved_by = approver
        version_obj.approved_at = datetime.now(UTC)
        version_obj.updated_at = datetime.now(UTC)

        # Update Benchmark.current_version
        benchmark = await self.get_benchmark(db, tenant_id, benchmark_id)
        benchmark.current_version = version
        benchmark.updated_at = datetime.now(UTC)

        await db.flush()

        logger.info(
            "Approved benchmark version %s (benchmark: %s, tenant: %s)",
            version,
            benchmark_id,
            tenant_id,
        )

        return version_obj

    async def deprecate_benchmark(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        benchmark_id: uuid.UUID,
        reason: str,
        deprecator: str = "system",
    ) -> BenchmarkDataset:
        """
        Deprecate a benchmark.

        Args:
            db: Database session
            tenant_id: Tenant ID
            benchmark_id: Benchmark ID
            reason: Reason for deprecation
            deprecator: User deprecating

        Returns:
            Updated BenchmarkDataset

        Raises:
            BenchmarkNotFoundError: If benchmark not found
        """
        benchmark = await self.get_benchmark(db, tenant_id, benchmark_id)

        if benchmark.deprecated_at is not None:
            raise ValueError("Benchmark is already deprecated")

        benchmark.is_active = False
        benchmark.deprecated_at = datetime.now(UTC)
        benchmark.deprecation_reason = reason
        benchmark.updated_at = datetime.now(UTC)

        await db.flush()

        logger.info(
            "Deprecated benchmark %s (reason: %s, tenant: %s)",
            benchmark_id,
            reason,
            tenant_id,
        )

        return benchmark

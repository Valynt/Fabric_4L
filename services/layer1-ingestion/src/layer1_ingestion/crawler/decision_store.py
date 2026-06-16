from __future__ import annotations

"""Canonical decision store for crawl routing decisions.

Provides persistent, queryable decision history separate from operational logs.
Enables replay analysis, audit lookup, and policy validation.
"""


import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..shared.database import TenantContextError, get_db_session
from ..shared.models import CrawlDecision as CrawlDecisionModel

logger = structlog.get_logger()


@dataclass
class CrawlDecisionRecord:
    """Canonical record of a crawl routing decision.

    Immutable record of what was requested, decided, attempted, and executed.
    This is the source of truth for debugging, metrics, and optimization.
    """

    # Identity (required fields first)
    decision_id: str
    job_id: str

    # Request context (required fields)
    url: str
    domain: str
    requested_path: str  # Target-level mode: fast/browser/fast_fallback

    # Routing decision
    router_decision: str  # What SmartRouter chose
    router_rule: str  # Which rule triggered the decision

    # Quality evaluation
    quality_passed: bool | None
    quality_checks: dict[str, bool] | None
    fallback_reason: str | None

    # Execution outcome
    final_path: str  # What actually executed: fast/browser/fallback/error
    status_code: int | None

    # Performance metrics
    fast_duration_ms: int
    browser_duration_ms: int | None
    fetch_time_ms: int  # Total time
    bytes_transferred: int

    # Content analysis
    spa_detected: bool
    text_length: int

    # Error tracking (optional fields with defaults)
    tenant_id: str | None = None
    error_type: str | None = None
    error_message: str | None = None

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "decision_id": self.decision_id,
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "url": self.url,
            "domain": self.domain,
            "requested_path": self.requested_path,
            "router_decision": self.router_decision,
            "router_rule": self.router_rule,
            "quality_passed": self.quality_passed,
            "quality_checks": self.quality_checks,
            "fallback_reason": self.fallback_reason,
            "final_path": self.final_path,
            "status_code": self.status_code,
            "fast_duration_ms": self.fast_duration_ms,
            "browser_duration_ms": self.browser_duration_ms,
            "fetch_time_ms": self.fetch_time_ms,
            "bytes_transferred": self.bytes_transferred,
            "spa_detected": self.spa_detected,
            "text_length": self.text_length,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class FallbackStats:
    """Statistics about fallback behavior for a domain."""

    domain: str
    total_decisions: int
    fast_count: int
    browser_count: int
    fallback_count: int
    fallback_rate: float
    top_fallback_reasons: dict[str, int]
    avg_fast_duration_ms: float
    avg_browser_duration_ms: float


@dataclass
class RouterQualityReport:
    """Quality report for a job's routing decisions."""

    job_id: str
    total_urls: int
    fast_path_count: int
    browser_path_count: int
    fallback_count: int
    fallback_rate: float
    quality_gate_accuracy: float  # % of quality assessments that matched outcome
    top_router_rules: dict[str, int]
    avg_fetch_time_ms: float
    slowest_url: str | None
    fastest_url: str | None


class CrawlDecisionRepository:
    """Repository for crawl decision persistence and querying.

    Provides CRUD operations for decision records with efficient
    querying by job, URL, domain, and time range.

    Example:
        repo = CrawlDecisionRepository()

        # Save a decision
        record = CrawlDecisionRecord(
            decision_id=str(uuid4()),
            job_id="job-123",
            url="https://example.com",
            # ... other fields
        )
        await repo.save(record)

        # Query by job
        decisions = await repo.get_by_job("job-123", tenant_id="tenant-uuid")

        # Get fallback stats
        stats = await repo.get_fallback_stats(
            "example.com", tenant_id="tenant-uuid", since=datetime.now() - timedelta(days=7)
        )
    """

    def __init__(self, db_session: Session | None = None) -> None:
        """Initialize repository.

        Args:
            db_session: Optional database session. If None, uses get_db_session().
        """
        self._session = db_session
        self.logger = logger.bind(component="CrawlDecisionRepository")

    def _get_session(self) -> Session:
        """Get database session.

        Raises:
            RuntimeError: If called without explicit tenant context.
        """
        if self._session:
            return self._session
        raise RuntimeError(
            "_get_session() must be called with explicit tenant context. "
            "Pass db_session to CrawlDecisionRepository constructor or use "
            "repository methods with tenant context already set."
        )

    def _save_sync(self, record: CrawlDecisionRecord) -> None:
        """Synchronous save implementation (runs in thread pool)."""
        if not record.tenant_id:
            raise TenantContextError("CrawlDecisionRecord.tenant_id is required for persistence")

        try:
            tenant_id = UUID(record.tenant_id)
        except (TypeError, ValueError) as exc:
            raise TenantContextError(
                f"Invalid CrawlDecisionRecord.tenant_id for persistence: {record.tenant_id!r}"
            ) from exc

        with get_db_session(tenant_id=tenant_id, require_tenant=True) as session:
            db_record = CrawlDecisionModel(
                decision_id=UUID(record.decision_id),
                job_id=UUID(record.job_id) if record.job_id else None,
                tenant_id=tenant_id,
                url=record.url,
                domain=record.domain,
                requested_path=record.requested_path,
                router_decision=record.router_decision,
                router_rule=record.router_rule,
                quality_passed=record.quality_passed,
                quality_checks=json.dumps(record.quality_checks) if record.quality_checks else None,
                fallback_reason=record.fallback_reason,
                final_path=record.final_path,
                status_code=record.status_code,
                fast_duration_ms=record.fast_duration_ms,
                browser_duration_ms=record.browser_duration_ms,
                fetch_time_ms=record.fetch_time_ms,
                bytes_transferred=record.bytes_transferred,
                spa_detected=record.spa_detected,
                text_length=record.text_length,
                error_type=record.error_type,
                error_message=record.error_message,
                created_at=record.created_at,
            )
            session.add(db_record)
            session.commit()

    async def save(self, record: CrawlDecisionRecord) -> None:
        """Save a crawl decision record.

        Args:
            record: The decision record to persist
        """
        try:
            # P2 FIX: Run sync DB operations in thread pool to prevent blocking
            await asyncio.to_thread(self._save_sync, record)
            self.logger.debug(
                "Decision record saved",
                decision_id=record.decision_id,
                job_id=record.job_id,
                final_path=record.final_path,
            )
        except Exception:
            self.logger.error(
                "Failed to save decision record",
                decision_id=record.decision_id,
                error_code="DECISION_SAVE_ERROR",
                exc_info=True,
            )
            raise

    def _get_by_id_sync(self, decision_id: str, tenant_id: str) -> CrawlDecisionRecord | None:
        """Synchronous get by ID implementation."""
        with self._get_session() as session:
            db_record = session.get(CrawlDecisionModel, UUID(decision_id))
            if not db_record or str(db_record.tenant_id) != tenant_id:
                return None
            return self._to_record(db_record)

    async def get_by_id(self, decision_id: str, tenant_id: str) -> CrawlDecisionRecord | None:
        """Get a decision record by ID.

        Args:
            decision_id: The decision UUID
            tenant_id: The tenant UUID that owns the record

        Returns:
            Decision record or None if not found
        """
        return await asyncio.to_thread(self._get_by_id_sync, decision_id, tenant_id)

    def _get_by_job_sync(
        self,
        job_id: str,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CrawlDecisionRecord]:
        """Synchronous get by job implementation."""
        with self._get_session() as session:
            stmt = (
                select(CrawlDecisionModel)
                .where(CrawlDecisionModel.job_id == UUID(job_id))
                .where(CrawlDecisionModel.tenant_id == UUID(tenant_id))
                .order_by(CrawlDecisionModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            db_records = session.execute(stmt).scalars().all()
            return [self._to_record(r) for r in db_records]

    async def get_by_job(
        self,
        job_id: str,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CrawlDecisionRecord]:
        """Get all decision records for a job.

        Args:
            job_id: The job UUID
            tenant_id: The tenant UUID that owns the records
            limit: Maximum records to return
            offset: Offset for pagination

        Returns:
            List of decision records
        """
        return await asyncio.to_thread(self._get_by_job_sync, job_id, tenant_id, limit, offset)

    def _get_by_url_sync(
        self, url: str, tenant_id: str, limit: int = 100
    ) -> list[CrawlDecisionRecord]:
        """Synchronous get by URL implementation."""
        with self._get_session() as session:
            stmt = (
                select(CrawlDecisionModel)
                .where(CrawlDecisionModel.url == url)
                .where(CrawlDecisionModel.tenant_id == UUID(tenant_id))
                .order_by(CrawlDecisionModel.created_at.desc())
                .limit(limit)
            )
            db_records = session.execute(stmt).scalars().all()
            return [self._to_record(r) for r in db_records]

    async def get_by_url(
        self,
        url: str,
        tenant_id: str,
        limit: int = 100,
    ) -> list[CrawlDecisionRecord]:
        """Get decision history for a specific URL.

        Args:
            url: The URL to query
            tenant_id: The tenant UUID that owns the records
            limit: Maximum records to return

        Returns:
            List of decision records for this URL
        """
        return await asyncio.to_thread(self._get_by_url_sync, url, tenant_id, limit)

    def _get_by_domain_sync(
        self,
        domain: str,
        tenant_id: str,
        since: datetime | None = None,
        limit: int = 1000,
    ) -> list[CrawlDecisionRecord]:
        """Synchronous get by domain implementation."""
        with self._get_session() as session:
            stmt = (
                select(CrawlDecisionModel)
                .where(CrawlDecisionModel.domain == domain)
                .where(CrawlDecisionModel.tenant_id == UUID(tenant_id))
            )
            if since:
                stmt = stmt.where(CrawlDecisionModel.created_at >= since)
            stmt = stmt.order_by(CrawlDecisionModel.created_at.desc()).limit(limit)
            db_records = session.execute(stmt).scalars().all()
            return [self._to_record(r) for r in db_records]

    async def get_by_domain(
        self,
        domain: str,
        tenant_id: str,
        since: datetime | None = None,
        limit: int = 1000,
    ) -> list[CrawlDecisionRecord]:
        """Get decision records for a domain.

        Args:
            domain: The domain to query
            tenant_id: The tenant UUID that owns the records
            since: Optional time filter
            limit: Maximum records to return

        Returns:
            List of decision records
        """
        return await asyncio.to_thread(self._get_by_domain_sync, domain, tenant_id, since, limit)

    def _get_fallback_stats_sync(
        self,
        domain: str,
        tenant_id: str,
        since: datetime | None = None,
    ) -> FallbackStats:
        """Synchronous get fallback stats implementation."""
        with self._get_session() as session:
            base_stmt = (
                select(CrawlDecisionModel)
                .where(CrawlDecisionModel.domain == domain)
                .where(CrawlDecisionModel.tenant_id == UUID(tenant_id))
            )
            if since:
                base_stmt = base_stmt.where(CrawlDecisionModel.created_at >= since)
            all_decisions = session.execute(base_stmt).scalars().all()
            if not all_decisions:
                return FallbackStats(
                    domain=domain,
                    total_decisions=0,
                    fast_count=0,
                    browser_count=0,
                    fallback_count=0,
                    fallback_rate=0.0,
                    top_fallback_reasons={},
                    avg_fast_duration_ms=0.0,
                    avg_browser_duration_ms=0.0,
                )
            total = len(all_decisions)
            fast_count = sum(1 for d in all_decisions if d.final_path == "fast")
            browser_count = sum(1 for d in all_decisions if d.final_path == "browser")
            fallback_count = sum(1 for d in all_decisions if d.final_path == "fallback")
            reasons: dict[str, int] = {}
            for d in all_decisions:
                if d.fallback_reason:
                    reasons[d.fallback_reason] = reasons.get(d.fallback_reason, 0) + 1
            fast_times = [d.fast_duration_ms for d in all_decisions if d.fast_duration_ms > 0]
            browser_times = [d.browser_duration_ms for d in all_decisions if d.browser_duration_ms]
            avg_fast = sum(fast_times) / len(fast_times) if fast_times else 0.0
            avg_browser = sum(browser_times) / len(browser_times) if browser_times else 0.0
            return FallbackStats(
                domain=domain,
                total_decisions=total,
                fast_count=fast_count,
                browser_count=browser_count,
                fallback_count=fallback_count,
                fallback_rate=fallback_count / total if total > 0 else 0.0,
                top_fallback_reasons=dict(sorted(reasons.items(), key=lambda x: x[1], reverse=True)[:5]),
                avg_fast_duration_ms=avg_fast,
                avg_browser_duration_ms=avg_browser,
            )

    async def get_fallback_stats(
        self,
        domain: str,
        tenant_id: str,
        since: datetime | None = None,
    ) -> FallbackStats:
        """Get fallback statistics for a domain.

        Args:
            domain: The domain to analyze
            tenant_id: The tenant UUID that owns the records
            since: Optional time filter

        Returns:
            Fallback statistics
        """
        return await asyncio.to_thread(self._get_fallback_stats_sync, domain, tenant_id, since)

    def _get_router_quality_report_sync(
        self, job_id: str, tenant_id: str
    ) -> RouterQualityReport:
        """Synchronous get router quality report implementation."""
        with self._get_session() as session:
            stmt = (
                select(CrawlDecisionModel)
                .where(CrawlDecisionModel.job_id == UUID(job_id))
                .where(CrawlDecisionModel.tenant_id == UUID(tenant_id))
                .order_by(CrawlDecisionModel.created_at.desc())
            )
            decisions = session.execute(stmt).scalars().all()
            if not decisions:
                return RouterQualityReport(
                    job_id=job_id,
                    total_urls=0,
                    fast_path_count=0,
                    browser_path_count=0,
                    fallback_count=0,
                    fallback_rate=0.0,
                    quality_gate_accuracy=0.0,
                    top_router_rules={},
                    avg_fetch_time_ms=0.0,
                    slowest_url=None,
                    fastest_url=None,
                )
            total = len(decisions)
            fast_count = sum(1 for d in decisions if d.final_path == "fast")
            browser_count = sum(1 for d in decisions if d.final_path == "browser")
            fallback_count = sum(1 for d in decisions if d.final_path == "fallback")
            rules: dict[str, int] = {}
            for d in decisions:
                rules[d.router_rule] = rules.get(d.router_rule, 0) + 1
            correct_quality = 0
            for d in decisions:
                if d.quality_passed is True and d.final_path == "fast":
                    correct_quality += 1
                elif d.quality_passed is False and d.final_path == "fallback":
                    correct_quality += 1
            accuracy = correct_quality / total if total > 0 else 0.0
            times = [(d.url, d.fetch_time_ms) for d in decisions if d.fetch_time_ms > 0]
            avg_time = sum(t[1] for t in times) / len(times) if times else 0.0
            sorted_times = sorted(times, key=lambda x: x[1])
            slowest = sorted_times[-1][0] if sorted_times else None
            fastest = sorted_times[0][0] if sorted_times else None
            return RouterQualityReport(
                job_id=job_id,
                total_urls=total,
                fast_path_count=fast_count,
                browser_path_count=browser_count,
                fallback_count=fallback_count,
                fallback_rate=fallback_count / total if total > 0 else 0.0,
                quality_gate_accuracy=accuracy,
                top_router_rules=dict(sorted(rules.items(), key=lambda x: x[1], reverse=True)[:5]),
                avg_fetch_time_ms=avg_time,
                slowest_url=slowest,
                fastest_url=fastest,
            )

    async def get_router_quality_report(
        self, job_id: str, tenant_id: str
    ) -> RouterQualityReport:
        """Generate a quality report for a job's routing decisions.

        Args:
            job_id: The job to analyze
            tenant_id: The tenant UUID that owns the records

        Returns:
            Router quality report
        """
        return await asyncio.to_thread(
            self._get_router_quality_report_sync, job_id, tenant_id
        )

    def _get_decisions_by_rule_sync(
        self,
        router_rule: str,
        tenant_id: str,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[CrawlDecisionRecord]:
        """Synchronous get decisions by rule implementation."""
        with self._get_session() as session:
            stmt = (
                select(CrawlDecisionModel)
                .where(CrawlDecisionModel.router_rule == router_rule)
                .where(CrawlDecisionModel.tenant_id == UUID(tenant_id))
            )
            if since:
                stmt = stmt.where(CrawlDecisionModel.created_at >= since)
            stmt = stmt.order_by(CrawlDecisionModel.created_at.desc()).limit(limit)
            db_records = session.execute(stmt).scalars().all()
            return [self._to_record(r) for r in db_records]

    async def get_decisions_by_rule(
        self,
        router_rule: str,
        tenant_id: str,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[CrawlDecisionRecord]:
        """Get decisions that triggered a specific router rule.

        Args:
            router_rule: The rule to filter by (e.g., "known_dynamic_page:PRICING")
            tenant_id: The tenant UUID that owns the records
            since: Optional time filter
            limit: Maximum records

        Returns:
            List of matching decisions
        """
        return await asyncio.to_thread(
            self._get_decisions_by_rule_sync, router_rule, tenant_id, since, limit
        )

    def _to_record(self, db_record: CrawlDecisionModel) -> CrawlDecisionRecord:
        """Convert database model to domain record."""
        return CrawlDecisionRecord(
            decision_id=str(db_record.decision_id),
            job_id=str(db_record.job_id) if db_record.job_id else "",
            tenant_id=str(db_record.tenant_id) if db_record.tenant_id else None,
            url=db_record.url,
            domain=db_record.domain,
            requested_path=db_record.requested_path,
            router_decision=db_record.router_decision,
            router_rule=db_record.router_rule,
            quality_passed=db_record.quality_passed,
            quality_checks=json.loads(db_record.quality_checks) if db_record.quality_checks else None,
            fallback_reason=db_record.fallback_reason,
            final_path=db_record.final_path,
            status_code=db_record.status_code,
            fast_duration_ms=db_record.fast_duration_ms,
            browser_duration_ms=db_record.browser_duration_ms,
            fetch_time_ms=db_record.fetch_time_ms,
            bytes_transferred=db_record.bytes_transferred,
            spa_detected=db_record.spa_detected,
            text_length=db_record.text_length,
            error_type=db_record.error_type,
            error_message=db_record.error_message,
            created_at=db_record.created_at,
        )


class InMemoryCrawlDecisionRepository(CrawlDecisionRepository):
    """In-memory repository for testing.

    Stores decisions in memory without database persistence.
    Useful for unit tests and benchmarks.
    """

    def __init__(self) -> None:
        """Initialize in-memory store."""
        super().__init__()
        self._store: dict[str, CrawlDecisionRecord] = {}
        self._job_index: dict[str, list[str]] = {}
        self._url_index: dict[str, list[str]] = {}
        self._domain_index: dict[str, list[str]] = {}

    async def save(self, record: CrawlDecisionRecord) -> None:
        """Save to in-memory store."""
        self._store[record.decision_id] = record

        # Update indexes
        if record.job_id:
            self._job_index.setdefault(record.job_id, []).append(record.decision_id)
        self._url_index.setdefault(record.url, []).append(record.decision_id)
        self._domain_index.setdefault(record.domain, []).append(record.decision_id)

    async def get_by_id(
        self, decision_id: str, tenant_id: str
    ) -> CrawlDecisionRecord | None:
        """Get from in-memory store."""
        record = self._store.get(decision_id)
        if record and record.tenant_id == tenant_id:
            return record
        return None

    async def get_by_job(
        self,
        job_id: str,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CrawlDecisionRecord]:
        """Get by job from in-memory store."""
        ids = self._job_index.get(job_id, [])
        sorted_ids = sorted(ids, reverse=True)[offset:offset + limit]
        records = [self._store[i] for i in sorted_ids if i in self._store]
        return [r for r in records if r.tenant_id == tenant_id][:limit]

    async def get_by_url(
        self, url: str, tenant_id: str, limit: int = 100
    ) -> list[CrawlDecisionRecord]:
        """Get by URL from in-memory store."""
        ids = self._url_index.get(url, [])
        sorted_ids = sorted(ids, reverse=True)[:limit]
        records = [self._store[i] for i in sorted_ids if i in self._store]
        return [r for r in records if r.tenant_id == tenant_id][:limit]

    async def get_by_domain(
        self,
        domain: str,
        tenant_id: str,
        since: datetime | None = None,
        limit: int = 1000,
    ) -> list[CrawlDecisionRecord]:
        """Get by domain from in-memory store."""
        ids = self._domain_index.get(domain, [])
        records = [self._store[i] for i in ids if i in self._store]

        if since:
            records = [r for r in records if r.created_at >= since]

        records = [r for r in records if r.tenant_id == tenant_id]
        return sorted(records, key=lambda r: r.created_at, reverse=True)[:limit]

    def clear(self) -> None:
        """Clear all stored decisions (for test cleanup)."""
        self._store.clear()
        self._job_index.clear()
        self._url_index.clear()
        self._domain_index.clear()

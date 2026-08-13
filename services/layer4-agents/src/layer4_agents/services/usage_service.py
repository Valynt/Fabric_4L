from __future__ import annotations

"""Usage metering service for event ingestion and aggregation.

Handles high-throughput usage event ingestion with idempotency,
tenant validation, and Stripe MeterEvents integration for usage-based billing.
"""
import asyncio
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..models.billing import BillingCustomer, BillingUsageEvent, UsageEventStatus


class UsageService_ingest_batchResult(TypedDictModel):
    created: Any
    duplicates: Any
    error_details: Any
    errors: Any


class UsageService_get_usage_summaryResult(TypedDictModel):
    customer_id: Any
    event_count: int
    first_event: Any
    last_event: Any
    metric_name: Any
    period_end: Any
    period_start: Any
    total_quantity: Any


class UsageService_sync_to_stripeResult(TypedDictModel):
    customer_id: Any | None = None
    details: Any | None = None
    error: str | None = None
    message: str | None = None
    metrics: Any | None = None
    stripe_customer_id: Any | None = None
    synced: int


class UsageService__report_to_stripeResult(TypedDictModel):
    error: Any


logger = logging.getLogger(__name__)

# Auto-report to Stripe on ingestion
AUTO_REPORT_TO_STRIPE = os.environ.get("STRIPE_AUTO_REPORT_USAGE", "false").lower() == "true"


class UsageValidationError(Exception):
    """Raised when usage event validation fails."""

    def __init__(self, message: str, field: str | None = None):
        self.message = message
        self.field = field
        super().__init__(message)


class UsageService:
    """Service for usage event ingestion and aggregation."""

    # Maximum events per batch to prevent memory issues
    MAX_BATCH_SIZE = 1000

    # Default lookback period for aggregation
    DEFAULT_AGGREGATION_WINDOW_DAYS = 30

    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        # See OverageService: normalize UUID-typed tenant context to str for
        # String-typed billing columns under asyncpg.
        self.tenant_id = str(tenant_id) if tenant_id is not None else None

    async def _get_stripe_customer_id(self, customer_id: str) -> str | None:
        """Get Stripe customer ID for internal customer.

        Args:
            customer_id: Internal customer ID

        Returns:
            Stripe customer ID or None if not found
        """

        if not self.tenant_id:
            return None

        query = select(BillingCustomer).where(
            BillingCustomer.tenant_id == self.tenant_id,
            BillingCustomer.id == customer_id,
        )

        result = await self.db.execute(query)
        customer = result.scalar_one_or_none()

        return customer.stripe_customer_id if customer else None

    async def _report_to_stripe(
        self,
        customer_id: str,
        metric_name: str,
        quantity: float,
        event_id: str,
    ) -> dict[str, Any] | None:
        """Report usage event to Stripe MeterEvents if enabled.

        Args:
            customer_id: Internal customer ID
            metric_name: Metric name
            quantity: Quantity consumed
            event_id: Unique event identifier

        Returns:
            Stripe response or None if disabled/failed
        """
        if not AUTO_REPORT_TO_STRIPE:
            return None

        try:
            from ..services.stripe_client import (
                StripeMeterEventError,
                StripeNotConfiguredError,
                report_meter_event,
            )

            stripe_customer_id = await self._get_stripe_customer_id(customer_id)
            if not stripe_customer_id:
                logger.debug(f"No Stripe customer ID for {customer_id}, skipping meter reporting")
                return None

            return report_meter_event(
                stripe_customer_id=stripe_customer_id,
                metric_name=metric_name,
                quantity=quantity,
                event_id=event_id,
            )

        except StripeNotConfiguredError:
            logger.debug("Stripe not configured, skipping meter reporting")
            return None
        except StripeMeterEventError as e:
            logger.warning(f"Failed to report meter event: {e}")
            return UsageService__report_to_stripeResult.model_validate(
                {"error": "STRIPE_METER_ERROR"}
            )
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            logger.error(
                "Stripe reporting infrastructure failure",
                extra={
                    "customer_id": customer_id,
                    "metric_name": metric_name,
                    "event_id": event_id,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            return None

    async def ingest_event(
        self,
        event_id: str,
        customer_id: str,
        event_name: str,
        metric_name: str,
        quantity: float = 1.0,
        unit: str | None = None,
        timestamp: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BillingUsageEvent:
        """Ingest a single usage event with idempotency.

        Args:
            event_id: Unique event identifier (idempotency key)
            customer_id: Internal customer/user ID
            event_name: Event type (e.g., 'api_call', 'data_processed')
            metric_name: Metric to bill against (e.g., 'tokens', 'bytes')
            quantity: Numeric quantity consumed
            unit: Unit of measurement (optional)
            timestamp: Event timestamp (defaults to now)
            metadata: Additional event attributes

        Returns:
            Created or existing usage event

        Raises:
            UsageValidationError: If validation fails
            IntegrityError: If tenant_id is not set
        """
        # Validate tenant context
        if not self.tenant_id:
            raise UsageValidationError(
                "tenant_id is required for usage event ingestion", field="tenant_id"
            )

        # Validate required fields
        if not event_id or len(event_id) > 255:
            raise UsageValidationError(
                "event_id is required and must be <= 255 chars", field="event_id"
            )
        if not customer_id or len(customer_id) > 100:
            raise UsageValidationError(
                "customer_id is required and must be <= 100 chars", field="customer_id"
            )
        if not event_name or len(event_name) > 100:
            raise UsageValidationError(
                "event_name is required and must be <= 100 chars", field="event_name"
            )
        if not metric_name or len(metric_name) > 100:
            raise UsageValidationError(
                "metric_name is required and must be <= 100 chars", field="metric_name"
            )
        if quantity < 0:
            raise UsageValidationError("quantity must be non-negative", field="quantity")

        # Use provided timestamp or now
        event_timestamp = timestamp or datetime.now(UTC)

        # Create the event
        event = BillingUsageEvent(
            id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            customer_id=customer_id,
            event_id=event_id,
            event_name=event_name,
            metric_name=metric_name,
            quantity=quantity,
            unit=unit,
            timestamp=event_timestamp,
            status=UsageEventStatus.PENDING,
            event_metadata=metadata or {},
            created_at=datetime.now(UTC),
        )

        stripe_response = None
        try:
            self.db.add(event)
            await self.db.flush()
            logger.debug(
                f"Usage event ingested: {event_id} for customer {customer_id}, "
                f"metric {metric_name}, quantity {quantity}"
            )

            # Optionally report to Stripe for real-time metering
            stripe_response = await self._report_to_stripe(
                customer_id=customer_id,
                metric_name=metric_name,
                quantity=quantity,
                event_id=event_id,
            )

            # Attach stripe response to event for return
            event._stripe_response = stripe_response
            return event

        except IntegrityError:
            # Duplicate event - fetch and return existing
            await self.db.rollback()
            existing = await self._get_event_by_idempotency(event_id)
            if existing:
                logger.debug(f"Duplicate usage event detected: {event_id}, returning existing")
                # Mark as duplicate
                existing._stripe_response = {"skipped": True, "reason": "duplicate"}
                return existing
            raise
        except SQLAlchemyError as exc:
            # Rollback database errors to prevent partial writes
            await self.db.rollback()
            logger.error(
                "Usage ingest database failure",
                extra={
                    "tenant_id": self.tenant_id,
                    "event_id": event_id,
                    "error_type": type(exc).__name__,
                },
                exc_info=True,
            )
            raise

    async def _get_existing_event_ids(
        self,
        event_ids: list[str],
    ) -> set[str]:
        """Return the set of idempotency keys that already exist for this tenant."""
        if not event_ids or not self.tenant_id:
            return set()

        query = select(BillingUsageEvent.event_id).where(
            BillingUsageEvent.tenant_id == self.tenant_id,
            BillingUsageEvent.event_id.in_(event_ids),
        )
        result = await self.db.execute(query)
        return {row[0] for row in result.all() if row[0]}

    async def ingest_batch(
        self,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Ingest multiple usage events in a batch.

        Uses bulk database inserts and a single idempotency lookup to avoid
        the N+1 flush pattern of inserting events one at a time.

        Args:
            events: List of event dictionaries with keys:
                - event_id (required)
                - customer_id (required)
                - event_name (required)
                - metric_name (required)
                - quantity (optional, default 1.0)
                - unit (optional)
                - timestamp (optional)
                - metadata (optional)

        Returns:
            Summary dict with counts: {created: int, duplicates: int, errors: int}

        Raises:
            UsageValidationError: If batch exceeds MAX_BATCH_SIZE
        """
        if len(events) > self.MAX_BATCH_SIZE:
            raise UsageValidationError(
                f"Batch size {len(events)} exceeds maximum {self.MAX_BATCH_SIZE}", field="events"
            )

        if not self.tenant_id:
            raise UsageValidationError(
                "tenant_id is required for batch ingestion", field="tenant_id"
            )

        errors = 0
        error_details: list[dict] = []
        valid_events: list[dict[str, Any]] = []

        # Phase 1: validate every event locally
        for idx, event_data in enumerate(events):
            event_id = event_data.get("event_id")
            customer_id = event_data.get("customer_id")
            event_name = event_data.get("event_name")
            metric_name = event_data.get("metric_name")
            quantity = event_data.get("quantity", 1.0)

            try:
                if not event_id or len(event_id) > 255:
                    raise UsageValidationError(
                        "event_id is required and must be <= 255 chars", field="event_id"
                    )
                if not customer_id or len(customer_id) > 100:
                    raise UsageValidationError(
                        "customer_id is required and must be <= 100 chars", field="customer_id"
                    )
                if not event_name or len(event_name) > 100:
                    raise UsageValidationError(
                        "event_name is required and must be <= 100 chars", field="event_name"
                    )
                if not metric_name or len(metric_name) > 100:
                    raise UsageValidationError(
                        "metric_name is required and must be <= 100 chars", field="metric_name"
                    )
                if quantity < 0:
                    raise UsageValidationError("quantity must be non-negative", field="quantity")

                valid_events.append(event_data)
            except UsageValidationError as e:
                errors += 1
                error_details.append(
                    {
                        "index": idx,
                        "event_id": event_id or "unknown",
                        "error": e.message,
                        "field": e.field,
                    }
                )
                logger.warning(f"Validation error for event at index {idx}: {e.message}")

        if not valid_events:
            return UsageService_ingest_batchResult.model_validate(
                {
                    "created": 0,
                    "duplicates": 0,
                    "errors": errors,
                    "error_details": error_details,
                }
            )

        # Phase 2: single idempotency lookup for the whole batch
        candidate_ids = [e["event_id"] for e in valid_events]
        existing_ids = await self._get_existing_event_ids(candidate_ids)

        # Phase 3: bulk insert new events
        new_events: list[BillingUsageEvent] = []
        duplicates = 0
        now = datetime.now(UTC)
        for event_data in valid_events:
            event_id = event_data["event_id"]
            if event_id in existing_ids:
                duplicates += 1
                continue

            event_ts = event_data.get("timestamp") or now
            new_events.append(
                BillingUsageEvent(
                    id=str(uuid.uuid4()),
                    tenant_id=self.tenant_id,
                    customer_id=event_data["customer_id"],
                    event_id=event_id,
                    event_name=event_data["event_name"],
                    metric_name=event_data["metric_name"],
                    quantity=float(event_data.get("quantity", 1.0)),
                    unit=event_data.get("unit"),
                    timestamp=event_ts,
                    status=UsageEventStatus.PENDING,
                    event_metadata=event_data.get("metadata") or {},
                    created_at=now,
                )
            )

        created = 0
        if new_events:
            self.db.add_all(new_events)
            try:
                await self.db.flush()
                created = len(new_events)

                # Optional real-time Stripe reporting per event
                if AUTO_REPORT_TO_STRIPE:
                    await asyncio.gather(
                        *[
                            self._report_to_stripe(
                                customer_id=event.customer_id,
                                metric_name=event.metric_name,
                                quantity=event.quantity,
                                event_id=event.event_id,
                            )
                            for event in new_events
                        ],
                        return_exceptions=True,
                    )
            except IntegrityError:
                # A concurrent batch may have inserted some of the same
                # (tenant_id, event_id) pairs. Roll back and fall back to the
                # single-event path, which already handles duplicates gracefully.
                await self.db.rollback()
                logger.warning(
                    "Batch usage ingest hit duplicate key; falling back to per-event idempotency",
                    extra={"tenant_id": self.tenant_id, "batch_size": len(new_events)},
                )
                for event_data in valid_events:
                    event_id = event_data["event_id"]
                    if event_id in existing_ids:
                        continue
                    try:
                        await self.ingest_event(
                            event_id=event_id,
                            customer_id=event_data["customer_id"],
                            event_name=event_data["event_name"],
                            metric_name=event_data["metric_name"],
                            quantity=float(event_data.get("quantity", 1.0)),
                            unit=event_data.get("unit"),
                            timestamp=event_data.get("timestamp"),
                            metadata=event_data.get("metadata"),
                        )
                        created += 1
                    except IntegrityError:
                        duplicates += 1
                        logger.debug(
                            "Duplicate usage event detected in batch fallback",
                            extra={"tenant_id": self.tenant_id, "event_id": event_id},
                        )

        return UsageService_ingest_batchResult.model_validate(
            {
                "created": created,
                "duplicates": duplicates,
                "errors": errors,
                "error_details": error_details if errors > 0 else None,
            }
        )

    async def get_usage_summary(
        self,
        customer_id: str,
        metric_name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Get aggregated usage for a customer and metric.

        Args:
            customer_id: Customer to summarize
            metric_name: Metric to aggregate
            start_date: Start of period (defaults to 30 days ago)
            end_date: End of period (defaults to now)

        Returns:
            Summary dict with total quantity, event count, etc.
        """
        if not self.tenant_id:
            raise UsageValidationError("tenant_id is required", field="tenant_id")

        # Default date range
        end = end_date or datetime.now(UTC)
        start = start_date or (end - timedelta(days=self.DEFAULT_AGGREGATION_WINDOW_DAYS))

        # Build query
        query = select(
            func.sum(BillingUsageEvent.quantity).label("total_quantity"),
            func.count(BillingUsageEvent.id).label("event_count"),
            func.min(BillingUsageEvent.timestamp).label("first_event"),
            func.max(BillingUsageEvent.timestamp).label("last_event"),
        ).where(
            BillingUsageEvent.tenant_id == self.tenant_id,
            BillingUsageEvent.customer_id == customer_id,
            BillingUsageEvent.metric_name == metric_name,
            BillingUsageEvent.timestamp >= start,
            BillingUsageEvent.timestamp <= end,
            BillingUsageEvent.status != UsageEventStatus.IGNORED,
        )

        result = await self.db.execute(query)
        row = result.one()

        return UsageService_get_usage_summaryResult.model_validate(
            {
                "customer_id": customer_id,
                "metric_name": metric_name,
                "period_start": start.isoformat(),
                "period_end": end.isoformat(),
                "total_quantity": float(row.total_quantity or 0),
                "event_count": row.event_count or 0,
                "first_event": row.first_event.isoformat() if row.first_event else None,
                "last_event": row.last_event.isoformat() if row.last_event else None,
            }
        )

    async def list_customer_usage(
        self,
        customer_id: str,
        metric_name: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[BillingUsageEvent]:
        """List individual usage events for a customer.

        Args:
            customer_id: Customer to query
            metric_name: Optional metric filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum results (default 100, max 1000)
            offset: Pagination offset

        Returns:
            List of usage events
        """
        if not self.tenant_id:
            raise UsageValidationError("tenant_id is required", field="tenant_id")

        # Cap limit for safety
        safe_limit = min(limit, 1000)

        query = select(BillingUsageEvent).where(
            BillingUsageEvent.tenant_id == self.tenant_id,
            BillingUsageEvent.customer_id == customer_id,
        )

        if metric_name:
            query = query.where(BillingUsageEvent.metric_name == metric_name)
        if start_date:
            query = query.where(BillingUsageEvent.timestamp >= start_date)
        if end_date:
            query = query.where(BillingUsageEvent.timestamp <= end_date)

        query = query.order_by(BillingUsageEvent.timestamp.desc())
        query = query.limit(safe_limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_events_processed(
        self,
        event_ids: list[str],
    ) -> int:
        """Mark events as processed (for billing calculation).

        Args:
            event_ids: List of event IDs to mark processed

        Returns:
            Number of events updated
        """
        if not event_ids:
            return 0

        if not self.tenant_id:
            raise UsageValidationError("tenant_id is required", field="tenant_id")

        try:
            query = select(BillingUsageEvent).where(
                BillingUsageEvent.tenant_id == self.tenant_id,
                BillingUsageEvent.id.in_(event_ids),
                BillingUsageEvent.status == UsageEventStatus.PENDING,
            )

            result = await self.db.execute(query)
            events = result.scalars().all()

            now = datetime.now(UTC)
            updated = 0
            for event in events:
                event.status = UsageEventStatus.PROCESSED
                event.processed_at = now
                updated += 1

            if updated > 0:
                await self.db.flush()

            return updated
        except asyncio.CancelledError:
            raise
        except Exception:
            # Rollback on any database error to prevent partial state
            await self.db.rollback()
            raise

    async def _get_event_by_idempotency(
        self,
        event_id: str,
    ) -> BillingUsageEvent | None:
        """Get an event by its idempotency key.

        Args:
            event_id: The event idempotency key

        Returns:
            Existing event or None
        """
        if not self.tenant_id:
            return None

        query = select(BillingUsageEvent).where(
            BillingUsageEvent.tenant_id == self.tenant_id,
            BillingUsageEvent.event_id == event_id,
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def sync_to_stripe(
        self,
        customer_id: str,
        metric_name: str | None = None,
    ) -> dict[str, Any]:
        """Sync pending usage events to Stripe MeterEvents.

        Aggregates pending events and reports to Stripe for metered billing.
        Marks events as PROCESSED after successful reporting.

        Args:
            customer_id: Customer to sync usage for
            metric_name: Optional metric filter (syncs all if None)

        Returns:
            Sync summary with counts and Stripe response
        """
        from ..services.stripe_client import (
            StripeMeterEventError,
            StripeNotConfiguredError,
            report_meter_event,
        )

        if not self.tenant_id:
            raise UsageValidationError("tenant_id is required", field="tenant_id")

        try:
            # Get Stripe customer ID
            stripe_customer_id = await self._get_stripe_customer_id(customer_id)
            if not stripe_customer_id:
                return UsageService_sync_to_stripeResult.model_validate(
                    {
                        "synced": 0,
                        "error": f"No Stripe customer ID found for {customer_id}",
                    }
                )

            # Build query for pending events
            query = (
                select(
                    BillingUsageEvent.metric_name,
                    func.sum(BillingUsageEvent.quantity).label("total_quantity"),
                    func.count(BillingUsageEvent.id).label("event_count"),
                )
                .where(
                    BillingUsageEvent.tenant_id == self.tenant_id,
                    BillingUsageEvent.customer_id == customer_id,
                    BillingUsageEvent.status == UsageEventStatus.PENDING,
                )
                .group_by(BillingUsageEvent.metric_name)
            )

            if metric_name:
                query = query.where(BillingUsageEvent.metric_name == metric_name)

            result = await self.db.execute(query)
            metrics_to_sync = result.all()

            if not metrics_to_sync:
                return UsageService_sync_to_stripeResult.model_validate(
                    {"synced": 0, "message": "No pending events to sync"}
                )

            sync_results = []
            total_synced = 0

            for row in metrics_to_sync:
                metric = row.metric_name
                quantity = float(row.total_quantity)
                count = row.event_count

                try:
                    # Report to Stripe
                    stripe_response = report_meter_event(
                        stripe_customer_id=stripe_customer_id,
                        metric_name=metric,
                        quantity=quantity,
                    )

                    # Mark events as processed
                    update_query = select(BillingUsageEvent).where(
                        BillingUsageEvent.tenant_id == self.tenant_id,
                        BillingUsageEvent.customer_id == customer_id,
                        BillingUsageEvent.metric_name == metric,
                        BillingUsageEvent.status == UsageEventStatus.PENDING,
                    )

                    events_result = await self.db.execute(update_query)
                    events = events_result.scalars().all()

                    processed_at = datetime.now(UTC)
                    for event in events:
                        event.status = UsageEventStatus.PROCESSED
                        event.processed_at = processed_at

                    await self.db.flush()

                    sync_results.append(
                        {
                            "metric": metric,
                            "quantity": quantity,
                            "events": count,
                            "stripe_status": stripe_response.get("status", "unknown"),
                        }
                    )
                    total_synced += count

                except StripeMeterEventError:
                    sync_results.append(
                        {
                            "metric": metric,
                            "quantity": quantity,
                            "events": count,
                            "error": "STRIPE_METER_ERROR",
                        }
                    )
                except StripeNotConfiguredError:
                    return UsageService_sync_to_stripeResult.model_validate(
                        {
                            "synced": 0,
                            "error": "Stripe not configured",
                            "details": "STRIPE_NOT_CONFIGURED",
                        }
                    )

            return UsageService_sync_to_stripeResult.model_validate(
                {
                    "synced": total_synced,
                    "customer_id": customer_id,
                    "stripe_customer_id": stripe_customer_id,
                    "metrics": sync_results,
                }
            )

        except asyncio.CancelledError:
            raise
        except Exception:
            # Rollback on any database error to prevent partial state
            await self.db.rollback()
            raise

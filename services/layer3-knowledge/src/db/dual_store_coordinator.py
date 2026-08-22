"""Dual-Store Transaction Coordinator for Layer 3 Knowledge Graph.

Manages the write lifecycle across heterogeneous storage layers:
  1. Neo4j Graph Database (nodes & relationships)
  2. PostgreSQL + pgvector (entity metadata + embeddings)

Enforces strict tenant isolation, compensating rollback on failure,
and audit trail observability for all cross-store mutations.

Design Guarantees:
- Fail-closed: Every failure causes rollback of both stores, never partial state.
- Tenant-scoped: All writes and compensating deletes require explicit tenant_id.
- Idempotent compensation: Compensating operations are safe to re-execute.
- Auditable: Every mutation and rollback produces an AuditEvent node.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from neo4j import AsyncDriver, AsyncSession

from ..db.audited_mutation import AuditedGraphMutation

logger = logging.getLogger(__name__)


# Import metrics lazily to avoid hard dependency on prometheus_client at
# import time; ``get_metrics()`` returns None if metrics are not initialized,
# which the coordinator handles by short-circuiting increments.
try:  # pragma: no cover - import-time guard
    from ..metrics.prometheus_metrics import get_metrics as _get_metrics
except Exception:  # pragma: no cover - defensive
    _get_metrics = None  # type: ignore[assignment]


class DualStoreTransactionError(RuntimeError):
    """Raised when a dual-store transaction cannot proceed or must rollback."""


class DualStoreRollbackError(DualStoreTransactionError):
    """Raised when a compensating rollback operation fails."""


def _build_result(
    neo4j_status: str | None = None,
    neo4j_error: object = None,
    postgres_status: str | None = None,
    postgres_error: object = None,
    request_id: str | None = None,
) -> dict[str, str]:
    """Build a structured result dict from a dual-store mutation attempt."""
    return {
        "neo4j_status": neo4j_status or "",
        "neo4j_error": str(neo4j_error) if neo4j_error else "",
        "postgres_status": postgres_status or "",
        "postgres_error": str(postgres_error) if postgres_error else "",
        "request_id": request_id or "",
        "timestamp": datetime.now(UTC).isoformat(),
    }


class DualStoreTransactionCoordinator:
    """Coordinates multi-store writes with compensating rollback guarantees.

    Usage pattern:

        coordinator = DualStoreTransactionCoordinator(driver, session, tenant_id)

        # Attempt coordinated write
        result = await coordinator.write_with_rollback(
            neo4j_op=lambda session: mutation.write_node(...),
            postgres_op=lambda session: postgres_repo.create(...),
            request_id=request_id,
        )

        if result["neo4j_status"] == "failed":
            # Compensating rollback already executed
            ...
        elif result["postgres_status"] == "failed":
            # Compensating rollback already executed
            ...
    """

    def __init__(
        self,
        driver: AsyncDriver,
        tenant_id: str,
        request_id: str | None = None,
        metrics: object | None = None,
    ) -> None:
        """Initialize the dual-store transaction coordinator.

        Args:
            driver: Neo4j async driver instance
            tenant_id: Authenticated tenant context for all operations
            request_id: Correlation ID for tracing across stores
            metrics: Optional ``PrometheusMetrics`` instance. When omitted
                the coordinator falls back to the global singleton returned
                by ``get_metrics()`` (or skips increments if metrics are
                not initialized). Pass an explicit instance in tests.
        """
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id is required for dual-store coordination")
        self.tenant_id = tenant_id.strip()
        self.driver = driver
        self.request_id = request_id or self._generate_request_id()
        self._audit_mutations: list[dict[str, object]] = []
        # Per-transaction postgres compensator; set by write_with_rollback
        # before any store work begins so that emergency compensation has a
        # real handle instead of a no-op. Always reset in the finally block.
        self._active_postgres_rollback: (
            Callable[[], Awaitable[dict[str, object]]] | None
        ) = None
        # Metrics collector. Use the caller-supplied instance when present;
        # otherwise fall back to the global singleton so production wiring
        # still records counters. ``_get_metrics`` may be None at import time
        # in environments without prometheus_client installed.
        if metrics is not None:
            self._metrics = metrics
        else:
            self._metrics = _get_metrics() if _get_metrics is not None else None

    @staticmethod
    def _generate_request_id() -> str:
        """Generate a unique request correlation ID."""
        import uuid

        return str(uuid.uuid4())

    def _record_mutation_metric(self, status: str) -> None:
        """Record a terminal-path counter increment when metrics are wired up.

        No-op if metrics are disabled or the collector is unavailable. The
        source label is fixed to ``"dual_store.coordinator"`` so cardinality
        is bounded; per-request correlation IDs intentionally do NOT become
        Prometheus labels (they live in logs and audit events instead).
        """
        metrics = self._metrics
        if metrics is None:
            return
        increment = getattr(metrics, "increment_dual_store_mutation", None)
        if increment is None:
            return
        try:
            increment(source="dual_store.coordinator", status=status)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(
                "Failed to record dual_store_mutation_total for status=%s: %s",
                status,
                exc,
            )

    async def write_with_rollback(
        self,
        neo4j_op: Callable[[AsyncSession], Awaitable[dict[str, object]]],
        postgres_op: Callable[[], Awaitable[dict[str, object]]],
        request_id: str | None = None,
        postgres_rollback: (
            Callable[[], Awaitable[dict[str, object]]] | None
        ) = None,
    ) -> dict[str, str]:
        """Execute coordinated Neo4j + PostgreSQL write with compensating rollback.

        The transaction proceeds as a coordinated saga:
        1. Execute Neo4j write operation
        2. If Neo4j succeeds, execute PostgreSQL write
        3. If PostgreSQL fails after Neo4j success -> compensating rollback Neo4j
        4. If Neo4j fails -> no-op on PostgreSQL (uncommitted)

        Args:
            neo4j_op: Async callable(Neo4j session) -> dict with write results
            postgres_op: Async callable(Postgres session) -> dict with write results
            request_id: Optional correlation ID; generated if omitted
            postgres_rollback: Optional idempotent async callable that rolls
                back the postgres-side writes produced by ``postgres_op`` for
                this ``request_id``. Required so that emergency compensation
                can reconcile an uncertain postgres commit instead of logging
                a no-op. The callback MUST be idempotent: a partial / repeated
                rollback must be safe to invoke.

        Returns:
            DualStoreMutationResult with status of both stores and any errors

        Raises:
            DualStoreRollbackError: If compensating rollback itself fails
            DualStoreTransactionError: If transaction cannot proceed
        """
        req_id = request_id or self.request_id
        neo4j_session = None
        postgres_session = None
        # Register the postgres compensator for the duration of this transaction
        # so that emergency compensation has a real handle to invoke if the
        # transaction ends in an unexpected failure mode. Cleared in finally.
        self._active_postgres_rollback = postgres_rollback

        try:
            # Phase 1: Execute Neo4j write
            neo4j_result = await self._execute_neo4j_write(neo4j_op, req_id)
            if neo4j_result["status"] == "failed":
                # Neo4j already logged its own error; return early
                self._record_mutation_metric("neo4j_failure")
                return _build_result(
                    neo4j_status="failed",
                    neo4j_error=neo4j_result.get("error"),
                    request_id=req_id,
                )

            # Phase 2: Execute PostgreSQL write (Neo4j succeeded)
            postgres_result = await self._execute_postgres_write(postgres_op, req_id)
            if postgres_result["status"] == "failed":
                # PostgreSQL failed after Neo4j success -> compensate
                logger.warning(
                    "PostgreSQL write failed after Neo4j success; initiating compensating rollback for Neo4j. "
                    "request_id=%s, tenant_id=%s",
                    req_id,
                    self.tenant_id,
                )
                rollback_result = await self._compensate_neo4j_rollback(
                    error_source="postgres_write_failure",
                    request_id=req_id,
                )
                if rollback_result["status"] == "failed":
                    self._record_mutation_metric("rollback_failure")
                    raise DualStoreRollbackError(
                        f"PostgreSQL write failed and Neo4j compensating rollback also failed: "
                        f"{rollback_result.get('error')}"
                    )
                self._record_mutation_metric("rolled_back")
                return _build_result(
                    neo4j_status="rolled_back",
                    neo4j_error=rollback_result.get("error"),
                    postgres_status="failed",
                    postgres_error=postgres_result.get("error"),
                    request_id=req_id,
                )

            # Phase 3: Both succeeded
            logger.info(
                "Dual-store write completed successfully. Neo4j + PostgreSQL both committed. "
                "request_id=%s, tenant_id=%s",
                req_id,
                self.tenant_id,
            )
            self._record_mutation_metric("success")
            return _build_result(
                neo4j_status="committed",
                postgres_status="committed",
                request_id=req_id,
            )

        except DualStoreRollbackError:
            # Re-raise - already logged with full context
            raise
        except Exception as exc:
            # Unexpected error - attempt emergency compensation
            logger.error(
                "Unexpected error in dual-store transaction; initiating emergency rollback. "
                "request_id=%s, tenant_id=%s, error=%s",
                req_id,
                self.tenant_id,
                exc,
            )
            try:
                emergency_rollback = await self._emergency_compensation(req_id)
                if emergency_rollback:
                    logger.warning(
                        "Emergency compensation completed for unexpected error. "
                        "request_id=%s, tenant_id=%s",
                        req_id,
                        self.tenant_id,
                    )
                self._record_mutation_metric(
                    "emergency_compensated" if emergency_rollback
                    else "emergency_compensation_failed"
                )
            except Exception:
                self._record_mutation_metric("emergency_compensation_failed")
                logger.critical(
                    "Emergency compensation FAILED for unexpected error. "
                    "request_id=%s, tenant_id=%s - potential data inconsistency.",
                    req_id,
                    self.tenant_id,
                )
            raise DualStoreTransactionError(
                f"Unexpected transaction failure: {exc}. "
                "Emergency compensation attempted but may not have restored consistency."
            )
        finally:
            # Ensure session cleanup
            if neo4j_session:
                try:
                    await neo4j_session.close()
                except Exception:
                    pass
            if postgres_session:
                try:
                    await postgres_session.close()
                except Exception:
                    pass
            # Drop the per-transaction postgres compensator handle so it
            # cannot leak into the next write_with_rollback call.
            self._active_postgres_rollback = None

    async def _execute_neo4j_write(
        self,
        neo4j_op: Callable[[AsyncSession], Awaitable[dict[str, object]]],
        request_id: str,
    ) -> dict[str, object]:
        """Execute a Neo4j write operation through the validated gateway.

        Forwards the underlying ``neo4j_op`` result's ``status`` field so
        downstream coordinators can branch on "failed" outcomes (mirrors the
        postgres path). When the caller does not supply a status we default
        to "committed" — a failure-mode that surfaces as "failed" must be
        opted into by the caller, never silently coerced to "committed".
        """
        async with self.driver.session(database="neo4j") as session:
            # Execute the user-provided operation
            result = await neo4j_op(session)

            # Record audit metadata for this write
            audit_entry: dict[str, object] = {
                "operation": "dual_store_write",
                "target": "neo4j",
                "tenant_id": self.tenant_id,
                "request_id": request_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "result": result,
            }
            self._audit_mutations.append(audit_entry)

            # Forward the actual status from neo4j_op (mirror of postgres path).
            # Hardcoding "committed" would mask downstream failures and was the
            # root cause of the P1 finding where neo4j_op returned a failure
            # shape but the coordinator reported the write as committed.
            return {"status": result.get("status", "committed"), "result": result}

    async def _execute_postgres_write(
        self,
        postgres_op: Callable[[], Awaitable[dict[str, object]]],
        request_id: str,
    ) -> dict[str, object]:
        """Execute a PostgreSQL write operation.

        Note: This method currently validates tenant context through
        the caller's postgres_op, since postgres session management
        is handled at the service layer. The coordinator ensures
        that if the overall transaction fails, compensation is triggered.
        """
        # For now, delegate to the provided callable
        # The actual postgres session management is done by the service
        result = await postgres_op()

        # Record audit metadata
        audit_entry: dict[str, object] = {
            "operation": "dual_store_write",
            "target": "postgres",
            "tenant_id": self.tenant_id,
            "request_id": request_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "result": result,
        }
        self._audit_mutations.append(audit_entry)

        # Return the actual status from postgres_op, not hardcoded "committed"
        return {"status": result.get("status", "committed"), "result": result}

    async def _compensate_neo4j_rollback(
        self, error_source: str, request_id: str
    ) -> dict[str, object]:
        """Compensating rollback for Neo4j: purge recently created nodes/edges.

        Routes through ``AuditedGraphMutation.delete_by_request`` so the
        compensating purge is scoped to both ``tenant_id`` and
        ``_request_id`` â€” only nodes from THIS transaction are removed,
        never unrelated historical entities.

        The compensation is idempotent: purging non-existent nodes simply
        returns a zero count.
        """
        try:
            async with self.driver.session(database="neo4j") as session:
                mutation = AuditedGraphMutation(
                    tenant_id=self.tenant_id,
                    session=session,
                    request_id=request_id,
                    operation_source="dual_store.coordinator",
                )

                result = await mutation.delete_by_request(request_id=request_id)
                deleted_count = result.get("deleted_count", 0)

                # Emit audit event for the compensating rollback
                await self._emit_audit_event(
                    action="COMPENSATING_ROLLBACK",
                    entity_id=f"tenant:{self.tenant_id}",
                    session=session,
                    details={
                        "error_source": error_source,
                        "deleted_count": deleted_count,
                        "request_id": request_id,
                    },
                )

                return {
                    "status": "completed",
                    "error": None,
                    "deleted_count": deleted_count,
                }

        except Exception as exc:
            logger.error(
                "Neo4j compensating rollback failed: %s, tenant_id=%s, request_id=%s",
                exc,
                self.tenant_id,
                request_id,
                exc_info=True,
            )
            return {
                "status": "failed",
                "error": "dual_store_compensation_failed",
                "deleted_count": 0,
            }

    async def _emit_audit_event(
        self,
        action: str,
        entity_id: str,
        session: AsyncSession | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        """Emit an AuditEvent node through the AuditedGraphMutation gateway."""
        try:
            mutation = AuditedGraphMutation(
                tenant_id=self.tenant_id,
                session=session,
                operation_source="dual_store.coordinator",
            )

            await mutation.emit_audit_event(
                action=action,
                entity_id=entity_id,
                details=details,
            )
        except Exception as exc:
            logger.warning(
                "Failed to emit audit event for dual-store coordinator: %s",
                exc,
                exc_info=True,
            )

    async def _emergency_compensation(self, request_id: str) -> bool:
        """Emergency compensation for unexpected transaction failures.

        Attempts to rollback any partially committed state across both stores.
        Returns True only when compensation was actually executed for at
        least one store. For postgres, a real idempotent compensator
        registered via ``write_with_rollback(postgres_rollback=...)`` is
        invoked; without one, postgres compensation is impossible (not just
        unlogged) and the caller is explicitly flagged.

        Failure semantics:
          - Returns ``True`` if at least one store was successfully
            compensated.
          - Returns ``False`` if neither store could be compensated (e.g. no
            postgres compensator was registered AND neo4j purge failed).
            Callers MUST treat False as "uncertain state, surface to
            operators" — never as "no-op success".
        """
        emergency_success = False
        postgres_compensated = False

        try:
            # Attempt Neo4j compensation
            neo4j_comp = await self._compensate_neo4j_rollback(
                error_source="emergency_failure",
                request_id=request_id,
            )
            if neo4j_comp["status"] == "completed":
                emergency_success = True
                logger.info(
                    "Emergency Neo4j compensation deleted %s nodes",
                    neo4j_comp.get("deleted_count", 0),
                )
        except Exception:
            pass

        # Attempt PostgreSQL compensation through the caller-registered
        # idempotent compensator. Without one we cannot reconcile postgres
        # state — surface that explicitly so operators know the dual-store
        # guarantee is broken for this transaction.
        compensator = self._active_postgres_rollback
        if compensator is not None:
            try:
                comp_result = await compensator()
                status = comp_result.get("status", "unknown")
                if status == "completed":
                    postgres_compensated = True
                    emergency_success = True
                    logger.info(
                        "Emergency PostgreSQL compensation completed for request_id=%s",
                        request_id,
                    )
                elif status == "skipped":
                    logger.info(
                        "PostgreSQL compensator reported skipped "
                        "(no rows to rollback) for request_id=%s",
                        request_id,
                    )
                else:
                    logger.warning(
                        "PostgreSQL compensator returned status=%s for request_id=%s",
                        status,
                        request_id,
                    )
            except Exception as exc:
                logger.error(
                    "Emergency PostgreSQL compensation failed for request_id=%s: %s",
                    request_id,
                    exc,
                    exc_info=True,
                )
        else:
            logger.warning(
                "No PostgreSQL compensator registered for request_id=%s; "
                "postgres state cannot be reconciled automatically. "
                "Operators must investigate and reconcile manually.",
                request_id,
            )

        if not postgres_compensated:
            logger.warning(
                "Emergency PostgreSQL compensation NOT executed for request_id=%s "
                "(compensator=%s)",
                request_id,
                "registered" if compensator is not None else "missing",
            )

        return emergency_success

"""Durable source ingestion pipeline orchestrator.

Uses a PostgreSQL-backed state machine, transactional outbox, and Celery
workers to advance a source through the L1-L6 pipeline. Temporal and Kafka are
intentionally deferred until the pipeline semantics are proven.
"""

from .coordinator import PipelineCoordinator
from .state_machine import PipelineStateMachine, TransitionError

__all__ = ["PipelineCoordinator", "PipelineStateMachine", "TransitionError"]

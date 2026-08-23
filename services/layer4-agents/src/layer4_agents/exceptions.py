from __future__ import annotations

"""Layer 4 Agents custom exceptions.

P1-25: WorkflowTimeoutError - Global workflow timeout enforcement
P1-42: ConcurrencyLimitExceeded - Max concurrent workflow limit
"""


class WorkflowTimeoutError(TimeoutError):
    """Raised when a workflow exceeds its global timeout.

    P1-25: Global workflow timeout enforcement (default 30 minutes)

    Attributes:
        workflow_id: ID of the timed-out workflow
        timeout_seconds: The timeout threshold that was exceeded
    """

    def __init__(
        self,
        message: str,
        workflow_id: str | None = None,
        timeout_seconds: int | None = None,
    ):
        super().__init__(message)
        self.workflow_id = workflow_id
        self.timeout_seconds = timeout_seconds


class ConcurrencyLimitExceeded(Exception):
    """Raised when max concurrent workflow limit is reached.

    P1-42: Maximum concurrent workflows per replica (default 10)

    Attributes:
        max_concurrent: The configured concurrency limit
        current_active: Number of currently active workflows
    """

    def __init__(
        self,
        message: str,
        max_concurrent: int | None = None,
        current_active: int | None = None,
    ):
        super().__init__(message)
        self.max_concurrent = max_concurrent
        self.current_active = current_active

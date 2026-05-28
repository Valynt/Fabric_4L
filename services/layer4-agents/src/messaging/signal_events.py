from __future__ import annotations

"""Signal streaming event models for WebSocket communication.

Defines the event schema for real-time signal discovery streaming
from Layer 4 to frontend clients.
"""


from datetime import UTC, datetime
from enum import Enum as PyEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..models.pain_signal import PainSignal


class SignalEventType(str, PyEnum):
    """Types of signal stream events."""

    SIGNAL_DISCOVERED = "signal_discovered"
    SIGNAL_COMPLETED = "signal_completed"
    SIGNAL_FAILED = "signal_failed"
    STREAM_COMPLETE = "stream_complete"


class ErrorCategory(str, PyEnum):
    """Categories of signal processing errors."""

    EXTRACTION = "extraction"
    ENRICHMENT = "enrichment"
    PERSISTENCE = "persistence"
    STREAMING = "streaming"
    UNKNOWN = "unknown"


class BaseSignalEvent(BaseModel):
    """Base class for all signal events."""

    model_config = ConfigDict(extra="forbid")

    event_type: SignalEventType = Field(..., description="Type of event")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Event timestamp"
    )
    prospect_id: str = Field(..., description="Associated prospect ID")
    event_id: str = Field(
        default_factory=lambda: f"evt_{datetime.now(UTC).timestamp()}",
        description="Unique event identifier"
    )

    def to_json(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dictionary."""
        return self.model_dump(mode="json")


class SignalDiscoveredEvent(BaseSignalEvent):
    """Event emitted when a signal is discovered (partial or complete).

    Sent during the extraction and enrichment pipeline to provide
    real-time updates to the frontend.
    """

    event_type: Literal[SignalEventType.SIGNAL_DISCOVERED] = Field(
        default=SignalEventType.SIGNAL_DISCOVERED
    )
    signal: PainSignal = Field(..., description="The discovered signal")
    partial: bool = Field(
        default=True,
        description="True if signal is still being populated"
    )
    stage: str = Field(
        default="extracted",
        description="Current pipeline stage: extracted, enriching, quantifying, complete"
    )
    progress_percent: int = Field(
        default=0, ge=0, le=100,
        description="Progress within this signal's processing"
    )


class SignalCompletedEvent(BaseSignalEvent):
    """Event emitted when a signal is fully processed.

    Indicates that all extraction, enrichment, and persistence
    stages have completed successfully.
    """

    event_type: Literal[SignalEventType.SIGNAL_COMPLETED] = Field(
        default=SignalEventType.SIGNAL_COMPLETED
    )
    signal_id: str = Field(..., description="Completed signal ID")
    final_signal: PainSignal = Field(..., description="Final complete signal")
    processing_duration_ms: int = Field(
        ..., ge=0, description="Total processing time in milliseconds"
    )


class SignalFailedEvent(BaseSignalEvent):
    """Event emitted when signal processing fails.

    Provides error details and retry information for client handling.
    """

    event_type: Literal[SignalEventType.SIGNAL_FAILED] = Field(
        default=SignalEventType.SIGNAL_FAILED
    )
    signal_id: str | None = Field(
        default=None,
        description="Signal ID if available, None if discovery failed"
    )
    error_category: ErrorCategory = Field(
        ..., description="Category of error for client handling"
    )
    error_message: str = Field(..., description="Human-readable error description")
    error_details: dict[str, Any] | None = Field(
        default=None, description="Additional error context"
    )
    retryable: bool = Field(
        ..., description="Whether client should allow retry"
    )
    retry_after_seconds: int | None = Field(
        default=None, description="Suggested retry delay if retryable"
    )


class SignalStreamCompleteEvent(BaseSignalEvent):
    """Event emitted when the entire signal stream completes.

    Sent after all signals for a prospect have been processed.
    """

    event_type: Literal[SignalEventType.STREAM_COMPLETE] = Field(
        default=SignalEventType.STREAM_COMPLETE
    )
    prospect_id: str = Field(..., description="Associated prospect ID")
    total_signals: int = Field(..., ge=0, description="Total signals discovered")
    completed_signals: int = Field(..., ge=0, description="Successfully processed")
    failed_signals: int = Field(..., ge=0, description="Failed to process")
    stream_duration_ms: int = Field(
        ..., ge=0, description="Total stream duration in milliseconds"
    )


# Union type for all signal events
SignalEvent = (
    SignalDiscoveredEvent |
    SignalCompletedEvent |
    SignalFailedEvent |
    SignalStreamCompleteEvent
)


def create_signal_discovered_event(
    prospect_id: str,
    signal: PainSignal,
    partial: bool = True,
    stage: str = "extracted",
    progress_percent: int = 0,
) -> SignalDiscoveredEvent:
    """Factory function for signal discovered events.

    Args:
        prospect_id: Associated prospect ID
        signal: The discovered signal
        partial: Whether signal is still being populated
        stage: Current pipeline stage
        progress_percent: Progress within this signal

    Returns:
        SignalDiscoveredEvent instance
    """
    return SignalDiscoveredEvent(
        prospect_id=prospect_id,
        signal=signal,
        partial=partial,
        stage=stage,
        progress_percent=progress_percent,
    )


def create_signal_completed_event(
    prospect_id: str,
    signal: PainSignal,
    duration_ms: int,
) -> SignalCompletedEvent:
    """Factory function for signal completed events.

    Args:
        prospect_id: Associated prospect ID
        signal: The completed signal
        duration_ms: Processing duration in milliseconds

    Returns:
        SignalCompletedEvent instance
    """
    return SignalCompletedEvent(
        prospect_id=prospect_id,
        signal_id=signal.id,
        final_signal=signal,
        processing_duration_ms=duration_ms,
    )


def create_signal_failed_event(
    prospect_id: str,
    error_category: ErrorCategory,
    error_message: str,
    signal_id: str | None = None,
    retryable: bool = False,
    error_details: dict[str, Any] | None = None,
) -> SignalFailedEvent:
    """Factory function for signal failed events.

    Args:
        prospect_id: Associated prospect ID
        error_category: Category of error
        error_message: Human-readable error description
        signal_id: Signal ID if available
        retryable: Whether client should allow retry
        error_details: Additional error context

    Returns:
        SignalFailedEvent instance
    """
    return SignalFailedEvent(
        prospect_id=prospect_id,
        signal_id=signal_id,
        error_category=error_category,
        error_message=error_message,
        retryable=retryable,
        error_details=error_details,
    )


def create_stream_complete_event(
    prospect_id: str,
    total_signals: int,
    completed_signals: int,
    failed_signals: int,
    duration_ms: int,
) -> SignalStreamCompleteEvent:
    """Factory function for stream complete events.

    Args:
        prospect_id: Associated prospect ID
        total_signals: Total signals discovered
        completed_signals: Successfully processed count
        failed_signals: Failed to process count
        duration_ms: Total stream duration

    Returns:
        SignalStreamCompleteEvent instance
    """
    return SignalStreamCompleteEvent(
        prospect_id=prospect_id,
        total_signals=total_signals,
        completed_signals=completed_signals,
        failed_signals=failed_signals,
        stream_duration_ms=duration_ms,
    )

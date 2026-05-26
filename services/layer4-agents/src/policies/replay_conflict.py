"""Canonical replay-conflict policy for Layer 4 workflows.

Defines an explicit, enforceable contract for conflict handling during
duplicate resumes / replays across all workflow types.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.agent_state import WorkflowStatus

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class NormalizedHash:
    """Canonical SHA-256 hash representation for strict typed comparison."""

    algorithm: str
    encoding: str
    digest_hex: str


class HashNormalizationError(ValueError):
    """Raised when a checkpoint hash cannot be normalized safely."""

    def __init__(self, message: str, details: dict[str, Any]):
        super().__init__(message)
        self.details = details


def _normalize_sha256_hash(value: str | None, *, field_name: str) -> NormalizedHash | None:
    """Normalize hash input to canonical sha256/hex/lowercase-64 format."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise HashNormalizationError(
            "Invalid hash type",
            {"field": field_name, "reason": "hash must be str", "type": type(value).__name__},
        )

    candidate = value.strip().lower()
    if candidate.startswith("sha256:"):
        candidate = candidate[len("sha256:") :]
    if candidate.startswith("0x"):
        candidate = candidate[2:]

    if not _SHA256_HEX_RE.fullmatch(candidate):
        raise HashNormalizationError(
            "Invalid hash encoding",
            {
                "field": field_name,
                "reason": "expected sha256 hex digest length=64",
                "length": len(candidate),
            },
        )

    return NormalizedHash(algorithm="sha256", encoding="hex", digest_hex=candidate)


class ReplayDecision(str, Enum):
    """Allowed policy outcomes for replay conflict checks."""

    REJECT = "reject"
    MERGE_SAFE = "merge-safe"
    FORCE_REPLAY = "force-replay"


class CollisionAction(str, Enum):
    """Action when a resume would overwrite a newer checkpoint."""

    FAIL = "fail"
    OVERWRITE = "overwrite"
    APPEND = "append"


class ReplayConflictPolicy(BaseModel):
    """Centralized replay-conflict policy artifact.

    Invariants:
      - strategy determines how duplicate replays are handled.
      - max_replay_age_seconds limits how old a checkpoint can be for resume.
      - require_exact_checkpoint_match enforces hash equality before resume.
      - on_collision governs behavior when resume targets diverge from latest.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    default_decision: ReplayDecision = Field(
        default=ReplayDecision.REJECT,
        description="Default outcome for duplicate or conflicting replay attempts",
    )
    max_replay_age_seconds: int = Field(
        default=86400,
        ge=0,
        description="Maximum age of a checkpoint eligible for resume",
    )
    require_exact_checkpoint_match: bool = Field(
        default=True,
        description="Require deterministic hash match before allowing resume",
    )
    allowed_statuses_for_resume: set[WorkflowStatus] = Field(
        default_factory=lambda: {
            WorkflowStatus.INTERRUPTED,
            WorkflowStatus.PAUSED,
            WorkflowStatus.PENDING,
            WorkflowStatus.RUNNING,
        },
        description="Workflow statuses that are eligible for resume",
    )
    on_collision: CollisionAction = Field(
        default=CollisionAction.FAIL,
        description="What to do if a resume would overwrite a newer checkpoint",
    )

    @field_validator("allowed_statuses_for_resume")
    @classmethod
    def _allowed_statuses_non_empty(cls, v: set[WorkflowStatus]) -> set[WorkflowStatus]:
        if not v:
            raise ValueError("allowed_statuses_for_resume must not be empty")
        return v


class ReplayConflictError(ValueError):
    """Raised when a replay/resume attempt violates the conflict policy."""

    pass


class ReplayConflictResolver:
    """Runtime enforcement of ReplayConflictPolicy."""

    DEFAULT_POLICY = ReplayConflictPolicy()

    def __init__(self, policy: ReplayConflictPolicy | None = None) -> None:
        self.policy = policy or self.DEFAULT_POLICY

    @staticmethod
    def compute_replay_fingerprint(
        run_id: str,
        tenant_id: str,
        checkpoint_id: str | None,
    ) -> str:
        """Deterministic hash for detecting duplicate replays.

        Returns:
            SHA-256 hex digest of the canonical replay identity.
        """
        canonical = json.dumps(
            {
                "run_id": run_id,
                "tenant_id": tenant_id,
                "checkpoint_id": checkpoint_id,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def validate_resume_attempt(
        self,
        *,
        workflow_status: WorkflowStatus,
        checkpoint_created_at: datetime | None,
        checkpoint_hash: str | None,
        expected_hash: str | None,
        latest_checkpoint_hash: str | None,
    ) -> None:
        """Validate a resume attempt against the active policy.

        Args:
            workflow_status: Current status of the workflow.
            checkpoint_created_at: When the target checkpoint was created.
            checkpoint_hash: Hash of the target checkpoint.
            expected_hash: Expected hash if exact-match is required.
            latest_checkpoint_hash: Hash of the most recent checkpoint.

        Raises:
            ReplayConflictError: If the resume attempt violates policy.
        """
        # Status guard
        if workflow_status not in self.policy.allowed_statuses_for_resume:
            raise ReplayConflictError(
                f"Replay rejected: workflow status {workflow_status.value} is not eligible for resume. "
                f"Allowed: {[s.value for s in self.policy.allowed_statuses_for_resume]}"
            )

        # Age guard
        if checkpoint_created_at is not None:
            age_seconds = (datetime.now(UTC) - checkpoint_created_at).total_seconds()
            if age_seconds > self.policy.max_replay_age_seconds:
                raise ReplayConflictError(
                    f"Replay rejected: checkpoint age {age_seconds:.0f}s exceeds "
                    f"max_replay_age_seconds ({self.policy.max_replay_age_seconds})"
                )

        try:
            normalized_checkpoint = _normalize_sha256_hash(
                checkpoint_hash, field_name="checkpoint_hash"
            )
            normalized_expected = _normalize_sha256_hash(
                expected_hash, field_name="expected_hash"
            )
            normalized_latest = _normalize_sha256_hash(
                latest_checkpoint_hash, field_name="latest_checkpoint_hash"
            )
        except HashNormalizationError as exc:
            raise ReplayConflictError(
                f"Replay rejected: hash normalization failed ({exc.details})"
            ) from exc

        # Exact hash match guard
        if self.policy.require_exact_checkpoint_match:
            if normalized_expected is not None and normalized_checkpoint != normalized_expected:
                raise ReplayConflictError(
                    f"Replay rejected: checkpoint hash mismatch "
                    f"(got={normalized_checkpoint}, expected={normalized_expected})"
                )

        # Collision guard
        if normalized_latest is not None and normalized_checkpoint != normalized_latest:
            if self.policy.on_collision == CollisionAction.FAIL:
                raise ReplayConflictError(
                    "Replay rejected: checkpoint collision/mismatch against latest checkpoint "
                    f"(target={normalized_checkpoint}, latest={normalized_latest})"
                )
            # For OVERWRITE / APPEND, we allow the caller to proceed but log the conflict

    def evaluate_duplicate_replay(
        self,
        *,
        run_id: str,
        tenant_id: str,
        checkpoint_id: str | None,
        seen_fingerprints: set[str],
        audit_justification: str | None = None,
    ) -> ReplayDecision:
        """Return deterministic policy decision for duplicate replay attempts."""
        fingerprint = self.compute_replay_fingerprint(run_id, tenant_id, checkpoint_id)
        if fingerprint not in seen_fingerprints:
            return ReplayDecision.MERGE_SAFE
        if audit_justification and audit_justification.strip():
            return ReplayDecision.FORCE_REPLAY
        return ReplayDecision.REJECT

"""Pydantic v2 models for LLM degradation policies (ADR-031, Pass 1).

Degradation is a declared policy, never an implicit code-path decision.
These models represent the declarative degradation ladders defined in
`harness.runtime.yaml` under `llm.degradation_policies`.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DegradationRungKind(str, Enum):
    """Types of rungs in a degradation ladder."""

    RETRY = "retry"
    FAILOVER = "failover"
    HEURISTIC = "heuristic"
    TEMPLATE = "template"


class OutputMarking(str, Enum):
    """Output marking governance requirements."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    NONE = "none"


class RetryRungConfig(BaseModel):
    """Configuration for a retry rung."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    same_model: int = Field(default=1, ge=1, description="Number of retry attempts with the same model")


class FailoverRungConfig(BaseModel):
    """Configuration for a failover rung."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    tier: str = Field(default="secondary_provider", description="Failover target tier")
    provider: str | None = Field(default=None, description="Explicit target provider override")
    model: str | None = Field(default=None, description="Explicit target model override")


class HeuristicRungConfig(BaseModel):
    """Configuration for a deterministic heuristic fallback rung."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(..., min_length=1, description="Identifier of the deterministic heuristic implementation")


class TemplateRungConfig(BaseModel):
    """Configuration for a template fallback rung."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(..., min_length=1, description="Identifier of the template fallback implementation")


class DegradationLadderStep(BaseModel):
    """A single step/rung in a degradation policy ladder.

    Can be initialized from YAML dictionaries such as:
      - `{"retry": {"same_model": 1}}`
      - `{"failover": {"tier": "secondary_provider"}}`
      - `{"heuristic": {"id": "chat_deterministic_v1"}}`
      - `{"template": {"id": "narrative_fallback_v3"}}`
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    retry: RetryRungConfig | None = None
    failover: FailoverRungConfig | None = None
    heuristic: HeuristicRungConfig | None = None
    template: TemplateRungConfig | None = None

    @model_validator(mode="before")
    @classmethod
    def _validate_single_rung(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # If already structured with a single key matching one of the rung types
        rungs = {"retry", "failover", "heuristic", "template"}
        present = [k for k in data.keys() if k in rungs and data[k] is not None]
        if len(present) != 1:
            raise ValueError(
                f"DegradationLadderStep must define exactly one rung type (one of {sorted(rungs)}), "
                f"got present keys: {list(data.keys())}"
            )
        return data

    @property
    def kind(self) -> DegradationRungKind:
        """Return the active rung kind for this step."""
        if self.retry is not None:
            return DegradationRungKind.RETRY
        if self.failover is not None:
            return DegradationRungKind.FAILOVER
        if self.heuristic is not None:
            return DegradationRungKind.HEURISTIC
        if self.template is not None:
            return DegradationRungKind.TEMPLATE
        raise ValueError("DegradationLadderStep has no active rung")

    @property
    def config(self) -> RetryRungConfig | FailoverRungConfig | HeuristicRungConfig | TemplateRungConfig:
        """Return the typed configuration object for this step."""
        if self.retry is not None:
            return self.retry
        if self.failover is not None:
            return self.failover
        if self.heuristic is not None:
            return self.heuristic
        if self.template is not None:
            return self.template
        raise ValueError("DegradationLadderStep has no active configuration")


class DegradationPolicy(BaseModel):
    """Complete degradation policy for a model task."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ladder: list[DegradationLadderStep] = Field(
        default_factory=list,
        description="Ordered sequence of fallback rungs to evaluate on failure",
    )
    output_marking: OutputMarking = Field(
        default=OutputMarking.REQUIRED,
        description="Whether degraded outputs must carry output marking and audit events",
    )

    @property
    def max_retries(self) -> int:
        """Total retry count configured in the ladder."""
        total = 0
        for step in self.ladder:
            if step.kind == DegradationRungKind.RETRY and isinstance(step.config, RetryRungConfig):
                total += step.config.same_model
        return total

    @property
    def has_failover(self) -> bool:
        """Whether a failover rung is defined."""
        return any(step.kind == DegradationRungKind.FAILOVER for step in self.ladder)

    @property
    def has_heuristic(self) -> bool:
        """Whether a heuristic fallback rung is defined."""
        return any(step.kind == DegradationRungKind.HEURISTIC for step in self.ladder)

    @property
    def has_template(self) -> bool:
        """Whether a template fallback rung is defined."""
        return any(step.kind == DegradationRungKind.TEMPLATE for step in self.ladder)

    @property
    def heuristic_id(self) -> str | None:
        """Identifier of the first configured heuristic rung, if any."""
        for step in self.ladder:
            if step.kind == DegradationRungKind.HEURISTIC and isinstance(step.config, HeuristicRungConfig):
                return step.config.id
        return None

    @property
    def template_id(self) -> str | None:
        """Identifier of the first configured template rung, if any."""
        for step in self.ladder:
            if step.kind == DegradationRungKind.TEMPLATE and isinstance(step.config, TemplateRungConfig):
                return step.config.id
        return None


class DegradationPoliciesConfig(BaseModel):
    """Mapping of model tasks to their declared degradation policies."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    policies: dict[str, DegradationPolicy] = Field(
        default_factory=dict,
        description="Mapping from task identifier (conversation, narrative, reasoning) to policy",
    )

    @model_validator(mode="before")
    @classmethod
    def _extract_policies(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # If the input is the top-level or llm dictionary, extract degradation_policies
        if "llm" in data and isinstance(data["llm"], dict) and "degradation_policies" in data["llm"]:
            return {"policies": data["llm"]["degradation_policies"]}
        if "degradation_policies" in data and isinstance(data["degradation_policies"], dict):
            return {"policies": data["degradation_policies"]}
        if "policies" in data and isinstance(data["policies"], dict):
            return data
        # Otherwise assume the dict itself is a mapping of task -> policy
        # Filter out non-task keys if any (or treat entire dict as policies)
        return {"policies": data}

    def get_policy(self, task_name: str) -> DegradationPolicy | None:
        """Retrieve policy for a given model task."""
        return self.policies.get(task_name)

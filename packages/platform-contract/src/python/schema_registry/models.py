"""Pydantic models for the Schema Registry."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class LifecycleStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    PUBLISHED = "PUBLISHED"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


class SchemaKind(str, Enum):
    API_REQUEST = "API_REQUEST"
    API_RESPONSE = "API_RESPONSE"
    API_ERROR = "API_ERROR"
    COMMAND = "COMMAND"
    EVENT_ENVELOPE = "EVENT_ENVELOPE"
    EVENT_DATA = "EVENT_DATA"
    PROVIDER_OBSERVATION = "PROVIDER_OBSERVATION"
    TOOL_INPUT = "TOOL_INPUT"
    TOOL_OUTPUT = "TOOL_OUTPUT"
    AUDIT_EVIDENCE = "AUDIT_EVIDENCE"
    COMMON_VALUE_OBJECT = "COMMON_VALUE_OBJECT"


class AuthoringDirection(str, Enum):
    SCHEMA_FIRST = "SCHEMA_FIRST"
    CODE_FIRST_WITH_GENERATED_SCHEMA = "CODE_FIRST_WITH_GENERATED_SCHEMA"
    OPENAPI_FIRST = "OPENAPI_FIRST"
    ASYNCAPI_FIRST = "ASYNCAPI_FIRST"


class CompatibilityPolicy(str, Enum):
    ADDITIVE_WITHIN_MAJOR = "ADDITIVE_WITHIN_MAJOR"
    NONE = "NONE"
    FULL = "FULL"


class ContactInfo(BaseModel):
    name: str | None = None
    email: str | None = None
    slack: str | None = None


class Owner(BaseModel):
    team: str
    contacts: list[ContactInfo] = Field(default_factory=list)


class ExampleRecord(BaseModel):
    name: str | None = None
    description: str | None = None
    payload: dict[str, Any] | None = None


class Fixture(BaseModel):
    path: str
    description: str | None = None


class Classification(BaseModel):
    public: bool = False
    pii: bool = False
    financial: bool = False
    regulated: bool = False
    hipaa: bool = False
    soc2: bool = False


class Subscription(BaseModel):
    team: str | None = None
    channel: str | None = None
    events: list[str] = Field(default_factory=list)


class SchemaRecord(BaseModel):
    schema_id: str = Field(..., pattern=r"^[a-z0-9.-]+$")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    kind: SchemaKind
    domain: str
    owner: Owner | str
    status: LifecycleStatus
    artifact: str
    content_hash: str | None = None
    authoring_direction: AuthoringDirection = AuthoringDirection.SCHEMA_FIRST
    source_of_truth: str | None = None
    compatibility_policy: CompatibilityPolicy = CompatibilityPolicy.ADDITIVE_WITHIN_MAJOR
    examples: list[ExampleRecord | str] = Field(default_factory=list)
    fixtures: list[Fixture] = Field(default_factory=list)
    classification: Classification = Field(default_factory=Classification)
    subscriptions: list[Subscription] = Field(default_factory=list)
    changelog: str | None = None
    reviewed_by: str | None = None
    review_date: datetime | None = None
    published_at: datetime | None = None
    deprecated_at: datetime | None = None
    retired_at: datetime | None = None
    description: str | None = None

    # Extra fields from existing registry.yaml that we keep but don't strictly model
    model_config = {"extra": "ignore"}

    @field_validator("owner", mode="before")
    @classmethod
    def parse_owner(cls, v: Any) -> Any:
        if isinstance(v, str):
            return Owner(team=v)
        return v

    @field_validator("examples", mode="before")
    @classmethod
    def parse_examples(cls, v: Any) -> Any:
        if not isinstance(v, list):
            return v
        result: list[ExampleRecord | str] = []
        for item in v:
            if isinstance(item, str):
                # File path reference; wrap as example record without payload
                result.append(ExampleRecord(name=item, description=f"Fixture: {item}"))
            else:
                result.append(item)
        return result

    @field_validator("review_date", "published_at", "deprecated_at", "retired_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> Any:
        if v is None or isinstance(v, datetime):
            return v
        if isinstance(v, str):
            v = v.replace("Z", "+00:00")
            return datetime.fromisoformat(v)
        return v

    @model_validator(mode="after")
    def check_source_of_truth_for_generated(self) -> "SchemaRecord":
        if self.authoring_direction == AuthoringDirection.CODE_FIRST_WITH_GENERATED_SCHEMA and not self.source_of_truth:
            raise ValueError("source_of_truth is required when authoring_direction is CODE_FIRST_WITH_GENERATED_SCHEMA")
        return self

    @model_validator(mode="after")
    def check_timestamps_match_status(self) -> "SchemaRecord":
        if self.status == LifecycleStatus.PUBLISHED and not self.published_at:
            raise ValueError("published_at is required when status is PUBLISHED")
        if self.status == LifecycleStatus.DEPRECATED and not self.deprecated_at:
            raise ValueError("deprecated_at is required when status is DEPRECATED")
        if self.status == LifecycleStatus.RETIRED and not self.retired_at:
            raise ValueError("retired_at is required when status is RETIRED")
        return self

    def compute_content_hash(self, artifact_path: Path | None = None) -> str:
        """Compute SHA-256 of the artifact file contents."""
        if artifact_path is None:
            return self.content_hash or ""
        if not artifact_path.exists():
            return ""
        content = artifact_path.read_bytes()
        return f"sha256:{hashlib.sha256(content).hexdigest()}"

    def key(self) -> str:
        return f"{self.schema_id}@{self.version}"


class CompatibilityRule(BaseModel):
    rule_id: str = Field(alias="id")
    description: str = Field(alias="text")
    severity: str = "ERROR"
    check: str = ""

    model_config = {"populate_by_name": True, "extra": "ignore"}


class PolicyDefinition(BaseModel):
    policy_id: CompatibilityPolicy | None = None
    description: str = ""
    rules: list[CompatibilityRule] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


class LifecycleTransition(BaseModel):
    from_status: LifecycleStatus
    to_status: LifecycleStatus
    allowed: bool
    requires_review: bool = False
    notes: str | None = None


class CompatibilityPolicyDoc(BaseModel):
    version: str = "1.0.0"
    last_updated: datetime | None = None
    default_policy: CompatibilityPolicy = CompatibilityPolicy.ADDITIVE_WITHIN_MAJOR
    policies: list[PolicyDefinition] | dict[str, PolicyDefinition] = Field(default_factory=list)
    lifecycle_transitions: list[LifecycleTransition] = Field(default_factory=list)

    model_config = {"extra": "ignore"}

    @field_validator("last_updated", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> Any:
        if v is None or isinstance(v, datetime):
            return v
        if isinstance(v, str):
            v = v.replace("Z", "+00:00")
            return datetime.fromisoformat(v)
        return v

    @field_validator("policies", mode="before")
    @classmethod
    def parse_policies(cls, v: Any) -> Any:
        if isinstance(v, dict):
            policies: list[PolicyDefinition] = []
            for key, val in v.items():
                if isinstance(val, dict):
                    val["policy_id"] = key
                policies.append(val)
            return policies
        return v

    @field_validator("lifecycle_transitions", mode="before")
    @classmethod
    def parse_lifecycle_transitions(cls, v: Any) -> Any:
        if isinstance(v, dict):
            transitions: list[LifecycleTransition] = []
            if "valid" in v:
                for pair in v["valid"]:
                    if isinstance(pair, list) and len(pair) == 2:
                        transitions.append(
                            LifecycleTransition(
                                from_status=LifecycleStatus(pair[0]),
                                to_status=LifecycleStatus(pair[1]),
                                allowed=True,
                            )
                        )
            if "forbidden" in v:
                for pair in v["forbidden"]:
                    if isinstance(pair, list) and len(pair) == 2:
                        transitions.append(
                            LifecycleTransition(
                                from_status=LifecycleStatus(pair[0]),
                                to_status=LifecycleStatus(pair[1]),
                                allowed=False,
                            )
                        )
            return transitions
        return v


class RegistryCatalog(BaseModel):
    registry_version: str = "1.0.0"
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    policies: CompatibilityPolicyDoc | None = None
    schemas: list[SchemaRecord] = Field(default_factory=list)
    subscriptions: list[Subscription] = Field(default_factory=list)

    model_config = {"extra": "ignore"}

    @model_validator(mode="after")
    def check_unique_schema_keys(self) -> "RegistryCatalog":
        keys = [s.key() for s in self.schemas]
        if len(keys) != len(set(keys)):
            duplicates = {k for k in keys if keys.count(k) > 1}
            raise ValueError(f"Duplicate schema records found: {duplicates}")
        return self

    def get_schema(self, schema_id: str, version: str | None = None) -> SchemaRecord | None:
        matches = [s for s in self.schemas if s.schema_id == schema_id]
        if not matches:
            return None
        if version:
            return next((s for s in matches if s.version == version), None)
        return max(matches, key=lambda s: _semver_tuple(s.version))

    def get_published_latest(self, schema_id: str) -> SchemaRecord | None:
        matches = [s for s in self.schemas if s.schema_id == schema_id and s.status == LifecycleStatus.PUBLISHED]
        if not matches:
            return None
        return max(matches, key=lambda s: _semver_tuple(s.version))

    def get_dependents(self, schema_id: str) -> list[SchemaRecord]:
        return []


def _semver_tuple(v: str) -> tuple[int, ...]:
    parts = v.split(".")
    return tuple(int(p) for p in parts)

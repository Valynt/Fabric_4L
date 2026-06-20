"""Pure, side-effect-free connector resolution contract and artifact model.

No network calls, secret access, or persistence operations are performed here.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CustodyMode(str, Enum):
    """Data storage and retention compliance constraints."""

    FABRIC_FULL_CUSTODY = "fabric_full_custody"
    REFERENCE_EXTRACT = "reference_extract"
    CUSTOMER_HOSTED = "customer_hosted"


class ConnectorKind(str, Enum):
    """Technical classification of the resolved ingestion mechanism."""

    LOCAL = "local"
    FILE = "file"
    CRM = "crm"
    CALL = "call"
    MEETING = "meeting"
    WEB = "web"


class ExternalSystem(str, Enum):
    """Enterprise ecosystems supported by the mapping layer."""

    SALESFORCE = "salesforce"
    HUBSPOT = "hubspot"
    GONG = "gong"
    CHORUS = "chorus"
    ZOOM = "zoom"
    TEAMS = "teams"
    GOOGLE_MEET = "google_meet"
    GENERIC = "generic"


class FetchStrategy(str, Enum):
    """Methodological approach used to pull the underlying source payload."""

    NONE = "none"
    LOCAL_PAYLOAD = "local_payload"
    OBJECT_STORAGE = "object_storage"
    EXTERNAL_CONNECTOR = "external_connector"
    CUSTOMER_HOSTED_CONNECTOR = "customer_hosted_connector"
    WEB_FETCH = "web_fetch"


# Mapping from the repository's single-letter custody codes to the spec names.
_REPO_CUSTODY_TO_SPEC: dict[str, str] = {
    "A": CustodyMode.FABRIC_FULL_CUSTODY.value,
    "B": CustodyMode.REFERENCE_EXTRACT.value,
    "C": CustodyMode.CUSTOMER_HOSTED.value,
}


def normalize_custody_mode(value: str | CustodyMode) -> str:
    """Return the canonical spec custody-mode string.

    Accepts either the spec enum/value, or the repository's single-letter code.
    Unknown values are returned unchanged so the caller can fail safely.
    """
    if isinstance(value, CustodyMode):
        return value.value
    mapped = _REPO_CUSTODY_TO_SPEC.get(value)
    return mapped if mapped is not None else value


class ConnectorResolutionError(Exception):
    """Configuration or input validation failure during connector resolution."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


class ConnectorResolution(BaseModel):
    """Deterministic, credential-free artifact from the RESOLVING_CONNECTOR stage."""

    schema_version: int = Field(default=1)
    connector_kind: ConnectorKind
    connector_name: str
    external_system: ExternalSystem | None = None
    external_object_type: str | None = None
    external_object_id: str | None = None
    custody_mode: CustodyMode
    field_scope_id: str | None = None
    customer_hosted: bool = False
    connector_endpoint: str | None = None
    connector_id: str | None = None
    policy_version: str = Field(default="default-v1")
    fetch_strategy: FetchStrategy
    requires_fetch: bool
    requires_snapshot_verification: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("connector_endpoint")
    @classmethod
    def sanitize_endpoint(cls, value: str | None) -> str | None:
        """Prevent injection of credentials inside raw URL fields."""
        if value is not None and "@" in value:
            raise ValueError("Credentials are not permitted inside connector_endpoint URLs.")
        return value

    def to_artifact(self) -> dict[str, Any]:
        """Serialize to a JSON-safe, hashable artifact dictionary."""
        return self.model_dump()

    @classmethod
    def from_artifact(cls, data: dict[str, Any]) -> ConnectorResolution:
        """Reconstruct from an artifact dictionary."""
        return cls(**data)

    def config_hash(self) -> str:
        """Generate a deterministic SHA-256 hash of the routing configuration."""
        payload = {
            "connector_kind": self.connector_kind.value,
            "external_system": self.external_system.value if self.external_system else None,
            "connector_name": self.connector_name,
            "custody_mode": self.custody_mode.value,
            "field_scope_id": self.field_scope_id,
            "customer_hosted": self.customer_hosted,
            "connector_ref": self.connector_endpoint or self.connector_id,
            "policy_version": self.policy_version,
        }
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()

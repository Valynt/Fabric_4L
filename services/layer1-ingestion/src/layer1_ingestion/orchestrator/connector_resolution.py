"""Pure, side-effect-free connector resolution contract and artifact model.

No network calls, secret access, or persistence operations are performed here.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from layer1_ingestion.shared.custody_policy import CustodyPolicyService
from layer1_ingestion.shared.models import SourceType


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


def normalize_custody_mode(value: str | CustodyMode | Any) -> str:
    """Return the canonical spec custody-mode string.

    Accepts:
      - The local spec CustodyMode enum
      - The SQLAlchemy DB CustodyMode enum (which uses single-letter values)
      - The single-letter repository code (A/B/C)
      - A full spec name string

    Unknown values are returned unchanged so the caller can fail safely.
    """
    if isinstance(value, CustodyMode):
        return value.value
    if isinstance(value, Enum):
        value = value.value
    if not isinstance(value, str):
        return value
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
    headers: dict[str, str] | None = None
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
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _normalize_source_type(value: str | SourceType | Any) -> SourceType:
    """Return a canonical `SourceType` from user input and domain objects."""
    if isinstance(value, SourceType):
        return value
    if not isinstance(value, str):
        raise ConnectorResolutionError(
            "UNSUPPORTED_SOURCE_TYPE",
            f"source_type {value!r} is not supported.",
        )
    try:
        return SourceType(value.lower())
    except ValueError as exc:
        raise ConnectorResolutionError(
            "UNSUPPORTED_SOURCE_TYPE",
            f"Unsupported source type '{value}'. Allowed: {', '.join(s.value for s in SourceType)}",
        ) from exc


def _merge_metadata(
    source: Any,
    source_version: Any | None,
) -> dict[str, Any]:
    """Merge metadata from `SourceVersion` and `IngestedSource` payloads."""
    merged: dict[str, Any] = {}
    source_meta = getattr(source, "meta", None)
    if isinstance(source_meta, dict):
        merged.update(source_meta)
    external_reference = getattr(source, "external_reference", None)
    if isinstance(external_reference, str) and external_reference.strip():
        merged.setdefault("external_reference", external_reference.strip())
    source_url = getattr(source, "source_url", None)
    if isinstance(source_url, str) and source_url.strip():
        merged.setdefault("source_url", source_url.strip())
    if source_version is not None:
        version_meta = getattr(source_version, "meta", None)
        if isinstance(version_meta, dict):
            merged.update(version_meta)
        source_uri = getattr(source_version, "source_uri", None)
        if isinstance(source_uri, str) and source_uri.strip():
            merged.setdefault("source_uri", source_uri.strip())
    return merged


def _as_bool(value: Any) -> bool:
    """Best-effort boolean conversion for loosely typed metadata."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "t", "yes", "y"}
    return bool(value)


def _default_connector_name(source_type: SourceType, *, customer_hosted: bool) -> str:
    """Return a default connector backend name for the source type."""
    if source_type in (SourceType.AUDIO, SourceType.MEETING):
        return "s3_reference"
    if source_type == SourceType.CRM:
        return "customer_hosted" if customer_hosted else "crm_connector"
    return "postgres"


def _pick_url(metadata: dict[str, Any], source: Any | None = None) -> str | None:
    """Read an incoming URL field using a permissive key list."""
    for key in ("url", "source_url", "link", "source_link", "source_uri"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if source is not None:
        source_reference = getattr(source, "external_reference", None)
        if isinstance(source_reference, str) and source_reference.strip():
            return source_reference.strip()
    return None


def _pick_storage_ref(
    metadata: dict[str, Any],
    source_version: Any | None,
) -> str | None:
    """Read a stable storage reference for object-backend fetch stages."""
    storage_ref = metadata.get("storage_ref")
    if isinstance(storage_ref, str) and storage_ref.strip():
        return storage_ref.strip()

    raw_storage_uri = getattr(source_version, "raw_storage_uri", None)
    return raw_storage_uri if isinstance(raw_storage_uri, str) and raw_storage_uri.strip() else None


def resolve_connector_for_source(
    source: Any,
    source_version: Any | None = None,
) -> ConnectorResolution:
    """Map a logical source to connector kind, strategy, and fetch metadata."""
    source_type = _normalize_source_type(getattr(source, "source_type", None))
    metadata = _merge_metadata(source, source_version)

    custody_mode = normalize_custody_mode(
        getattr(source, "custody_mode", CustodyMode.REFERENCE_EXTRACT.value)
    )

    customer_hosted = _as_bool(metadata.get("customer_hosted", False)) or (
        custody_mode == CustodyMode.CUSTOMER_HOSTED.value
    )

    # Validate connector naming against the custody policy before resolving connector
    # behavior, so unsupported backends fail early.
    custody = CustodyPolicyService().decide(
        source_type,
        connector_name=metadata.get("connector_name"),
        customer_hosted=customer_hosted,
    )

    connector_name = metadata.get("connector_name") or _default_connector_name(
        source_type,
        customer_hosted=customer_hosted,
    )
    try:
        CustodyPolicyService().validate_connector_against_policy(custody, connector_name)
    except ValueError as exc:
        raise ConnectorResolutionError(
            "UNSUPPORTED_CONNECTOR",
            f"Connector '{connector_name}' is not allowed for source_type '{source_type.value}'.",
        ) from exc

    if source_type in (SourceType.NOTES, SourceType.PDF):
        return ConnectorResolution(
            connector_kind=ConnectorKind.LOCAL,
            connector_name=connector_name,
            custody_mode=custody_mode,
            policy_version=custody.policy_version,
            fetch_strategy=FetchStrategy.LOCAL_PAYLOAD,
            requires_fetch=True,
            requires_snapshot_verification=False,
            metadata={
                "source_type": source_type.value,
                "source_version_id": getattr(source_version, "id", None),
            },
        )

    if source_type == SourceType.URL:
        url = _pick_url(metadata, source)
        if not url:
            raise ConnectorResolutionError(
                "UNSUPPORTED_CONNECTOR_CONFIG",
                "URL source type requires a URL in source metadata.",
            )
        return ConnectorResolution(
            connector_kind=ConnectorKind.WEB,
            connector_name=connector_name,
            custody_mode=custody_mode,
            policy_version=custody.policy_version,
            fetch_strategy=FetchStrategy.WEB_FETCH,
            requires_fetch=True,
            requires_snapshot_verification=False,
            metadata={"url": url, "source_type": source_type.value},
        )

    if source_type in (SourceType.AUDIO, SourceType.MEETING):
        storage_ref = _pick_storage_ref(metadata, source_version)
        if not storage_ref:
            raise ConnectorResolutionError(
                "UNSUPPORTED_CONNECTOR_CONFIG",
                f"{source_type.value} source requires storage_ref or source_version.raw_storage_uri.",
            )
        return ConnectorResolution(
            connector_kind=ConnectorKind.FILE,
            connector_name=connector_name,
            custody_mode=custody_mode,
            policy_version=custody.policy_version,
            fetch_strategy=FetchStrategy.OBJECT_STORAGE,
            requires_fetch=True,
            requires_snapshot_verification=False,
            metadata={
                "storage_ref": storage_ref,
                "source_type": source_type.value,
            },
        )

    if source_type == SourceType.CRM:
        metadata_url = _pick_url(metadata, source) or metadata.get("metadata_url")
        if metadata_url:
            return ConnectorResolution(
                connector_kind=ConnectorKind.CRM,
                connector_name=connector_name,
                external_system=metadata.get("external_system"),
                external_object_type=metadata.get("external_object_type"),
                external_object_id=metadata.get("external_object_id"),
                custody_mode=custody_mode,
                policy_version=custody.policy_version,
                fetch_strategy=FetchStrategy.CUSTOMER_HOSTED_CONNECTOR,
                requires_fetch=True,
                requires_snapshot_verification=False,
                metadata={
                    "metadata_url": metadata_url,
                    "source_type": source_type.value,
                },
            )

        storage_ref = _pick_storage_ref(metadata, source_version)
        if not storage_ref:
            raise ConnectorResolutionError(
                "UNSUPPORTED_CONNECTOR_CONFIG",
                "CRM source requires either metadata_url or storage_ref/raw_storage_uri.",
            )
        return ConnectorResolution(
            connector_kind=ConnectorKind.CRM,
            connector_name=connector_name,
            external_system=metadata.get("external_system"),
            external_object_type=metadata.get("external_object_type"),
            external_object_id=metadata.get("external_object_id"),
            custody_mode=custody_mode,
            policy_version=custody.policy_version,
            fetch_strategy=FetchStrategy.OBJECT_STORAGE,
            requires_fetch=True,
            requires_snapshot_verification=False,
            metadata={"storage_ref": storage_ref, "source_type": source_type.value},
        )

    raise ConnectorResolutionError(
        "UNSUPPORTED_SOURCE_TYPE",
        f"Unsupported source type '{source_type.value}'.",
    )

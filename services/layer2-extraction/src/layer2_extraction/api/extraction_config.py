"""Extraction request configuration helpers."""

from __future__ import annotations

import hashlib
import os
from typing import Any

from value_fabric.shared.error_handling.exceptions import ValidationError


def resolve_value_pack_scope(extraction_config: dict[str, Any]) -> str:
    return str(extraction_config.get("value_pack_scope") or extraction_config.get("value_pack") or "default")


def build_idempotency_key(
    *,
    tenant_id: str,
    source_url: str,
    content_id: str,
    extraction_config: dict[str, Any],
) -> str:
    extraction_version = str(extraction_config.get("extraction_version") or "v1")
    value_pack_scope = resolve_value_pack_scope(extraction_config)
    source_hash = hashlib.sha256(f"{content_id}|{source_url}".encode()).hexdigest()
    payload = f"{tenant_id}|{source_hash}|{extraction_version}|{value_pack_scope}"
    return hashlib.sha256(payload.encode()).hexdigest()


def validated_extraction_config(
    extraction_config: dict[str, Any],
    *,
    tenant_id: str,
    operation: str | None = None,
) -> dict[str, Any]:
    """Return extraction config with required runtime metadata populated."""
    config = dict(extraction_config)
    config["tenant_id"] = tenant_id
    model_version = config.get("model_version") or os.getenv("EXTRACTION_MODEL")
    if not model_version:
        message = "model_version is required in extraction_config or EXTRACTION_MODEL env var"
        if operation:
            message = f"{message} for {operation}"
        raise ValidationError(message=message)
    if not config.get("schema_version"):
        message = "schema_version is required in extraction_config"
        if operation:
            message = f"{message} for {operation}"
        raise ValidationError(message=message)
    if not config.get("prompt_version"):
        message = "prompt_version is required in extraction_config"
        if operation:
            message = f"{message} for {operation}"
        raise ValidationError(message=message)
    config["model_version"] = str(model_version)
    return config

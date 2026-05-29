from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

from ..settings import get_layer6_settings

LOGGER = logging.getLogger("layer6.startup")


def config_fingerprint(config: dict[str, Any]) -> str:
    payload = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def emit_startup_metadata(*, service: str, version: str, build_sha: str, config: dict[str, Any]) -> None:
    LOGGER.info(
        "layer6_startup",
        extra={
            "service": service,
            "version": version,
            "build_sha": build_sha,
            "config_fingerprint": config_fingerprint(config),
        },
    )


def runtime_metadata_from_env(default_version: str = "dev") -> dict[str, str]:
    settings = get_layer6_settings()
    return {
        "service": settings.layer6_service_name,
        "version": (
            settings.layer6_version
            or os.getenv("APP_VERSION")
            or os.getenv("VERSION")
            or default_version
        ),
        "build_sha": (
            settings.layer6_build_sha
            or os.getenv("BUILD_SHA")
            or os.getenv("GIT_SHA")
            or "unknown"
        ),
    }

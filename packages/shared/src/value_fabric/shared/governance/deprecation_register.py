"""Canonical loader for the repository deprecation/compatibility register.

Single source of truth: ``docs/deprecation_register.json`` at the repository
root. The register is a JSON object with an ``items`` array; every consumer
(runtime deprecation headers, service startup warnings, CI gates, and generated
documentation) must read it through this module so the schema and the resolved
path can never drift apart.

Failure policy: a missing, unreadable, or malformed register raises
``DeprecationRegisterError``. Callers that must not fail closed (for example a
request-path header helper) opt in explicitly via ``default=``; there is no
silent empty-register fallback.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

REGISTER_RELATIVE_PATH = Path("docs") / "deprecation_register.json"
"""Location of the register relative to the repository root."""

REGISTER_PATH_ENV_VAR = "DEPRECATION_REGISTER_PATH"
"""Explicit override for the register path (used by tests and containers)."""

ITEMS_KEY = "items"
"""The only supported top-level key holding register entries."""

_REQUIRED_ITEM_FIELDS = ("feature", "target_removal")


class DeprecationRegisterError(RuntimeError):
    """Raised when the deprecation register is missing or malformed."""


@dataclass(frozen=True)
class DeprecationItem:
    """A single typed register entry."""

    feature: str
    target_removal: str
    path: str = ""
    owner: str = ""
    introduced: str = ""
    deprecated_since: str = ""
    status: str = ""
    rationale: str = ""
    successor: str = ""
    telemetry: str = ""
    issue: str = ""

    @property
    def removal_date(self) -> date:
        """``target_removal`` parsed as a date."""
        return datetime.strptime(self.target_removal, "%Y-%m-%d").replace(tzinfo=UTC).date()

    @property
    def is_deferred(self) -> bool:
        """True when governance has explicitly deferred removal with a rationale."""
        return self.status == "deferred" and bool(self.rationale)

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> DeprecationItem:
        missing = [field for field in _REQUIRED_ITEM_FIELDS if not payload.get(field)]
        if missing:
            raise DeprecationRegisterError(
                f"Deprecation register item is missing required field(s) {missing}: {payload!r}"
            )
        known = {field.name for field in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{key: value for key, value in payload.items() if key in known})


def resolve_register_path(start: Path | None = None) -> Path:
    """Resolve the register path.

    Precedence: ``DEPRECATION_REGISTER_PATH`` env var, then the nearest ancestor
    directory of ``start`` (or this module) that contains
    ``docs/deprecation_register.json``, then the current working directory.
    """
    override = os.getenv(REGISTER_PATH_ENV_VAR)
    if override:
        return Path(override).expanduser()

    origins = [start] if start is not None else []
    origins.extend([Path(__file__).resolve(), Path.cwd().resolve()])
    for origin in origins:
        origin = origin.resolve()
        candidates = [origin, *origin.parents] if origin.is_dir() else list(origin.parents)
        for candidate in candidates:
            register = candidate / REGISTER_RELATIVE_PATH
            if register.is_file():
                return register

    return Path.cwd().resolve() / REGISTER_RELATIVE_PATH


def load_register(start: Path | None = None) -> dict[str, Any]:
    """Load and validate the raw register payload.

    Raises:
        DeprecationRegisterError: the file is absent, unreadable, not an
            object, or does not carry an ``items`` list.
    """
    register_path = resolve_register_path(start)
    try:
        raw = register_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DeprecationRegisterError(
            f"Deprecation register not readable at {register_path}: {exc}"
        ) from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DeprecationRegisterError(
            f"Deprecation register at {register_path} is not valid JSON: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise DeprecationRegisterError(
            f"Deprecation register at {register_path} must be a JSON object, got {type(payload).__name__}"
        )
    if not isinstance(payload.get(ITEMS_KEY), list):
        raise DeprecationRegisterError(
            f"Deprecation register at {register_path} must contain an {ITEMS_KEY!r} array"
        )
    return payload


def load_items(start: Path | None = None) -> list[DeprecationItem]:
    """Load the register and return typed items."""
    payload = load_register(start)
    return [DeprecationItem.from_mapping(item) for item in payload[ITEMS_KEY]]


def find_item(
    selector: str,
    *,
    items: list[DeprecationItem] | None = None,
) -> DeprecationItem | None:
    """Find the register entry whose ``path`` or ``feature`` matches ``selector``."""
    for item in items if items is not None else load_items():
        if selector and (selector in item.path or selector in item.feature):
            return item
    return None


def removal_date_for(selector: str, *, default: str | None = None) -> str:
    """Return the registered ``target_removal`` for ``selector``.

    Args:
        selector: route path or feature identifier to look up.
        default: value returned when the register has no matching entry. When
            ``None`` (the default) a missing entry raises, so an unregistered
            compatibility surface cannot silently advertise a sunset date.
    """
    item = find_item(selector)
    if item is not None:
        return item.target_removal
    if default is not None:
        return default
    raise DeprecationRegisterError(
        f"No deprecation register entry matches {selector!r}; register it in "
        f"{REGISTER_RELATIVE_PATH} before advertising a sunset date."
    )


def overdue_items(
    *,
    today: date | None = None,
    items: list[DeprecationItem] | None = None,
) -> list[DeprecationItem]:
    """Items whose removal date has passed without an approved deferral."""
    reference = today or datetime.now(UTC).date()
    resolved = items if items is not None else load_items()
    return [
        item
        for item in resolved
        if item.removal_date < reference and not item.is_deferred
    ]


__all__ = [
    "ITEMS_KEY",
    "REGISTER_PATH_ENV_VAR",
    "REGISTER_RELATIVE_PATH",
    "DeprecationItem",
    "DeprecationRegisterError",
    "find_item",
    "load_items",
    "load_register",
    "overdue_items",
    "removal_date_for",
    "resolve_register_path",
]

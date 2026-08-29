"""Compatibility engine implementing ADDITIVE_WITHIN_MAJOR and other policies."""

from __future__ import annotations

import copy
from typing import Any

from .models import CompatibilityPolicy, CompatibilityPolicyDoc, LifecycleStatus, SchemaRecord


class CompatibilityViolation(Exception):
    pass


class CompatibilityResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def ok(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def __repr__(self) -> str:
        status = "OK" if self.ok() else f"ERRORS({len(self.errors)})"
        return f"<CompatibilityResult {status}>"


class CompatibilityChecker:
    """Check compatibility between two schema records according to a policy."""

    def __init__(self, policy_doc: CompatibilityPolicyDoc | None = None) -> None:
        self.policy_doc = policy_doc

    def check(
        self,
        old: SchemaRecord,
        new: SchemaRecord,
        old_schema: dict[str, Any] | None = None,
        new_schema: dict[str, Any] | None = None,
    ) -> CompatibilityResult:
        policy = new.compatibility_policy
        result = CompatibilityResult()

        if policy == CompatibilityPolicy.NONE:
            result.add_warning("Compatibility policy is NONE; any change is allowed.")
            return result

        if policy == CompatibilityPolicy.FULL:
            if old.key() != new.key():
                result.add_error("FULL policy requires exact version match.")
            return result

        # ADDITIVE_WITHIN_MAJOR (default)
        if old_schema is None or new_schema is None:
            raise ValueError("Schema content required for ADDITIVE_WITHIN_MAJOR comparison")

        self._check_additive_within_major(old_schema, new_schema, result)
        return result

    def _check_additive_within_major(
        self,
        old: dict[str, Any],
        new: dict[str, Any],
        result: CompatibilityResult,
        path: str = "",
    ) -> None:
        """Recursively enforce additive-within-major rules."""
        # Rule AWM-01: field removal
        old_props = old.get("properties", {})
        new_props = new.get("properties", {})
        for key in old_props:
            if key not in new_props:
                result.add_error(f"AWM-01: Field '{_join(path, key)}' was removed.")

        # Rule AWM-02: type change (for same field)
        for key in old_props:
            if key not in new_props:
                continue
            old_type = old_props[key].get("type")
            new_type = new_props[key].get("type")
            if old_type is not None and new_type is not None and old_type != new_type:
                result.add_error(
                    f"AWM-02: Field '{_join(path, key)}' changed type from {old_type} to {new_type}."
                )

        # Rule AWM-03: required field addition (narrowing)
        old_required = set(old.get("required", []))
        new_required = set(new.get("required", []))
        added_required = new_required - old_required
        if added_required:
            result.add_error(
                f"AWM-03: Fields {_fmt_set(added_required)} were added to required at '{path or 'root'}'."
            )

        # Rule AWM-04: additionalProperties false -> true is OK; true -> false is narrowing
        old_add = old.get("additionalProperties")
        new_add = new.get("additionalProperties")
        if old_add is True and new_add is False:
            result.add_error(
                f"AWM-04: additionalProperties tightened from true to false at '{path or 'root'}'."
            )

        # Rule AWM-05: enum shrinkage (unless x-open-enum is present)
        for key in old_props:
            if key not in new_props:
                continue
            old_enum = old_props[key].get("enum")
            new_enum = new_props[key].get("enum")
            if isinstance(old_enum, list) and isinstance(new_enum, list):
                if not set(new_enum).issuperset(set(old_enum)):
                    if not new_props[key].get("x-open-enum"):
                        result.add_error(
                            f"AWM-05: Enum for '{_join(path, key)}' shrunk from "
                            f"{_fmt_set(set(old_enum))} to {_fmt_set(set(new_enum))}."
                        )

        # Rule AWM-06: numeric constraint narrowing
        for key in old_props:
            if key not in new_props:
                continue
            old_field = old_props[key]
            new_field = new_props[key]
            for constraint in ("minimum", "minLength", "minItems"):
                old_c = old_field.get(constraint)
                new_c = new_field.get(constraint)
                if old_c is not None and new_c is not None and new_c > old_c:
                    result.add_error(
                        f"AWM-06: Constraint '{constraint}' narrowed for '{_join(path, key)}' "
                        f"from {old_c} to {new_c}."
                    )
            for constraint in ("maximum", "maxLength", "maxItems"):
                old_c = old_field.get(constraint)
                new_c = new_field.get(constraint)
                if old_c is not None and new_c is not None and new_c < old_c:
                    result.add_error(
                        f"AWM-06: Constraint '{constraint}' narrowed for '{_join(path, key)}' "
                        f"from {old_c} to {new_c}."
                    )

        # Rule AWM-07: default change affecting semantics
        for key in old_props:
            if key not in new_props:
                continue
            old_default = old_props[key].get("default")
            new_default = new_props[key].get("default")
            if old_default is not None and new_default is not None and old_default != new_default:
                # Changing default is additive in spirit if the schema itself doesn't narrow,
                # but it can break consumers that rely on the old default.
                result.add_warning(
                    f"AWM-07: Default changed for '{_join(path, key)}' from {old_default!r} to {new_default!r}. "
                    "Ensure downstream consumers are not relying on the old default."
                )

        # Rule AWM-08: description/semantic drift (best effort)
        for key in old_props:
            if key not in new_props:
                continue
            old_desc = old_props[key].get("description", "")
            new_desc = new_props[key].get("description", "")
            if old_desc and new_desc and old_desc != new_desc:
                # Heuristic: flag if description contradicts old meaning
                # In practice this needs human review; we warn.
                result.add_warning(
                    f"AWM-08: Description changed for '{_join(path, key)}'. Review for semantic drift."
                )

        # Recurse into nested objects
        for key in new_props:
            if key in old_props:
                old_sub = old_props[key]
                new_sub = new_props[key]
                if old_sub.get("type") == "object" and new_sub.get("type") == "object":
                    self._check_additive_within_major(old_sub, new_sub, result, _join(path, key))
                if old_sub.get("type") == "array" and new_sub.get("type") == "array":
                    old_items = old_sub.get("items", {})
                    new_items = new_sub.get("items", {})
                    if old_items.get("type") == "object" and new_items.get("type") == "object":
                        self._check_additive_within_major(
                            old_items, new_items, result, _join(path, key) + "[]"
                        )

        # Rule AWM-09: $id / title changes that could break external references
        old_id = old.get("$id")
        new_id = new.get("$id")
        if old_id and new_id and old_id != new_id:
            result.add_error(
                f"AWM-09: Schema $id changed from {old_id!r} to {new_id!r}. "
                "External $ref consumers may break."
            )


def _join(path: str, key: str) -> str:
    if path:
        return f"{path}.{key}"
    return key


def _fmt_set(s: set[str]) -> str:
    return ", ".join(sorted(s))


def check_status_transition(old: LifecycleStatus, new: LifecycleStatus, policy_doc: CompatibilityPolicyDoc) -> list[str]:
    """Return list of error strings if transition is invalid."""
    errors: list[str] = []
    for t in policy_doc.lifecycle_transitions:
        if t.from_status == old and t.to_status == new:
            if not t.allowed:
                errors.append(f"Transition {old.value} -> {new.value} is forbidden.")
            return errors
    errors.append(f"Transition {old.value} -> {new.value} is not defined in policy.")
    return errors

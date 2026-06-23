"""S1-A: State Enum Alignment Tests — Production Approval Suite, Pillar 1.

Ship/No-Ship Gate: These tests verify that the backend WorkflowStatus and
WorkflowType enums are exactly aligned with the frontend TypeScript type
definitions.  A mismatch means the UI will silently mishandle workflows in
an unknown state — this is a release-blocking defect.

Expected Initial State:
    - All alignment checks should PASS when frontend/backend remain synchronized.
    - Duplicate alias checks should PASS when WorkflowType values remain unique.

These tests parse source files directly (no runtime import of frontend code)
so they run without Node.js and catch drift even when the two stacks are
developed independently.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers — extract enum values from Python and TypeScript sources
# ---------------------------------------------------------------------------

def _python_enum_values(filepath: Path, class_name: str) -> set[str]:
    """Extract the string values of a ``str, Enum`` class from a Python file.

    Parses the AST so it works regardless of import side-effects.
    """
    source = filepath.read_text()
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            values: set[str] = set()
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and isinstance(item.value, ast.Constant):
                            values.add(str(item.value.value))
            return values

    raise ValueError(f"Class {class_name!r} not found in {filepath}")


def _typescript_union_values(filepath: Path, type_name: str) -> set[str]:
    """Extract literal values from a TypeScript union type.

    Handles patterns like:
        export type WorkflowStatus = 'pending' | 'running' | 'completed';
    """
    source = filepath.read_text()

    # Match: export type <TypeName> = 'val1' | 'val2' | ...;
    pattern = rf"export\s+type\s+{re.escape(type_name)}\s*=\s*([^;]+);"
    match = re.search(pattern, source)
    if not match:
        raise ValueError(f"Type {type_name!r} not found in {filepath}")

    raw = match.group(1)
    # Extract all single-quoted or double-quoted string literals
    return set(re.findall(r"['\"]([^'\"]+)['\"]", raw))


def _typescript_interface_union_field(filepath: Path, interface_name: str, field_name: str) -> set[str]:
    """Extract literal values from a union-typed field inside a TS interface.

    Handles patterns like:
        export interface WorkflowCreateRequest {
            workflow_type: 'roi_calculator' | 'whitespace_analysis' | ...;
        }
    """
    source = filepath.read_text()

    # Find the interface block
    iface_pattern = rf"export\s+interface\s+{re.escape(interface_name)}\s*\{{([^}}]+)\}}"
    iface_match = re.search(iface_pattern, source, re.DOTALL)
    if not iface_match:
        raise ValueError(f"Interface {interface_name!r} not found in {filepath}")

    body = iface_match.group(1)

    # Find the field line
    field_pattern = rf"{re.escape(field_name)}\??\s*:\s*([^;]+);"
    field_match = re.search(field_pattern, body)
    if not field_match:
        raise ValueError(f"Field {field_name!r} not found in {interface_name}")

    raw = field_match.group(1)
    return set(re.findall(r"['\"]([^'\"]+)['\"]", raw))


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

_BACKEND_AGENT_STATE = (
    _PROJECT_ROOT
    / "services"
    / "layer4-agents"
    / "src"
    / "layer4_agents"
    / "models"
    / "agent_state.py"
)

_FRONTEND_WORKFLOWS_TS = (
    _PROJECT_ROOT / "apps" / "web" / "src" / "api" / "workflows.ts"
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestWorkflowStatusAlignment:
    """Verify backend WorkflowStatus enum matches frontend TypeScript type."""

    @pytest.fixture(autouse=True)
    def _load_enums(self):
        self.backend_values = _python_enum_values(
            _BACKEND_AGENT_STATE, "WorkflowStatus"
        )
        self.frontend_values = _typescript_union_values(
            _FRONTEND_WORKFLOWS_TS, "WorkflowStatus"
        )

    def test_backend_workflow_status_superset_of_frontend(self):
        """Every backend status must exist in the frontend type.

        This test fails if backend introduces a new status not represented
        in the frontend union (for example ``interrupted``).
        """
        missing_in_frontend = self.backend_values - self.frontend_values
        assert not missing_in_frontend, (
            f"Backend WorkflowStatus values missing from frontend TypeScript type: "
            f"{missing_in_frontend}. "
            f"Backend values: {sorted(self.backend_values)}. "
            f"Frontend values: {sorted(self.frontend_values)}."
        )

    def test_frontend_workflow_status_subset_of_backend(self):
        """Every frontend status must exist in the backend enum.

        Catches orphan frontend values that the backend would never produce,
        which would create dead UI branches.
        """
        missing_in_backend = self.frontend_values - self.backend_values
        assert not missing_in_backend, (
            f"Frontend WorkflowStatus values not present in backend enum: "
            f"{missing_in_backend}. "
            f"Frontend values: {sorted(self.frontend_values)}. "
            f"Backend values: {sorted(self.backend_values)}."
        )

    def test_exact_bidirectional_match(self):
        """Frontend and backend must define exactly the same set of statuses.

        This is the combined gate — if this passes, both directions are aligned.
        """
        assert self.backend_values == self.frontend_values, (
            f"WorkflowStatus mismatch.\n"
            f"  Only in backend:  {sorted(self.backend_values - self.frontend_values)}\n"
            f"  Only in frontend: {sorted(self.frontend_values - self.backend_values)}"
        )


class TestWorkflowTypeAlignment:
    """Verify backend WorkflowType enum matches frontend workflow_type field."""

    @pytest.fixture(autouse=True)
    def _load_enums(self):
        self.backend_values = _python_enum_values(
            _BACKEND_AGENT_STATE, "WorkflowType"
        )
        self.frontend_values = _typescript_interface_union_field(
            _FRONTEND_WORKFLOWS_TS, "WorkflowCreateRequest", "workflow_type"
        )

    def test_frontend_workflow_types_exist_in_backend(self):
        """Every workflow type the frontend can create must be handled by the backend."""
        missing = self.frontend_values - self.backend_values
        assert not missing, (
            f"Frontend can create workflow types the backend doesn't recognize: "
            f"{missing}. "
            f"Frontend: {sorted(self.frontend_values)}. "
            f"Backend: {sorted(self.backend_values)}."
        )

    def test_backend_has_no_unreachable_workflow_types(self):
        """Backend workflow types should be reachable from the frontend.

        Note: some backend types may be internal-only (e.g. document_ingestion).
        This test flags them for review — they should be explicitly documented
        as internal if they are intentionally excluded from the frontend.
        """
        unreachable = self.backend_values - self.frontend_values
        # Allow known internal-only types
        KNOWN_INTERNAL_TYPES = {
            "document_ingestion",
            "financial_extraction",
            "value_tree_projection",
        }
        unexpected_unreachable = unreachable - KNOWN_INTERNAL_TYPES
        assert not unexpected_unreachable, (
            f"Backend WorkflowType values not reachable from frontend: "
            f"{unexpected_unreachable}. "
            f"If these are internal-only, add them to KNOWN_INTERNAL_TYPES."
        )


class TestNoDuplicateEnumAliases:
    """Verify that WorkflowType has no duplicate values (aliases).

    Enum aliases create ambiguous routing/branching behavior and are disallowed.
    """

    def test_workflow_type_values_are_unique(self):
        """Each WorkflowType member should map to a unique string value."""
        source = _BACKEND_AGENT_STATE.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "WorkflowType":
                seen_values: dict[str, str] = {}  # value -> first member name
                duplicates: list[str] = []

                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and isinstance(item.value, ast.Constant):
                                val = str(item.value.value)
                                if val in seen_values:
                                    duplicates.append(
                                        f"{target.id} = {val!r} (duplicate of {seen_values[val]})"
                                    )
                                else:
                                    seen_values[val] = target.id

                assert not duplicates, (
                    f"WorkflowType has duplicate values (aliases): {duplicates}. "
                    f"Each enum member should map to a unique string."
                )
                return

        pytest.fail("WorkflowType class not found in agent_state.py")

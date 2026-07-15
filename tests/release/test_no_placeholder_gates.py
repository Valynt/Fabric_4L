"""Release Policy: No placeholder gates in release-candidate profile.

Verifies that the release-candidate profile in .fabric/prod-gates.policy.yaml
does not contain any gates with class 'placeholder'. Placeholder gates indicate
incomplete production readiness and must be resolved before release.
"""

import os
import re
from pathlib import Path

import pytest
import yaml

POLICY_FILE = Path(__file__).parent.parent.parent / ".fabric" / "prod-gates.policy.yaml"


class TestNoPlaceholderGates:
    """Enforce: release-candidate profile must have no placeholder gates."""

    def test_policy_file_exists(self):
        """Policy file must exist to be parsed."""
        assert POLICY_FILE.exists(), f"Policy file not found: {POLICY_FILE}"
        assert POLICY_FILE.stat().st_size > 0, "Policy file is empty"

    def test_policy_file_is_valid_yaml(self):
        """Policy file must be valid YAML."""
        with open(POLICY_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), "Policy file must be a YAML mapping"
        assert "profiles" in data, "Policy file must have 'profiles' section"
        assert "gate-definitions" in data, "Policy file must have 'gate-definitions' section"

    def test_release_candidate_profile_exists(self):
        """release-candidate profile must exist in policy."""
        with open(POLICY_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "release-candidate" in data.get("profiles", {}), \
            "release-candidate profile must exist in policy"

    def test_no_placeholder_gates_in_release_candidate(self):
        """release-candidate profile must not include any placeholder gates.

        Rationale: Placeholder gates indicate known gaps in production readiness.
        A release-candidate with placeholder gates is not production-ready.
        """
        with open(POLICY_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        profiles = data.get("profiles", {})
        gate_definitions = data.get("gate-definitions", {})
        release_candidate = profiles.get("release-candidate", {})
        gates = release_candidate.get("gates", [])

        placeholder_gates = []
        for gate_name in gates:
            gate_def = gate_definitions.get(gate_name, {})
            if gate_def.get("class") == "placeholder":
                placeholder_gates.append({
                    "name": gate_name,
                    "description": gate_def.get("description", ""),
                    "caveat": gate_def.get("caveat", ""),
                })

        if placeholder_gates:
            details = "\n".join(
                f"  - {g['name']}: {g['description']} (caveat: {g['caveat']})"
                for g in placeholder_gates
            )
            pytest.fail(
                f"release-candidate profile contains {len(placeholder_gates)} placeholder gate(s):\n{details}\n"
                f"All placeholder gates must be graduated (implemented and passing) before release."
            )

    def test_placeholder_gates_have_caveats(self):
        """Any placeholder gates in policy must have a caveat explaining why.

        Rationale: Placeholder status must be intentional and documented.
        """
        with open(POLICY_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        gate_definitions = data.get("gate-definitions", {})
        placeholders_without_caveats = []

        for gate_name, gate_def in gate_definitions.items():
            if gate_def.get("class") == "placeholder":
                caveat = gate_def.get("caveat", "")
                if not caveat or caveat.strip() == "":
                    placeholders_without_caveats.append(gate_name)

        # This is an informational assertion — placeholders should have caveats
        # but we won't fail the build for missing caveats on non-release profiles
        assert len(placeholders_without_caveats) == 0, \
            f"Placeholder gates without documented caveats: {placeholders_without_caveats}"

    def test_placeholder_gates_documented_in_gate_definitions(self):
        """All gates in release-candidate must have definitions in gate-definitions."""
        with open(POLICY_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        profiles = data.get("profiles", {})
        gate_definitions = data.get("gate-definitions", {})
        release_candidate = profiles.get("release-candidate", {})
        gates = release_candidate.get("gates", [])

        undefined_gates = [g for g in gates if g not in gate_definitions]
        assert len(undefined_gates) == 0, \
            f"release-candidate references undefined gates: {undefined_gates}"

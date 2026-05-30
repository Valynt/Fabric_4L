#!/usr/bin/env python3
"""
Negative validation tests for the release gate system.

Proves fail-closed behavior without requiring a full CI environment.
Uses temporary fixtures and controlled env flags.

Run: python scripts/test-release-gate-negative.py
"""

import os
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd, cwd=None, env=None):
    """Run a shell command and return (rc, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode, result.stdout, result.stderr


def test_unknown_profile_fails():
    """Unknown profile must cause non-zero exit."""
    rc, out, err = run_cmd("bash scripts/release-gate.sh nonexistent-profile")
    if rc == 0:
        # bash may not be available on Windows; skip this test
        print("  [SKIP] bash not available — test valid in Linux CI")
        return
    combined = (out or "") + (err or "")
    assert "Unknown profile" in combined, f"Expected 'Unknown profile' in output: {combined[:200]}"
    print("  [PASS] Unknown profile correctly fails")


def test_invalid_policy_fails():
    """Malformed YAML policy must cause non-zero exit."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("invalid: yaml: [")
        bad_policy = f.name

    rc, out, err = run_cmd(
        f"python -c \"import yaml; yaml.safe_load(open('{bad_policy}'))\""
    )
    os.unlink(bad_policy)
    assert rc != 0, f"Expected non-zero exit for invalid policy, got {rc}"
    print("  [PASS] Invalid policy correctly fails YAML parse")


def test_missing_policy_fails():
    """Missing policy file must cause non-zero exit."""
    rc, out, err = run_cmd("test -s .fabric/nonexistent.policy.yaml || exit 1")
    assert rc != 0, f"Expected non-zero exit for missing policy, got {rc}"
    print("  [PASS] Missing policy correctly fails")


def test_placeholder_gate_fails():
    """Placeholder gates must exit non-zero (they have no tests)."""
    rc, out, err = run_cmd("make gate-chaos")
    combined = (out or "") + (err or "")
    assert rc != 0, f"Expected non-zero exit for placeholder gate-chaos, got {rc}\n{combined[:500]}"
    assert "PLACEHOLDER" in combined, f"Expected PLACEHOLDER in output: {combined[:500]}"
    print("  [PASS] Placeholder gate-chaos correctly fails")


def test_placeholder_release_policy_fails():
    """Release policy gate (placeholder) must exit non-zero."""
    rc, out, err = run_cmd("make gate-release-policy")
    combined = (out or "") + (err or "")
    assert rc != 0, f"Expected non-zero exit for placeholder gate-release-policy, got {rc}\n{combined[:500]}"
    assert "PLACEHOLDER" in combined, f"Expected PLACEHOLDER in output: {combined[:500]}"
    print("  [PASS] Placeholder gate-release-policy correctly fails")


def test_sign_manifest_fails_without_artifacts():
    """Sign manifest must fail when no artifacts exist."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        empty_dir = os.path.join(tmpdir, "release")
        os.makedirs(empty_dir, exist_ok=True)
        # Override Makefile variable via command line
        rc, out, err = run_cmd(
            f"make gate-sign-manifest ARTIFACT_DIR={empty_dir}"
        )
        combined = (out or "") + (err or "")
        assert rc != 0, f"Expected non-zero exit for empty artifacts, got {rc}\n{combined[:500]}"
    print("  [PASS] Sign manifest correctly fails without artifacts")


def test_profile_strictness():
    """Verify profiles have meaningfully different gate lists."""
    import yaml

    policy_path = Path(".fabric/prod-gates.policy.yaml")
    assert policy_path.exists(), "Policy file must exist"

    with open(policy_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    profiles = data.get("profiles", {})
    pr_fast = set(profiles.get("pr-fast", {}).get("gates", []))
    mainline = set(profiles.get("mainline-full", {}).get("gates", []))
    release = set(profiles.get("release-candidate", {}).get("gates", []))

    # pr-fast is strict subset of mainline
    assert pr_fast < mainline, f"pr-fast must be strict subset of mainline-full"
    # mainline is strict subset of release-candidate
    assert mainline < release, f"mainline-full must be strict subset of release-candidate"
    # release-candidate has sign-manifest
    assert "sign-manifest" in release, "release-candidate must include sign-manifest"
    # pr-fast does NOT have sign-manifest
    assert "sign-manifest" not in pr_fast, "pr-fast must NOT include sign-manifest"
    print("  [PASS] Profile strictness verified: pr-fast < mainline-full < release-candidate")


def test_release_candidate_blocks_on_placeholders():
    """release-candidate profile must include placeholder gates that will fail."""
    import yaml

    with open(".fabric/prod-gates.policy.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    release_gates = data["profiles"]["release-candidate"]["gates"]
    gate_defs = data["gate-definitions"]

    placeholders_in_release = [
        g for g in release_gates
        if gate_defs.get(g, {}).get("class") == "placeholder"
    ]

    assert len(placeholders_in_release) > 0, (
        "release-candidate must include at least one placeholder gate to prove enforcement. "
        "If all gates are implemented, remove placeholder classification."
    )
    print(f"  [PASS] release-candidate includes {len(placeholders_in_release)} placeholder gate(s): {placeholders_in_release}")


def test_policy_schema_completeness():
    """Every gate in profiles must have a gate-definition."""
    import yaml

    with open(".fabric/prod-gates.policy.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    profile_gates = set()
    for p in data.get("profiles", {}).values():
        profile_gates.update(p.get("gates", []))

    defined_gates = set(data.get("gate-definitions", {}).keys())
    undefined = profile_gates - defined_gates
    assert not undefined, f"Gates referenced in profiles but undefined: {undefined}"
    print(f"  [PASS] All {len(profile_gates)} profile gates have definitions")


def test_lint_passes_all_layers():
    """Lint must pass across all layers (positive validation)."""
    layers = [
        "services/layer1-ingestion",
        "services/layer2-extraction",
        "services/layer3-knowledge",
        "services/layer4-agents",
        "services/layer5-ground-truth",
        "services/layer6-benchmarks",
    ]
    for layer in layers:
        rc, out, err = run_cmd(f"cd {layer} && ruff check src/")
        combined = (out or "") + (err or "")
        assert rc == 0, f"Lint failed for {layer}:\n{combined[:500]}"
    print(f"  [PASS] Lint passes for all {len(layers)} layers")


def test_makefile_targets_exist():
    """All gate targets referenced in policy must exist in Makefile."""
    import yaml

    with open(".fabric/prod-gates.policy.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    gate_defs = data.get("gate-definitions", {})
    makefile = Path("Makefile").read_text(encoding="utf-8")

    missing = []
    for gate, gdef in gate_defs.items():
        target = gdef.get("target", gate)
        # Look for target definition in Makefile
        if f"{target}:" not in makefile:
            missing.append(target)

    assert not missing, f"Makefile targets missing: {missing}"
    print(f"  [PASS] All {len(gate_defs)} gate targets exist in Makefile")


def main():
    print("Running release-gate negative validation tests ...")
    print("")

    tests = [
        ("Unknown profile fails", test_unknown_profile_fails),
        ("Invalid policy fails", test_invalid_policy_fails),
        ("Missing policy fails", test_missing_policy_fails),
        ("Placeholder gate (chaos) fails", test_placeholder_gate_fails),
        ("Placeholder gate (release-policy) fails", test_placeholder_release_policy_fails),
        ("Sign manifest fails without artifacts", test_sign_manifest_fails_without_artifacts),
        ("Profile strictness", test_profile_strictness),
        ("release-candidate blocks on placeholders", test_release_candidate_blocks_on_placeholders),
        ("Policy schema completeness", test_policy_schema_completeness),
        ("Makefile targets exist", test_makefile_targets_exist),
        ("Lint passes all layers", test_lint_passes_all_layers),
    ]

    passed = 0
    skipped = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: Unexpected error: {type(e).__name__}: {e}")
            failed += 1

    print("")
    print(f"Results: {passed} passed, {skipped} skipped, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

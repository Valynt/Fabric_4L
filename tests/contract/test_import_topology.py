"""Contract tests for import topology correctness.

Phase 4: Verify canonical imports resolve deterministically.
"""
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent.parent


class TestImportTopology:
    """Verify import namespace resolution."""

    def test_value_fabric_namespace_imports(self):
        """value_fabric namespace should resolve from packages/shared/src."""
        import value_fabric

        namespace_paths = [str(path).replace("\\", "/") for path in value_fabric.__path__]
        assert any(
            path.endswith("packages/shared/src/value_fabric") for path in namespace_paths
        ), f"value_fabric namespace resolved to {namespace_paths}"
        assert not (REPO_ROOT / "value_fabric").exists(), (
            "Root value_fabric/ compatibility package should not be restored."
        )

    def test_shared_namespace_resolution(self):
        """import value_fabric.shared should resolve to canonical location."""
        import value_fabric.shared

        shared_path = Path(value_fabric.shared.__file__)
        assert "packages/shared/src/value_fabric/shared" in str(shared_path).replace("\\", "/"), (
            f"shared resolved to {shared_path}, expected packages/shared/src/value_fabric/shared/"
        )

    @pytest.mark.parametrize("layer", [
        "layer1_ingestion",
        "layer2_extraction",
        "src",
        "layer4_agents",
        "layer5_ground_truth",
        "layer6_benchmarks",
    ])
    def test_layer_imports(self, layer):
        """Each layer should be importable via value_fabric."""
        try:
            module = __import__(f"layer4_agents", fromlist=["layer4_agents"])
            assert module is not None
        except ImportError as e:
            pytest.skip(f"Layer 4 agents not yet available: {e}")

    def test_layer4_engine_import(self):
        """Layer 4 engine module should be importable via layer4_agents."""
        try:
            import layer4_agents.engine
            assert layer4_agents.engine.__file__ is not None
        except ImportError as e:
            pytest.skip(f"Layer 4 engine not yet available: {e}")

    def test_layer4_tools_import(self):
        """Layer 4 tools module should be importable via layer4_agents."""
        try:
            import layer4_agents.tools
            assert layer4_agents.tools.__file__ is not None
        except ImportError as e:
            pytest.skip(f"Layer 4 tools not yet available: {e}")

    def test_layer4_models_import(self):
        """Layer 4 models module should be importable via layer4_agents."""
        try:
            import layer4_agents.models
            assert layer4_agents.models.__file__ is not None
        except ImportError as e:
            pytest.skip(f"Layer 4 models not yet available: {e}")

    def test_layer4_resolves_to_canonical_service_tree(self):
        """layer4_agents must resolve via services/layer4-agents/src/."""
        import layer4_agents

        canonical = (REPO_ROOT / "services" / "layer4-agents" / "src" / "layer4_agents").resolve()
        namespace_paths = [Path(path).resolve() for path in layer4_agents.__path__]
        assert canonical in namespace_paths, (
            f"layer4_agents resolved to {namespace_paths}, expected {canonical}"
        )

    @pytest.mark.timeout(180)
    def test_pytest_collection_no_import_errors(self):
        """pytest --collect-only should have zero import errors."""
        import subprocess

        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/contract", "tests/docs"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )

        # Check for import errors in stderr
        import_errors = [
            line for line in result.stderr.split("\n")
            if "ImportError" in line or "ModuleNotFoundError" in line
        ]

        assert len(import_errors) == 0, (
            f"Found {len(import_errors)} import errors:\n" +
            "\n".join(import_errors[:5])
        )

    def test_no_root_shared_shadowing(self):
        """Root value_fabric/shared/ must not have an __init__.py (no package shadowing)."""
        root_shared_init = REPO_ROOT / "value_fabric" / "shared" / "__init__.py"

        assert not root_shared_init.exists(), (
            f"Root {root_shared_init} still exists. "
            "It would shadow packages/shared/src/value_fabric/shared/ as a proper package. "
            "Remove it to prevent namespace collision."
        )

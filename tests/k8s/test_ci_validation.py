"""Tests for CI validation pipeline (kubeconform, conftest, kubectl dry-run).

Validates:
- K8s schema validation with kubeconform
- Policy validation with conftest/OPA
- Client-side and server-side dry-run
- Preflight check script functionality
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml


class TestKubeconformValidation:
    """Tests for kubeconform schema validation."""

    def test_dev_manifest_schema_valid(
        self, repo_root: Path, kustomize_build_dev: str, skip_without_kubeconform
    ) -> None:
        """[1c] Dev manifest passes kubeconform schema validation."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(kustomize_build_dev)
            f.flush()
            
            result = subprocess.run(
                ["kubeconform", "-strict", "-summary", f.name],
                capture_output=True,
                text=True,
            )
        
        assert result.returncode == 0, f"Dev manifest schema validation failed: {result.stderr}"

    def test_prod_manifest_schema_valid(
        self, repo_root: Path, kustomize_build_prod: str, skip_without_kubeconform
    ) -> None:
        """[1c] Prod manifest passes kubeconform schema validation."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(kustomize_build_prod)
            f.flush()
            
            result = subprocess.run(
                ["kubeconform", "-strict", "-summary", f.name],
                capture_output=True,
                text=True,
            )
        
        assert result.returncode == 0, f"Prod manifest schema validation failed: {result.stderr}"


class TestConftestPolicyValidation:
    """Tests for conftest/OPA policy validation."""

    def test_dev_passes_security_policies(
        self, repo_root: Path, kustomize_build_dev: str, skip_without_conftest
    ) -> None:
        """[1c] Dev manifest passes conftest security policy validation."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(kustomize_build_dev)
            f.flush()
            
            result = subprocess.run(
                ["conftest", "test", f.name, "-p", str(repo_root / "k8s" / "policy")],
                capture_output=True,
                text=True,
            )
        
        assert result.returncode == 0, f"Dev policy validation failed: {result.stdout}{result.stderr}"

    def test_prod_passes_security_policies(
        self, repo_root: Path, kustomize_build_prod: str, skip_without_conftest
    ) -> None:
        """[1c] Prod manifest passes conftest security policy validation."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(kustomize_build_prod)
            f.flush()
            
            result = subprocess.run(
                ["conftest", "test", f.name, "-p", str(repo_root / "k8s" / "policy")],
                capture_output=True,
                text=True,
            )
        
        assert result.returncode == 0, f"Prod policy validation failed: {result.stdout}{result.stderr}"

    def test_prod_no_raw_secrets(
        self, repo_root: Path, kustomize_build_prod: str, skip_without_conftest
    ) -> None:
        """Prod manifest must not contain raw Secret resources."""
        docs = list(yaml.safe_load_all(kustomize_build_prod))
        
        secrets = [d for d in docs if d and d.get("kind") == "Secret"]
        assert len(secrets) == 0, f"Found {len(secrets)} raw Secret resources in prod - use ExternalSecret only"

    def test_prod_has_external_secrets(
        self, repo_root: Path, kustomize_build_prod: str, skip_without_conftest
    ) -> None:
        """Prod manifest must include ExternalSecret resources."""
        docs = list(yaml.safe_load_all(kustomize_build_prod))
        
        external_secrets = [d for d in docs if d and d.get("kind") == "ExternalSecret"]
        assert len(external_secrets) > 0, "Prod must include ExternalSecret resources"


class TestKubectlDryRun:
    """Tests for kubectl dry-run validation."""

    def test_dev_client_dry_run(
        self, repo_root: Path, kustomize_build_dev: str, skip_without_kubectl
    ) -> None:
        """[1e] Dev manifest passes kubectl client-side dry-run."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(kustomize_build_dev)
            f.flush()
            
            result = subprocess.run(
                ["kubectl", "apply", "--dry-run=client", "-f", f.name],
                capture_output=True,
                text=True,
            )
        
        assert result.returncode == 0, f"Dev client dry-run failed: {result.stderr}"

    def test_prod_client_dry_run(
        self, repo_root: Path, kustomize_build_prod: str, skip_without_kubectl
    ) -> None:
        """[1e] Prod manifest passes kubectl client-side dry-run."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(kustomize_build_prod)
            f.flush()
            
            result = subprocess.run(
                ["kubectl", "apply", "--dry-run=client", "-f", f.name],
                capture_output=True,
                text=True,
            )
        
        assert result.returncode == 0, f"Prod client dry-run failed: {result.stderr}"


class TestPreflightChecks:
    """Tests for the preflight validation script."""

    def test_preflight_script_exists(self, repo_root: Path) -> None:
        """Verify k8s_preflight.py script exists and is executable."""
        script = repo_root / "scripts" / "ci" / "k8s_preflight.py"
        assert script.exists(), "Preflight script must exist"

    def test_preflight_script_valid_python(self, repo_root: Path) -> None:
        """Verify k8s_preflight.py is valid Python syntax."""
        script = repo_root / "scripts" / "ci" / "k8s_preflight.py"
        
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script)],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0, f"Preflight script has syntax errors: {result.stderr}"

    def test_preflight_passes(self, repo_root: Path) -> None:
        """Verify k8s_preflight.py passes against current k8s/base workloads."""
        script = repo_root / "scripts" / "ci" / "k8s_preflight.py"
        
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        
        assert result.returncode == 0, f"Preflight checks failed: {result.stdout}{result.stderr}"

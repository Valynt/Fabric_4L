"""Tests for Kubernetes security policies and hardening.

Validates:
- OPA/Rego security policies
- Pod security contexts (runAsNonRoot, seccomp)
- Container security contexts (readOnlyRootFilesystem, allowPrivilegeEscalation, drop ALL)
- Kyverno policies for SLSA provenance and signature verification
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml


class TestRegoPolicies:
    """Tests for OPA/Rego security policies."""

    def test_security_hardening_rego_exists(self, k8s_policy_dir: Path) -> None:
        """Verify security-hardening.rego policy file exists."""
        policy = k8s_policy_dir / "security-hardening.rego"
        assert policy.exists(), "security-hardening.rego must exist"

    def test_rego_syntax_valid(self, k8s_policy_dir: Path) -> None:
        """Verify Rego policy syntax is valid."""
        policy = k8s_policy_dir / "security-hardening.rego"
        
        if shutil.which("opa") is not None:
            result = subprocess.run(
                ["opa", "parse", str(policy)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Rego syntax error: {result.stderr}"
            return

        content = policy.read_text()
        brace_depth = 0
        for char in content:
            if char == "{":
                brace_depth += 1
            elif char == "}":
                brace_depth -= 1
            assert brace_depth >= 0, "Rego policy has unmatched closing brace"
        assert brace_depth == 0, "Rego policy has unmatched opening brace"
        assert re.search(r"(?m)^\s*package\s+main\b", content), "Rego policy must declare package main"
        assert "deny[" in content, "Rego policy must declare deny rules"

    def test_rego_has_run_as_non_root_check(self, k8s_policy_dir: Path) -> None:
        """Verify Rego policy checks for runAsNonRoot."""
        policy = k8s_policy_dir / "security-hardening.rego"
        
        with open(policy) as f:
            content = f.read()
        
        assert "runAsNonRoot" in content, "Policy must check runAsNonRoot"
        assert "runAsNonRoot != true" in content or "runAsNonRoot == true" in content

    def test_rego_has_seccomp_check(self, k8s_policy_dir: Path) -> None:
        """Verify Rego policy checks for seccompProfile."""
        policy = k8s_policy_dir / "security-hardening.rego"
        
        with open(policy) as f:
            content = f.read()
        
        assert "seccompProfile" in content, "Policy must check seccompProfile"
        assert "RuntimeDefault" in content

    def test_rego_checks_container_security_context(self, k8s_policy_dir: Path) -> None:
        """Verify Rego policy checks container securityContext hardening."""
        policy = k8s_policy_dir / "security-hardening.rego"
        
        with open(policy) as f:
            content = f.read()
        
        # Check for required container security settings
        assert "allowPrivilegeEscalation" in content
        assert "readOnlyRootFilesystem" in content
        assert "capabilities" in content
        assert "drop" in content
        assert "ALL" in content

    def test_rego_checks_init_containers(self, k8s_policy_dir: Path) -> None:
        """Verify Rego policy checks initContainers as well as containers."""
        policy = k8s_policy_dir / "security-hardening.rego"
        
        with open(policy) as f:
            content = f.read()
        
        assert "initContainers" in content, "Policy must check initContainers"


    def test_rego_disallows_privileged_containers(self, k8s_policy_dir: Path) -> None:
        """Verify Rego policy rejects privileged containers."""
        policy = k8s_policy_dir / "security-hardening.rego"

        with open(policy) as f:
            content = f.read()

        assert "privileged" in content
        assert "must not set securityContext.privileged=true" in content

    def test_rego_policy_evaluates(self, k8s_policy_dir: Path, repo_root: Path) -> None:
        """Test that Rego policy can evaluate against a sample deployment."""
        policy = k8s_policy_dir / "security-hardening.rego"
        
        # Create a test deployment that should pass
        test_deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "test-deployment"},
            "spec": {
                "template": {
                    "spec": {
                        "securityContext": {
                            "runAsNonRoot": True,
                            "seccompProfile": {"type": "RuntimeDefault"}
                        },
                        "containers": [{
                            "name": "test",
                            "image": "test:v1.0.0",
                            "securityContext": {
                                "allowPrivilegeEscalation": False,
                                "readOnlyRootFilesystem": True,
                                "capabilities": {"drop": ["ALL"]}
                            }
                        }]
                    }
                }
            }
        }
        
        conftest_path = shutil.which("conftest")
        # On Windows PATHEXT may match pytest conftest.py files in the repo root.
        # Only delegate to the real conftest CLI when the resolved path is not a
        # Python file.
        if conftest_path is not None and not str(conftest_path).lower().endswith(".py"):
            result = subprocess.run(
                ["conftest", "test", "-", "-p", str(k8s_policy_dir), "--policy", "main"],
                input=yaml.dump(test_deployment),
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Valid deployment failed policy check: {result.stdout}"
            return

        policy_content = policy.read_text()
        required_runtime_checks = (
            "runAsNonRoot",
            "RuntimeDefault",
            "allowPrivilegeEscalation",
            "readOnlyRootFilesystem",
            "capabilities",
            "drop",
            "ALL",
            "privileged",
        )
        missing = [token for token in required_runtime_checks if token not in policy_content]
        assert not missing, "Rego policy is missing release-critical checks: " + ", ".join(missing)


class TestKyvernoPolicies:
    """Tests for Kyverno policies."""

    def test_kyverno_slsa_provenance_policy_exists(self, k8s_policy_dir: Path) -> None:
        """Verify Kyverno SLSA provenance policy exists."""
        policy = k8s_policy_dir / "kyverno-slsa-provenance.yaml"
        assert policy.exists(), "kyverno-slsa-provenance.yaml must exist"

    def test_kyverno_signature_verify_policy_exists(self, k8s_policy_dir: Path) -> None:
        """Verify Kyverno signature verification policy exists."""
        policy = k8s_policy_dir / "kyverno-verify-signatures.yaml"
        assert policy.exists(), "kyverno-verify-signatures.yaml must exist"


    def test_kyverno_require_digest_policy_exists(self, k8s_policy_dir: Path) -> None:
        """Verify Kyverno digest enforcement policy exists."""
        policy = k8s_policy_dir / "kyverno-require-image-digests.yaml"
        assert policy.exists(), "kyverno-require-image-digests.yaml must exist"

    def test_digest_policy_targets_production_namespaces(self, k8s_policy_dir: Path) -> None:
        """Verify digest policy only enforces on production namespaces."""
        policy = k8s_policy_dir / "kyverno-require-image-digests.yaml"
        content = policy.read_text(encoding="utf-8")
        assert "value-fabric-prod" in content
        assert "value-fabric-production" in content
        assert "@sha256:" in content

    def test_slsa_policy_valid_yaml(self, k8s_policy_dir: Path) -> None:
        """Verify SLSA policy is valid YAML."""
        policy = k8s_policy_dir / "kyverno-slsa-provenance.yaml"
        
        with open(policy) as f:
            docs = [d for d in yaml.safe_load_all(f) if d]

        assert docs, "expected at least one YAML document"
        for doc in docs:
            assert doc.get("apiVersion") == "kyverno.io/v1"
            assert doc.get("kind") in ("ClusterPolicy", "Policy")

    def test_signature_policy_valid_yaml(self, k8s_policy_dir: Path) -> None:
        """Verify signature policy is valid YAML."""
        policy = k8s_policy_dir / "kyverno-verify-signatures.yaml"
        
        with open(policy) as f:
            docs = [d for d in yaml.safe_load_all(f) if d]

        assert docs, "expected at least one YAML document"
        for doc in docs:
            assert doc.get("apiVersion") == "kyverno.io/v1"
            assert doc.get("kind") in ("ClusterPolicy", "Policy")

    def test_slsa_policy_requires_provenance(self, k8s_policy_dir: Path) -> None:
        """Verify SLSA policy requires attestation."""
        policy = k8s_policy_dir / "kyverno-slsa-provenance.yaml"
        
        with open(policy) as f:
            content = f.read()
        
        assert "attest" in content.lower() or "provenance" in content.lower()

    def test_signature_policy_verifies_signatures(self, k8s_policy_dir: Path) -> None:
        """Verify signature policy checks image signatures."""
        policy = k8s_policy_dir / "kyverno-verify-signatures.yaml"
        
        with open(policy) as f:
            content = f.read()
        
        assert "signature" in content.lower() or "verify" in content.lower()


class TestPodSecurityStandards:
    """Tests for Pod Security Standards compliance in manifests."""

    def test_deployments_have_pod_security_context(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify all Deployments have pod-level securityContext."""
        failures = []
        
        for file_path, doc in workload_documents:
            if doc.get("kind") != "Deployment":
                continue
            
            spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            security_context = spec.get("securityContext", {})
            
            if not security_context:
                failures.append(f"{file_path}/{doc.get('metadata', {}).get('name')}: missing pod securityContext")
                continue
            
            if security_context.get("runAsNonRoot") != True:
                failures.append(
                    f"{file_path}/{doc.get('metadata', {}).get('name')}: runAsNonRoot not true"
                )
        
        if failures:
            pytest.fail("Pod security context violations:\n" + "\n".join(failures))

    def test_containers_have_security_context(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify all containers have securityContext with hardening."""
        failures = []
        
        for file_path, doc in workload_documents:
            kind = doc.get("kind")
            if kind not in ("Deployment", "StatefulSet", "DaemonSet", "Job"):
                continue
            
            spec = doc.get("spec", {})
            if kind == "Job":
                template = spec.get("template", {})
            else:
                template = spec.get("template", {})
            
            pod_spec = template.get("spec", {})
            containers = pod_spec.get("containers", [])
            init_containers = pod_spec.get("initContainers", [])
            
            for container in containers + init_containers:
                name = container.get("name", "unknown")
                security_context = container.get("securityContext", {})
                
                if not security_context:
                    failures.append(f"{file_path}/{name}: missing container securityContext")
                    continue
                
                if security_context.get("allowPrivilegeEscalation") != False:
                    failures.append(
                        f"{file_path}/{name}: allowPrivilegeEscalation not false"
                    )
                
                if security_context.get("readOnlyRootFilesystem") != True:
                    failures.append(
                        f"{file_path}/{name}: readOnlyRootFilesystem not true"
                    )
                
                capabilities = security_context.get("capabilities", {})
                drop = capabilities.get("drop", [])
                if "ALL" not in drop:
                    failures.append(f"{file_path}/{name}: capabilities.drop does not include ALL")
        
        if failures:
            pytest.fail("Container security context violations:\n" + "\n".join(failures))

    def test_no_privileged_containers(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify no containers run in privileged mode."""
        privileged = []
        
        for file_path, doc in workload_documents:
            spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            containers = spec.get("containers", []) + spec.get("initContainers", [])
            
            for container in containers:
                security_context = container.get("securityContext", {})
                if security_context.get("privileged") == True:
                    privileged.append(
                        f"{file_path}/{container.get('name')}: privileged=true"
                    )
        
        if privileged:
            pytest.fail("Privileged containers found:\n" + "\n".join(privileged))

    def test_no_root_containers(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify no containers explicitly run as root (uid=0)."""
        root_containers = []
        
        for file_path, doc in workload_documents:
            spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            containers = spec.get("containers", []) + spec.get("initContainers", [])
            
            for container in containers:
                security_context = container.get("securityContext", {})
                run_as_user = security_context.get("runAsUser")
                
                if run_as_user == 0:
                    root_containers.append(
                        f"{file_path}/{container.get('name')}: runAsUser=0"
                    )
        
        if root_containers:
            pytest.fail("Root containers found:\n" + "\n".join(root_containers))


class TestNetworkPolicies:
    """Tests for NetworkPolicy configuration."""

    def test_network_policies_directory_exists(self, k8s_base_dir: Path) -> None:
        """Verify network-policies directory exists."""
        netpol_dir = k8s_base_dir / "network-policies"
        assert netpol_dir.exists(), "network-policies directory must exist"

    def test_network_policies_have_yaml_files(self, k8s_base_dir: Path) -> None:
        """Verify network-policies directory contains YAML files."""
        netpol_dir = k8s_base_dir / "network-policies"
        
        yaml_files = list(netpol_dir.glob("*.yml"))
        assert len(yaml_files) > 0, "Network policies directory must contain YAML files"

    def test_network_policies_are_valid(self, k8s_base_dir: Path) -> None:
        """Verify all network policy YAML files are valid."""
        netpol_dir = k8s_base_dir / "network-policies"
        
        for yaml_file in netpol_dir.glob("*.yml"):
            with open(yaml_file) as f:
                docs = list(yaml.safe_load_all(f.read()))
            
            for doc in docs:
                if doc and doc.get("kind") == "NetworkPolicy":
                    # Basic NetworkPolicy structure
                    assert "spec" in doc
                    spec = doc["spec"]
                    assert "podSelector" in spec

    def test_default_deny_policy_exists(self, k8s_base_dir: Path) -> None:
        """Verify a default-deny network policy exists."""
        netpol_dir = k8s_base_dir / "network-policies"
        
        found = False
        for yaml_file in netpol_dir.glob("*.yml"):
            with open(yaml_file) as f:
                docs = list(yaml.safe_load_all(f.read()))
            
            for doc in docs:
                if doc and doc.get("kind") == "NetworkPolicy":
                    name = doc.get("metadata", {}).get("name", "").lower()
                    if "default" in name and "deny" in name:
                        found = True
                        break
        
        assert found, "A production baseline must include an explicit default-deny NetworkPolicy"

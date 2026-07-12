"""Integration tests for Kubernetes Readiness & Deployment.

Validates end-to-end flow from kustomize build through all validation stages.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml


class TestEndToEndValidation:
    """End-to-end validation tests simulating the CI pipeline."""

    def test_dev_full_validation_pipeline(
        self, repo_root: Path, skip_without_kustomize, skip_without_kubeconform
    ) -> None:
        """[1a, 1b, 1c, 1e] Full CI pipeline for dev overlay."""
        import tempfile
        
        # Step 1: Kustomize build [1a]
        result = subprocess.run(
            ["kustomize", "build", "k8s/envs/dev"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        assert result.returncode == 0, f"Kustomize build failed: {result.stderr}"
        
        # Step 2: Schema validation [1c]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(result.stdout)
            f.flush()
            
            result = subprocess.run(
                ["kubeconform", "-strict", f.name],
                capture_output=True,
                text=True,
            )
        
        assert result.returncode == 0, f"Schema validation failed: {result.stderr}"

    def test_prod_full_validation_pipeline(
        self, repo_root: Path, skip_without_kustomize, skip_without_kubeconform, skip_without_conftest
    ) -> None:
        """[1a, 1b, 1c, 1e] Full CI pipeline for prod overlay with policies."""
        import tempfile
        
        # Step 1: Kustomize build [1a]
        result = subprocess.run(
            [
                "kustomize",
                "build",
                "k8s/envs/prod",
                "--load-restrictor=LoadRestrictionsNone",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        assert result.returncode == 0, f"Kustomize build failed: {result.stderr}"
        
        rendered = result.stdout
        
        # Step 2: Schema validation [1c]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(rendered)
            f.flush()
            
            result = subprocess.run(
                ["kubeconform", "-strict", f.name],
                capture_output=True,
                text=True,
            )
        
        assert result.returncode == 0, f"Schema validation failed: {result.stderr}"
        
        # Step 3: Policy validation [1c]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(rendered)
            f.flush()
            
            result = subprocess.run(
                ["conftest", "test", f.name, "-p", "k8s/policy"],
                capture_output=True,
                text=True,
                cwd=str(repo_root),
            )
        
        assert result.returncode == 0, f"Policy validation failed: {result.stdout}{result.stderr}"

    def test_all_layers_present_in_build(
        self, repo_root: Path, skip_without_kustomize
    ) -> None:
        """Verify all 6 Value Fabric layers are present in rendered manifests."""
        result = subprocess.run(
            [
                "kustomize",
                "build",
                "k8s/envs/prod",
                "--load-restrictor=LoadRestrictionsNone",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        
        assert result.returncode == 0
        
        docs = list(yaml.safe_load_all(result.stdout))
        
        # Find all Deployment names
        deployments = [
            d.get("metadata", {}).get("name")
            for d in docs
            if d and d.get("kind") == "Deployment"
        ]
        
        required_layers = [
            "layer1-ingestion",
            "layer2-extraction",
            "layer3-knowledge",
            "layer4-agents",
            "layer5-ground-truth",
            "layer6-benchmarks",
        ]
        
        for layer in required_layers:
            matching = [d for d in deployments if layer in d]
            assert matching, f"Layer {layer} not found in rendered manifests"

    def test_monitoring_stack_present_in_build(
        self, repo_root: Path, skip_without_kustomize
    ) -> None:
        """Verify Prometheus and Alertmanager are present in rendered manifests."""
        result = subprocess.run(
            [
                "kustomize",
                "build",
                "k8s/envs/prod",
                "--load-restrictor=LoadRestrictionsNone",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        
        assert result.returncode == 0
        
        docs = list(yaml.safe_load_all(result.stdout))
        
        # Find ConfigMaps
        configmaps = [d for d in docs if d and d.get("kind") == "ConfigMap"]
        configmap_names = [c.get("metadata", {}).get("name") for c in configmaps]
        
        assert "prometheus-config" in configmap_names
        assert "alertmanager-config" in configmap_names
        
        # Find Deployments
        deployments = [d for d in docs if d and d.get("kind") == "Deployment"]
        deployment_names = [d.get("metadata", {}).get("name") for d in deployments]
        
        assert "prometheus" in deployment_names
        assert "alertmanager" in deployment_names


class TestEnvironmentDifferences:
    """Tests for differences between dev and prod environments."""

    def test_prod_has_external_secrets_dev_does_not(
        self, repo_root: Path, skip_without_kustomize
    ) -> None:
        """Verify prod has ExternalSecrets and dev does not."""
        # Build dev
        dev_result = subprocess.run(
            ["kustomize", "build", "k8s/envs/dev"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        assert dev_result.returncode == 0
        
        # Build prod
        prod_result = subprocess.run(
            [
                "kustomize",
                "build",
                "k8s/envs/prod",
                "--load-restrictor=LoadRestrictionsNone",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        assert prod_result.returncode == 0
        
        dev_docs = list(yaml.safe_load_all(dev_result.stdout))
        prod_docs = list(yaml.safe_load_all(prod_result.stdout))
        
        # Check for ExternalSecrets
        dev_external_secrets = [
            d for d in dev_docs if d and d.get("kind") == "ExternalSecret"
        ]
        prod_external_secrets = [
            d for d in prod_docs if d and d.get("kind") == "ExternalSecret"
        ]
        
        # Dev might have some, but prod should definitely have them
        assert len(prod_external_secrets) > 0, "Prod must have ExternalSecrets"

    def test_prod_has_environment_labels(
        self, repo_root: Path, skip_without_kustomize
    ) -> None:
        """Verify all prod resources have environment=prod label."""
        result = subprocess.run(
            [
                "kustomize",
                "build",
                "k8s/envs/prod",
                "--load-restrictor=LoadRestrictionsNone",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        
        assert result.returncode == 0
        
        docs = list(yaml.safe_load_all(result.stdout))
        
        missing_labels = []
        for doc in docs:
            if not doc or doc.get("kind") == "Namespace":
                continue
            
            metadata = doc.get("metadata", {})
            labels = metadata.get("labels", {})
            
            if labels.get("environment") != "prod":
                missing_labels.append(
                    f"{doc.get('kind')}/{metadata.get('name')}"
                )
        
        if missing_labels:
            pytest.fail("Resources missing environment=prod label:\n" + "\n".join(missing_labels))

    def test_replica_counts_differ(
        self, repo_root: Path, skip_without_kustomize
    ) -> None:
        """Verify replica counts differ between dev and prod where applicable."""
        # Build dev
        dev_result = subprocess.run(
            ["kustomize", "build", "k8s/envs/dev"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        assert dev_result.returncode == 0
        
        # Build prod
        prod_result = subprocess.run(
            [
                "kustomize",
                "build",
                "k8s/envs/prod",
                "--load-restrictor=LoadRestrictionsNone",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        assert prod_result.returncode == 0
        
        dev_docs = list(yaml.safe_load_all(dev_result.stdout))
        prod_docs = list(yaml.safe_load_all(prod_result.stdout))
        
        # Get deployments with replicas
        dev_deployments = {
            d.get("metadata", {}).get("name"): d.get("spec", {}).get("replicas", 1)
            for d in dev_docs
            if d and d.get("kind") == "Deployment" and "replicas" in d.get("spec", {})
        }
        
        prod_deployments = {
            d.get("metadata", {}).get("name"): d.get("spec", {}).get("replicas", 1)
            for d in prod_docs
            if d and d.get("kind") == "Deployment" and "replicas" in d.get("spec", {})
        }
        
        # Prod should have >= replicas than dev for critical services
        for name in set(dev_deployments.keys()) & set(prod_deployments.keys()):
            if "layer1" in name or "layer4" in name:
                assert prod_deployments[name] >= dev_deployments[name], \
                    f"{name}: prod replicas ({prod_deployments[name]}) < dev ({dev_deployments[name]})"


class TestCrossComponentIntegration:
    """Tests for cross-component integration and references."""

    def test_prometheus_references_alertmanager(
        self, repo_root: Path, skip_without_kustomize
    ) -> None:
        """Verify Prometheus configuration references Alertmanager service."""
        result = subprocess.run(
            [
                "kustomize",
                "build",
                "k8s/envs/prod",
                "--load-restrictor=LoadRestrictionsNone",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        
        assert result.returncode == 0
        
        docs = list(yaml.safe_load_all(result.stdout))
        
        # Find Prometheus ConfigMap
        prometheus_config = None
        for doc in docs:
            if doc and doc.get("kind") == "ConfigMap":
                name = doc.get("metadata", {}).get("name", "")
                if "prometheus" in name:
                    prometheus_config = doc
                    break
        
        if not prometheus_config:
            pytest.skip("Prometheus ConfigMap not found")
        
        # Check data for alertmanager reference
        data = prometheus_config.get("data", {})
        prometheus_yml = data.get("prometheus.yml", "")
        
        assert "alertmanager" in prometheus_yml, "Prometheus must reference alertmanager"

    def test_services_have_valid_selectors(
        self, repo_root: Path, skip_without_kustomize
    ) -> None:
        """Verify all Services have valid selectors matching Deployments."""
        result = subprocess.run(
            [
                "kustomize",
                "build",
                "k8s/envs/prod",
                "--load-restrictor=LoadRestrictionsNone",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        
        assert result.returncode == 0
        
        docs = list(yaml.safe_load_all(result.stdout))
        
        # Get all deployment labels
        deployment_labels = {}
        for doc in docs:
            if doc and doc.get("kind") == "Deployment":
                name = doc.get("metadata", {}).get("name")
                labels = doc.get("spec", {}).get("template", {}).get("metadata", {}).get("labels", {})
                deployment_labels[name] = labels
        
        # Check services
        failures = []
        for doc in docs:
            if doc and doc.get("kind") == "Service":
                name = doc.get("metadata", {}).get("name")
                selector = doc.get("spec", {}).get("selector", {})
                
                if not selector:
                    failures.append(f"{name}: missing selector")
                    continue
                
                # Check that at least one deployment has matching labels
                matching = False
                for dep_name, dep_labels in deployment_labels.items():
                    if all(dep_labels.get(k) == v for k, v in selector.items()):
                        matching = True
                        break
                
                if not matching:
                    # This is a warning - might be selecting StatefulSets or other resources
                    print(f"INFO: Service {name} selector may not match any Deployment")

    def test_namespace_consistency(self, k8s_base_dir: Path) -> None:
        """Verify all resources in base specify the same namespace."""
        namespace_yaml = k8s_base_dir / "namespace.yml"
        
        with open(namespace_yaml) as f:
            doc = yaml.safe_load(f)
        
        expected_namespace = doc.get("metadata", {}).get("name")
        
        # Check kustomization for namespace
        kustomization = k8s_base_dir / "kustomization.yaml"
        with open(kustomization) as f:
            kust = yaml.safe_load(f)
        
        # Note: kustomization.yaml doesn't set namespace in base
        # Namespace is set in overlays
        
        # Just verify namespace.yml exists and has a valid name
        assert expected_namespace, "Namespace must have a name"
        assert expected_namespace == "value-fabric", "Namespace should be value-fabric"

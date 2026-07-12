"""Tests for Kustomize overlay composition and configuration.

Validates:
- Base layer resources are correctly defined
- Dev/prod overlays extend base properly
- Image pinning in production (SHA digests)
- Replica scaling patches in prod
- Namespace configuration
- Label selectors and environment tags
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

ZERO_SHA256_DIGEST = "sha256:" + ("0" * 64)


class TestKustomizeBaseLayer:
    """Test the base Kustomization layer (k8s/base/)."""

    def test_base_kustomization_yaml_exists(self, k8s_base_dir: Path) -> None:
        """[2a] Verify base kustomization.yaml exists and is valid."""
        kustomization = k8s_base_dir / "kustomization.yaml"
        assert kustomization.exists(), "Base kustomization.yaml must exist"
        
        with open(kustomization) as f:
            content = yaml.safe_load(f)
        
        assert content.get("apiVersion") == "kustomize.config.k8s.io/v1beta1"
        assert content.get("kind") == "Kustomization"

    def test_base_resources_list_complete(self, k8s_base_dir: Path) -> None:
        """[2a] Verify base resources list includes all required components."""
        kustomization = k8s_base_dir / "kustomization.yaml"
        
        with open(kustomization) as f:
            content = yaml.safe_load(f)
        
        resources = content.get("resources", [])
        
        # Required core components
        required = [
            "namespace.yml",
            "configmap-global.yml",
            "postgres.yml",
            "redis.yml",
            "neo4j.yml",
        ]
        
        # All 6 layers
        layers = [
            "layer1-ingestion.yml",
            "layer2-extraction.yml",
            "layer3-knowledge.yml",
            "layer4-agents.yml",
            "layer5-ground-truth.yml",
            "layer6-benchmarks.yml",
        ]
        
        for r in required + layers:
            assert r in resources, f"Required resource {r} must be in base kustomization"

    def test_base_includes_monitoring_stack(self, k8s_base_dir: Path) -> None:
        """[2b] Verify monitoring stack is included in base resources."""
        kustomization = k8s_base_dir / "kustomization.yaml"
        
        with open(kustomization) as f:
            content = yaml.safe_load(f)
        
        resources = content.get("resources", [])
        
        assert "monitoring-prometheus.yml" in resources
        assert "monitoring-alertmanager.yml" in resources

    def test_base_includes_network_policies(self, k8s_base_dir: Path) -> None:
        """Verify network policies directory is included for zero-trust."""
        kustomization = k8s_base_dir / "kustomization.yaml"
        
        with open(kustomization) as f:
            content = yaml.safe_load(f)
        
        resources = content.get("resources", [])
        assert "network-policies/" in resources

    def test_base_includes_hpa_and_pdb(self, k8s_base_dir: Path) -> None:
        """Verify HPA and PodDisruptionBudget resources are included."""
        kustomization = k8s_base_dir / "kustomization.yaml"
        
        with open(kustomization) as f:
            content = yaml.safe_load(f)
        
        resources = content.get("resources", [])
        
        # HPA resources
        assert "hpa/layer2-extraction-hpa.yml" in resources
        assert "hpa/layer4-agents-hpa.yml" in resources
        assert "hpa/frontend-hpa.yml" in resources
        
        # PDB resources
        assert "pdb/layer4-agents-pdb.yml" in resources
        assert "pdb/layer2-extraction-pdb.yml" in resources
        assert "pdb/layer3-knowledge-pdb.yml" in resources
        assert "pdb/frontend-pdb.yml" in resources


class TestKustomizeProdOverlay:
    """Test the production Kustomize overlay (k8s/envs/prod/)."""

    def test_prod_kustomization_extends_base(self, k8s_overlays_dir: Path) -> None:
        """[2c] Verify prod overlay inherits from base layer."""
        kustomization = k8s_overlays_dir / "prod" / "kustomization.yaml"
        assert kustomization.exists()
        
        with open(kustomization) as f:
            content = yaml.safe_load(f)
        
        resources = content.get("resources", [])
        assert "../../base" in resources, "Prod must extend base layer"

    def test_prod_namespace_set(self, k8s_overlays_dir: Path) -> None:
        """Verify prod overlay sets the namespace to value-fabric."""
        kustomization = k8s_overlays_dir / "prod" / "kustomization.yaml"
        
        with open(kustomization) as f:
            content = yaml.safe_load(f)
        
        assert content.get("namespace") == "value-fabric"

    def test_prod_environment_label(self, k8s_overlays_dir: Path) -> None:
        """Verify prod overlay adds environment=prod label."""
        kustomization = k8s_overlays_dir / "prod" / "kustomization.yaml"
        
        with open(kustomization) as f:
            content = yaml.safe_load(f)
        
        labels = content.get("labels", [])
        env_label = next(
            (l for l in labels if l.get("pairs", {}).get("environment") == "prod"),
            None
        )
        assert env_label is not None, "Prod must have environment=prod label"

    def test_prod_includes_external_secrets(self, k8s_overlays_dir: Path) -> None:
        """Verify prod overlay includes ExternalSecret resources for Vault integration."""
        kustomization = k8s_overlays_dir / "prod" / "kustomization.yaml"
        
        with open(kustomization) as f:
            content = yaml.safe_load(f)
        
        resources = content.get("resources", [])
        
        assert "../../external-secrets/vault-integration.yml" in resources
        assert "../../external-secrets/vault-database-dynamic.yml" in resources

    def test_prod_replica_patch_applied(self, k8s_overlays_dir: Path) -> None:
        """[2d] Verify prod overlay applies replica scaling patches."""
        kustomization = k8s_overlays_dir / "prod" / "kustomization.yaml"
        
        with open(kustomization) as f:
            content = yaml.safe_load(f)
        
        patches = content.get("patches", [])
        patch_paths = [p.get("path", p) if isinstance(p, dict) else p for p in patches]
        
        assert "prod-replicas-patch.yml" in patch_paths

    def test_prod_replicas_patch_content(self, k8s_overlays_dir: Path) -> None:
        """[2e] Verify replica patch scales layer1-ingestion to 3 replicas for HA."""
        patch_file = k8s_overlays_dir / "prod" / "prod-replicas-patch.yml"
        assert patch_file.exists()
        
        with open(patch_file) as f:
            docs = list(yaml.safe_load_all(f.read()))
        
        # Find layer1-ingestion patch
        layer1_patch = next(
            (d for d in docs if d.get("metadata", {}).get("name") == "layer1-ingestion"),
            None
        )
        assert layer1_patch is not None, "Layer1 replica patch must exist"
        assert layer1_patch.get("spec", {}).get("replicas") == 3

    def test_prod_image_digest_pinning(self, k8s_overlays_dir: Path) -> None:
        """[2f] Verify production images use SHA digest pinning (immutable)."""
        kustomization = k8s_overlays_dir / "prod" / "kustomization.yaml"
        
        with open(kustomization) as f:
            content = yaml.safe_load(f)
        
        images = content.get("images", [])
        
        # All 6 layers + frontend should have digest pinning
        layer_names = [
            "services/layer1-ingestion",
            "services/layer2-extraction",
            "services/layer3-knowledge",
            "services/layer4-agents",
            "services/layer5-ground-truth",
            "services/layer6-benchmarks",
            "apps/web",
        ]
        
        for layer in layer_names:
            img = next((i for i in images if i.get("name") == layer), None)
            assert img is not None, f"{layer} must have image configuration"
            assert "digest" in img, f"{layer} must use digest pinning (not tags)"
            assert img["digest"].startswith("sha256:"), f"{layer} digest must be sha256"
            assert img["digest"] != ZERO_SHA256_DIGEST, f"{layer} must not use placeholder zero digest"

    def test_prod_infrastructure_image_tags(self, k8s_overlays_dir: Path) -> None:
        """Verify infrastructure images use specific versions (not :latest)."""
        kustomization = k8s_overlays_dir / "prod" / "kustomization.yaml"
        
        with open(kustomization) as f:
            content = yaml.safe_load(f)
        
        images = content.get("images", [])
        
        # Infrastructure images
        infra_images = {
            "postgres": "15.10-alpine",
            "redis": "7.4-alpine",
            "neo4j": "5.25-community",
        }
        
        for name, expected_tag in infra_images.items():
            img = next((i for i in images if i.get("name") == name), None)
            assert img is not None, f"{name} must have pinned version"
            has_correct_tag = img.get("newTag") == expected_tag
            has_digest = bool((img.get("digest") or "").startswith("sha256:"))
            assert has_correct_tag or has_digest, (
                f"{name} must use tag {expected_tag!r} or a sha256 digest pin, "
                f"got newTag={img.get('newTag')!r}, digest={img.get('digest')!r}"
            )


class TestKustomizeStagingOverlay:
    """Test the staging Kustomize overlay (k8s/envs/staging/)."""

    def test_staging_kustomization_extends_base(self, k8s_overlays_dir: Path) -> None:
        """Verify staging overlay inherits from base layer."""
        kustomization = k8s_overlays_dir / "staging" / "kustomization.yaml"
        assert kustomization.exists()

        with open(kustomization) as f:
            content = yaml.safe_load(f)

        resources = content.get("resources", [])
        assert "../../base" in resources, "Staging must extend base layer"

    def test_staging_namespace_set(self, k8s_overlays_dir: Path) -> None:
        """Verify staging overlay sets the namespace to value-fabric-staging."""
        kustomization = k8s_overlays_dir / "staging" / "kustomization.yaml"

        with open(kustomization) as f:
            content = yaml.safe_load(f)

        assert content.get("namespace") == "value-fabric-staging"

    def test_staging_environment_label(self, k8s_overlays_dir: Path) -> None:
        """Verify staging overlay adds environment=staging label."""
        kustomization = k8s_overlays_dir / "staging" / "kustomization.yaml"

        with open(kustomization) as f:
            content = yaml.safe_load(f)

        labels = content.get("labels", [])
        env_label = next(
            (l for l in labels if l.get("pairs", {}).get("environment") == "staging"),
            None
        )
        assert env_label is not None, "Staging must have environment=staging label"

    def test_staging_includes_external_secrets(self, k8s_overlays_dir: Path) -> None:
        """Verify staging overlay includes ExternalSecret resources for Vault integration."""
        kustomization = k8s_overlays_dir / "staging" / "kustomization.yaml"

        with open(kustomization) as f:
            content = yaml.safe_load(f)

        resources = content.get("resources", [])

        assert "../../external-secrets/vault-integration.yml" in resources
        assert "../../external-secrets/vault-database-dynamic.yml" in resources

    def test_staging_replica_patch_applied(self, k8s_overlays_dir: Path) -> None:
        """Verify staging overlay applies replica scaling patches."""
        kustomization = k8s_overlays_dir / "staging" / "kustomization.yaml"

        with open(kustomization) as f:
            content = yaml.safe_load(f)

        patches = content.get("patches", [])
        patch_paths = [p.get("path", p) if isinstance(p, dict) else p for p in patches]

        assert "staging-replicas-patch.yml" in patch_paths

    def test_staging_replicas_patch_content(self, k8s_overlays_dir: Path) -> None:
        """Verify replica patch scales layer1-ingestion to 2 replicas for HA."""
        patch_file = k8s_overlays_dir / "staging" / "staging-replicas-patch.yml"
        assert patch_file.exists()

        with open(patch_file) as f:
            docs = list(yaml.safe_load_all(f.read()))

        # Find layer1-ingestion patch
        layer1_patch = next(
            (d for d in docs if d.get("metadata", {}).get("name") == "layer1-ingestion"),
            None
        )
        assert layer1_patch is not None, "Layer1 replica patch must exist"
        assert layer1_patch.get("spec", {}).get("replicas") == 2

    def test_staging_image_digest_pinning(self, k8s_overlays_dir: Path) -> None:
        """Verify staging images use SHA digest pinning (immutable)."""
        kustomization = k8s_overlays_dir / "staging" / "kustomization.yaml"

        with open(kustomization) as f:
            content = yaml.safe_load(f)

        images = content.get("images", [])

        # All 6 layers + frontend should have digest pinning
        layer_names = [
            "services/layer1-ingestion",
            "services/layer2-extraction",
            "services/layer3-knowledge",
            "services/layer4-agents",
            "services/layer5-ground-truth",
            "services/layer6-benchmarks",
            "apps/web",
        ]

        for layer in layer_names:
            img = next((i for i in images if i.get("name") == layer), None)
            assert img is not None, f"{layer} must have image configuration"
            assert "digest" in img, f"{layer} must use digest pinning (not tags)"
            assert img["digest"].startswith("sha256:"), f"{layer} digest must be sha256"
            assert img["digest"] != ZERO_SHA256_DIGEST, f"{layer} must not use placeholder zero digest"

    def test_staging_infrastructure_image_tags(self, k8s_overlays_dir: Path) -> None:
        """Verify infrastructure images use specific versions (not :latest)."""
        kustomization = k8s_overlays_dir / "staging" / "kustomization.yaml"

        with open(kustomization) as f:
            content = yaml.safe_load(f)

        images = content.get("images", [])

        # Infrastructure images
        infra_images = {
            "postgres": "15.10-alpine",
            "redis": "7.4-alpine",
            "neo4j": "5.25-community",
        }

        for name, expected_tag in infra_images.items():
            img = next((i for i in images if i.get("name") == name), None)
            assert img is not None, f"{name} must have pinned version"
            has_correct_tag = img.get("newTag") == expected_tag
            has_digest = bool((img.get("digest") or "").startswith("sha256:"))
            assert has_correct_tag or has_digest, (
                f"{name} must use tag {expected_tag!r} or a sha256 digest pin, "
                f"got newTag={img.get('newTag')!r}, digest={img.get('digest')!r}"
            )


class TestKustomizeBuild:
    """Test kustomize build produces valid, complete manifests."""

    def test_dev_overlay_builds(self, repo_root: Path, skip_without_kustomize) -> None:
        """[1b] Dev overlay renders without errors."""
        result = subprocess.run(
            ["kustomize", "build", "k8s/envs/dev"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )
        
        assert result.returncode == 0, f"Dev build failed: {result.stderr}"
        assert result.stdout, "Dev build produced empty output"
        
        # Verify it produces valid YAML with expected resources
        docs = list(yaml.safe_load_all(result.stdout))
        kinds = [d.get("kind") for d in docs if d]
        
        assert "Namespace" in kinds
        assert "Deployment" in kinds
        assert "Service" in kinds

    def test_staging_overlay_builds(self, repo_root: Path, skip_without_kustomize) -> None:
        """Staging overlay renders without errors."""
        result = subprocess.run(
            [
                "kustomize",
                "build",
                "k8s/envs/staging",
                "--load-restrictor=LoadRestrictionsNone",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )

        assert result.returncode == 0, f"Staging build failed: {result.stderr}"
        assert result.stdout, "Staging build produced empty output"

    def test_staging_includes_external_secrets(self, repo_root: Path, skip_without_kustomize) -> None:
        """Verify staging build includes ExternalSecret resources."""
        result = subprocess.run(
            [
                "kustomize",
                "build",
                "k8s/envs/staging",
                "--load-restrictor=LoadRestrictionsNone",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )

        docs = list(yaml.safe_load_all(result.stdout))
        kinds = [d.get("kind") for d in docs if d]

        assert "ExternalSecret" in kinds, "Staging must include ExternalSecret resources"
        assert "Secret" not in kinds, "Staging must not include raw Secret resources"

    def test_staging_has_environment_label(self, repo_root: Path, skip_without_kustomize) -> None:
        """Verify all staging resources have environment=staging label."""
        result = subprocess.run(
            [
                "kustomize",
                "build",
                "k8s/envs/staging",
                "--load-restrictor=LoadRestrictionsNone",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )

        docs = list(yaml.safe_load_all(result.stdout))

        for doc in docs:
            if not doc or doc.get("kind") == "Namespace":
                continue

            metadata = doc.get("metadata", {})
            labels = metadata.get("labels", {})

            assert labels.get("environment") == "staging", \
                f"{doc.get('kind')}/{metadata.get('name')} missing environment=staging label"

    def test_staging_replicas_scaled(self, repo_root: Path, skip_without_kustomize) -> None:
        """Verify staging replica patches are applied."""
        result = subprocess.run(
            [
                "kustomize",
                "build",
                "k8s/envs/staging",
                "--load-restrictor=LoadRestrictionsNone",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )

        docs = list(yaml.safe_load_all(result.stdout))

        layer1_deployment = next(
            (d for d in docs
             if d.get("kind") == "Deployment" and
             d.get("metadata", {}).get("name") == "layer1-ingestion"),
            None
        )

        assert layer1_deployment is not None
        assert layer1_deployment.get("spec", {}).get("replicas") >= 2, \
            "Layer1 must have at least 2 replicas in staging"

    def test_prod_overlay_builds(self, repo_root: Path, skip_without_kustomize) -> None:
        """[1b] Prod overlay renders without errors."""
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
        
        assert result.returncode == 0, f"Prod build failed: {result.stderr}"
        assert result.stdout, "Prod build produced empty output"

    def test_prod_includes_external_secrets(self, repo_root: Path, skip_without_kustomize) -> None:
        """Verify prod build includes ExternalSecret resources."""
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
        
        docs = list(yaml.safe_load_all(result.stdout))
        kinds = [d.get("kind") for d in docs if d]
        
        assert "ExternalSecret" in kinds, "Prod must include ExternalSecret resources"
        assert "Secret" not in kinds, "Prod must not include raw Secret resources"

    def test_prod_has_environment_label(self, repo_root: Path, skip_without_kustomize) -> None:
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
        
        docs = list(yaml.safe_load_all(result.stdout))
        
        for doc in docs:
            if not doc or doc.get("kind") == "Namespace":
                continue
            
            metadata = doc.get("metadata", {})
            labels = metadata.get("labels", {})
            
            assert labels.get("environment") == "prod", \
                f"{doc.get('kind')}/{metadata.get('name')} missing environment=prod label"

    def test_prod_replicas_scaled(self, repo_root: Path, skip_without_kustomize) -> None:
        """Verify prod replica patches are applied."""
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
        
        docs = list(yaml.safe_load_all(result.stdout))
        
        layer1_deployment = next(
            (d for d in docs 
             if d.get("kind") == "Deployment" and 
             d.get("metadata", {}).get("name") == "layer1-ingestion"),
            None
        )
        
        assert layer1_deployment is not None
        assert layer1_deployment.get("spec", {}).get("replicas") >= 3, \
            "Layer1 must have at least 3 replicas in prod"

    def test_prod_uses_neo4j_aura_not_in_cluster_neo4j(self, repo_root: Path, skip_without_kustomize) -> None:
        """Production must not render the single-node in-cluster Neo4j deployment."""
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

        docs = list(yaml.safe_load_all(result.stdout))
        neo4j_deployment = next(
            (
                d for d in docs
                if d.get("kind") == "Deployment"
                and d.get("metadata", {}).get("name") == "neo4j"
            ),
            None,
        )
        assert neo4j_deployment is None


class TestKustomizeGatewayAPIDeployment:
    """Test the Gateway API deployment (prod-gateway-api) structure."""

    def test_prod_gateway_api_kustomization_exists(self, k8s_deployments_dir: Path) -> None:
        """Verify prod-gateway-api kustomization.yaml exists."""
        kustomization = k8s_deployments_dir / "prod-gateway-api" / "kustomization.yaml"
        assert kustomization.exists(), "prod-gateway-api kustomization.yaml must exist"

    def test_prod_gateway_api_imports_prod_env(self, k8s_deployments_dir: Path) -> None:
        """Verify prod-gateway-api imports the prod environment overlay."""
        kustomization = k8s_deployments_dir / "prod-gateway-api" / "kustomization.yaml"

        with open(kustomization) as f:
            content = yaml.safe_load(f)

        resources = content.get("resources", [])
        assert "../../envs/prod" in resources, "Must import prod environment"
        assert "../../routing/gateway-api" in resources, "Must import gateway-api routing"

    def test_prod_gateway_api_has_hostname_config(self, k8s_deployments_dir: Path) -> None:
        """Verify prod-gateway-api includes hostname configuration."""
        kustomization = k8s_deployments_dir / "prod-gateway-api" / "kustomization.yaml"

        with open(kustomization) as f:
            content = yaml.safe_load(f)

        resources = content.get("resources", [])
        assert "hostname-config.yaml" in resources, "Must include hostname config"

    def test_prod_gateway_api_has_replacements(self, k8s_deployments_dir: Path) -> None:
        """Verify prod-gateway-api has replacements for hostname substitution."""
        kustomization = k8s_deployments_dir / "prod-gateway-api" / "kustomization.yaml"

        with open(kustomization) as f:
            content = yaml.safe_load(f)

        replacements = content.get("replacements", [])
        assert len(replacements) >= 2, "Must have replacements for frontend and API hosts"

    def test_prod_gateway_api_builds(self, repo_root: Path, skip_without_kustomize) -> None:
        """Verify prod-gateway-api renders without errors."""
        result = subprocess.run(
            [
                "kustomize",
                "build",
                "k8s/deployments/prod-gateway-api",
                "--load-restrictor=LoadRestrictionsNone",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )

        assert result.returncode == 0, f"prod-gateway-api build failed: {result.stderr}"
        assert result.stdout, "prod-gateway-api build produced empty output"

    def test_prod_gateway_api_includes_gateway_resources(self, repo_root: Path, skip_without_kustomize) -> None:
        """Verify prod-gateway-api includes Gateway and HTTPRoute resources."""
        result = subprocess.run(
            [
                "kustomize",
                "build",
                "k8s/deployments/prod-gateway-api",
                "--load-restrictor=LoadRestrictionsNone",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )

        docs = list(yaml.safe_load_all(result.stdout))
        kinds = [d.get("kind") for d in docs if d]

        assert "Gateway" in kinds, "Must include Gateway resource"
        assert "HTTPRoute" in kinds, "Must include HTTPRoute resources"
        assert "Certificate" in kinds, "Must include Certificate resources"

    def test_prod_gateway_api_gateway_has_valid_class(self, repo_root: Path, skip_without_kustomize) -> None:
        """Verify Gateway has a valid gatewayClassName set."""
        result = subprocess.run(
            [
                "kustomize",
                "build",
                "k8s/deployments/prod-gateway-api",
                "--load-restrictor=LoadRestrictionsNone",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
        )

        docs = list(yaml.safe_load_all(result.stdout))
        gateway = next(
            (d for d in docs if d.get("kind") == "Gateway"),
            None
        )

        assert gateway is not None, "Gateway must exist"
        gateway_class = gateway.get("spec", {}).get("gatewayClassName", "")
        assert gateway_class and gateway_class != "", "gatewayClassName must be set"
        # Should be one of the known classes or a custom one
        assert gateway_class != "__GATEWAY_CLASS__", "gatewayClassName must be configured"

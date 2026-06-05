"""
GitOps and progressive delivery tests.

Policy:
- Local development: missing manifest files skip tests.
- CI (`CI=true`): required manifests fail closed with FileNotFoundError.

Validates:
1. Canary deployment configuration
2. Health gate logic
3. Feature flag behavior
4. Rollback triggers
"""

import os

import pytest
import yaml


def _load_yaml_documents(path: str, *, fail_in_ci: bool = False) -> list[dict]:
    """Load multi-document YAML with CI fail-closed behavior for missing files."""
    try:
        with open(path) as f:
            return list(yaml.safe_load_all(f))
    except FileNotFoundError:
        if fail_in_ci and os.getenv("CI") == "true":
            raise FileNotFoundError(f"Required manifest missing in CI: {path}") from None
        pytest.skip(f"File not found: {path}")


def _load_manifest_yaml(path: str, *, fail_in_ci: bool = False) -> list[dict]:
    """Resolve and load a manifest path using shared local-vs-CI policy."""
    manifest_path = os.path.expandvars(path)
    return _load_yaml_documents(manifest_path, fail_in_ci=fail_in_ci)


@pytest.fixture(scope="session")
def require_gitops_config():
    """Ensure GitOps config exists - hard fail in CI."""
    config_path = os.getenv("GITOPS_CONFIG_PATH", "k8s/gitops/")
    if not os.path.exists(config_path):
        if os.getenv("CI") == "true":
            raise FileNotFoundError(
                f"GitOps config required at {config_path}. "
                "Set GITOPS_CONFIG_PATH or create config files."
            )
        else:
            pytest.skip("GitOps config not found (local dev)")
    return config_path


class TestArgoRollouts:
    """Test Argo Rollouts configuration."""

    def test_rollout_yaml_valid(self, require_gitops_config):
        """Rollout YAML files are valid Kubernetes resources."""
        rollout_files = [
            "k8s/gitops/rollouts/layer4-agents-rollout.yaml",
            "k8s/gitops/rollouts/layer1-ingestion-rollout.yaml",
        ]

        for file in rollout_files:
            docs = _load_manifest_yaml(file, fail_in_ci=True)
            rollout = docs[0]

            # First doc should be a Rollout
            assert rollout["apiVersion"] == "argoproj.io/v1alpha1"
            assert rollout["kind"] == "Rollout"
            assert "spec" in rollout
            assert "strategy" in rollout["spec"]
            assert "canary" in rollout["spec"]["strategy"]

    def test_canary_steps_defined(self, require_gitops_config):
        """Canary rollout has proper steps defined."""
        rollout = _load_manifest_yaml("k8s/gitops/rollouts/layer4-agents-rollout.yaml", fail_in_ci=True)[0]
        steps = rollout["spec"]["strategy"]["canary"]["steps"]
        assert len(steps) > 0

        # Should have weight, pause, and analysis steps
        assert len([s for s in steps if "setWeight" in s]) >= 2
        assert len([s for s in steps if "pause" in s]) >= 1
        assert len([s for s in steps if "analysis" in s]) >= 1

    def test_auto_rollback_enabled(self):
        """Auto-rollback is enabled for safety."""
        rollout = _load_manifest_yaml("k8s/gitops/rollouts/layer4-agents-rollout.yaml", fail_in_ci=True)[0]
        canary = rollout["spec"]["strategy"]["canary"]
        assert canary.get("autoRollbackEnabled") is True

    def test_analysis_templates_defined(self):
        """Analysis templates are properly configured."""
        docs = _load_manifest_yaml("k8s/gitops/rollouts/layer4-agents-rollout.yaml", fail_in_ci=True)

        templates = [d for d in docs if d.get("kind") == "AnalysisTemplate"]
        assert len(templates) >= 2  # success-rate, latency, error-rate

        for template in templates:
            assert "spec" in template
            assert "metrics" in template["spec"]

            for metric in template["spec"]["metrics"]:
                assert "name" in metric
                assert "interval" in metric
                assert "provider" in metric


class TestHealthGates:
    """Test health gate configuration."""

    def test_health_gates_yaml_valid(self):
        """Health gates YAML is valid."""
        docs = _load_manifest_yaml("k8s/gitops/rollouts/health-gates.yaml", fail_in_ci=True)

        # Should have AnalysisRun definitions
        analysis_runs = [d for d in docs if d.get("kind") == "AnalysisRun"]
        assert len(analysis_runs) >= 1

    def test_pre_deployment_health_checks(self):
        """Pre-deployment health checks are comprehensive."""
        docs = _load_manifest_yaml("k8s/gitops/rollouts/health-gates.yaml", fail_in_ci=True)

        # Find deployment health gate
        health_gate = None
        for doc in docs:
            if doc.get("kind") == "AnalysisRun" and "deployment-health-gate" in str(
                doc.get("metadata", {}).get("name", "")
            ):
                health_gate = doc
                break

        if health_gate:
            metrics = health_gate["spec"]["metrics"]
            metric_names = [m["name"] for m in metrics]

            # Should check environment, resources, errors, database
            assert any("environment" in n or "health" in n for n in metric_names)
            assert any("resource" in n for n in metric_names)
            assert any("error" in n for n in metric_names)


class TestFeatureFlags:
    """Test feature flag configuration."""

    def test_feature_flags_per_environment(self):
        """Feature flags are configured per environment."""
        docs = _load_manifest_yaml("k8s/feature-flags/feature-flag-config.yaml", fail_in_ci=True)

        # Should have ConfigMaps for each environment
        configmaps = [d for d in docs if d.get("kind") == "ConfigMap"]
        assert len(configmaps) >= 3  # dev, staging, prod

        namespaces = [cm["metadata"]["namespace"] for cm in configmaps]
        assert any("prod" in ns for ns in namespaces)
        assert any("staging" in ns for ns in namespaces)
        assert any("dev" in ns for ns in namespaces)

    def test_production_conservative_rollout(self):
        """Production has conservative feature flag settings."""
        docs = _load_manifest_yaml("k8s/feature-flags/feature-flag-config.yaml", fail_in_ci=True)

        # Find production ConfigMap
        prod_cm = None
        for doc in docs:
            if doc.get("kind") == "ConfigMap" and "prod" in doc.get("metadata", {}).get("namespace", ""):
                prod_cm = doc
                break

        if prod_cm:
            data = prod_cm.get("data", {})

            # Experimental features should be disabled in prod
            assert data.get("FEATURE_EXPERIMENTAL_AI") == "false"
            assert data.get("FEATURE_BETA_FORMULAS") == "false"

            # Core features should be enabled
            assert data.get("FEATURE_MULTI_TENANT_ISOLATION") == "true"
            assert data.get("FEATURE_SSO_OIDC") == "true"

    def test_dev_all_features_enabled(self):
        """Development environment has all features enabled."""
        docs = _load_manifest_yaml("k8s/feature-flags/feature-flag-config.yaml", fail_in_ci=True)

        # Find dev ConfigMap
        dev_cm = None
        for doc in docs:
            if doc.get("kind") == "ConfigMap" and "dev" in doc.get("metadata", {}).get("namespace", ""):
                dev_cm = doc
                break

        if dev_cm:
            data = dev_cm.get("data", {})

            # All features should be enabled in dev
            for key, value in data.items():
                if key.startswith("FEATURE_"):
                    assert value == "true", f"Feature {key} should be enabled in dev"
                if key.startswith("ROLLOUT_"):
                    assert value == "100", f"Rollout {key} should be 100% in dev"


class TestArgoCD:
    """Test ArgoCD application configuration."""

    def test_argocd_bootstrap_manifest_declares_namespace_and_base_application(self):
        docs = _load_manifest_yaml("k8s/gitops/argocd-install.yaml", fail_in_ci=True)

        namespaces = [d for d in docs if d.get("kind") == "Namespace"]
        apps = [d for d in docs if d.get("kind") == "Application"]

        assert any(ns.get("metadata", {}).get("name") == "argocd" for ns in namespaces)
        assert any(app.get("metadata", {}).get("name") == "fabric-4l-base" for app in apps)

    def test_argocd_applications_yaml_valid(self):
        """ArgoCD applications YAML is valid."""
        docs = _load_manifest_yaml("k8s/gitops/argocd-applications.yaml", fail_in_ci=True)

        # Should have Applications
        apps = [d for d in docs if d.get("kind") == "Application"]
        assert len(apps) >= 3  # dev, staging, production

        # Should have AppProject
        projects = [d for d in docs if d.get("kind") == "AppProject"]
        assert len(projects) >= 1

        app_sets = [d for d in docs if d.get("kind") == "ApplicationSet"]
        assert len(app_sets) >= 1

    def test_argocd_operational_docs_do_not_claim_missing_manifests(self):
        workflow = open(".github/workflows/environment-promotion.yml", encoding="utf-8").read()
        checklist = open("docs/PRODUCTION_READINESS_CHECKLIST.md", encoding="utf-8").read()

        stale_claims = [
            "ArgoCD not installed",
            "no ArgoCD installation manifest",
            "no argocd namespace setup",
        ]
        for claim in stale_claims:
            assert claim not in workflow
            assert claim not in checklist

        assert "cluster sync/rollback evidence is still missing" in checklist
        assert "cluster sync unverified" in workflow

    def test_production_requires_manual_sync(self):
        """Production application requires manual sync."""
        docs = _load_manifest_yaml("k8s/gitops/argocd-applications.yaml", fail_in_ci=True)

        # Find production application
        prod_app = None
        for doc in docs:
            if doc.get("kind") == "Application" and "production" in str(
                doc.get("metadata", {}).get("name", "")
            ):
                prod_app = doc
                break

        if prod_app:
            sync_policy = prod_app["spec"]["syncPolicy"]
            automated = sync_policy.get("automated", {})

            # Production should not auto-sync
            assert automated.get("selfHeal") is False or automated.get("prune") is False


class TestCanaryConfiguration:
    """Test Flagger canary configuration."""

    def test_flagger_canary_yaml_valid(self):
        """Flagger canary YAML is valid."""
        try:
            with open("k8s/feature-flags/flagger-canary.yaml") as f:
                canary = yaml.safe_load(f)

            assert canary["apiVersion"] == "flagger.app/v1beta1"
            assert canary["kind"] == "Canary"
            assert "spec" in canary
        except FileNotFoundError:
            pytest.skip("Flagger canary file not found")

    def test_canary_thresholds_reasonable(self):
        """Canary thresholds are set to reasonable values."""
        try:
            with open("k8s/feature-flags/flagger-canary.yaml") as f:
                canary = yaml.safe_load(f)

            analysis = canary["spec"]["analysis"]

            # Threshold should allow some failures but not too many
            assert analysis["threshold"] <= 10

            # Max weight should not be 100 (that's full promotion)
            assert analysis["maxWeight"] <= 50

            # Step weight should be reasonable
            assert analysis["stepWeight"] >= 5
        except FileNotFoundError:
            pytest.skip("Flagger canary file not found")

    def test_webhooks_configured(self):
        """Pre/post rollout webhooks are configured."""
        try:
            with open("k8s/feature-flags/flagger-canary.yaml") as f:
                canary = yaml.safe_load(f)

            webhooks = canary["spec"]["analysis"].get("webhooks", [])
            webhook_types = [w.get("type") for w in webhooks]

            # Should have acceptance test before rollout
            assert "pre-rollout" in webhook_types

            # Should have load test during rollout
            assert "rollout" in webhook_types

            # Should have conformance test after rollout
            assert "post-rollout" in webhook_types

            # Should have rollback notification
            assert "rollback" in webhook_types
        except FileNotFoundError:
            pytest.skip("Flagger canary file not found")

"""Static production-blocker regression tests for Kubernetes manifests."""

from __future__ import annotations

from pathlib import Path

import yaml


def _load_yaml(path: Path) -> list[dict]:
    return [doc for doc in yaml.safe_load_all(path.read_text()) if doc]


def _resource_names(path: Path, kind: str) -> set[str]:
    return {
        doc.get("metadata", {}).get("name", "")
        for doc in _load_yaml(path)
        if doc.get("kind") == kind
    }


def test_prod_neo4j_is_aura_only(repo_root: Path) -> None:
    patch = (repo_root / "k8s/envs/prod/neo4j-aura-delete-deployment.yml").read_text()
    secrets = (repo_root / "k8s/external-secrets/neo4j-secrets.yaml").read_text()

    assert "$patch: delete" in patch
    assert "bolt://neo4j:7687" not in secrets
    assert 'NEO4J_URI: "{{ .neo4j_uri }}"' in secrets


def test_operator_evidence_exists_for_prod_crds(repo_root: Path) -> None:
    evidence = (repo_root / "k8s/operators/operator-prerequisites.yaml").read_text()
    prod_kustomization = yaml.safe_load((repo_root / "k8s/envs/prod/kustomization.yaml").read_text())

    assert "clusters.postgresql.cnpg.io" in evidence
    assert "Install CloudNativePG operator before applying k8s/envs/prod." in evidence
    assert "redisfailovers.databases.spotahome.com" in evidence
    assert "Install Spotahome Redis Operator before applying k8s/envs/prod." in evidence
    assert "../../operators" in prod_kustomization["resources"]


def test_prod_includes_thanos_and_loki_fluent_bit(repo_root: Path) -> None:
    prod_kustomization = yaml.safe_load((repo_root / "k8s/envs/prod/kustomization.yaml").read_text())
    resources = set(prod_kustomization["resources"])

    assert "../../monitoring/thanos.yml" in resources
    assert "../../monitoring/loki-fluent-bit.yml" in resources
    assert {"thanos-query", "thanos-store", "thanos-compactor"} <= _resource_names(
        repo_root / "k8s/monitoring/thanos.yml",
        "Deployment",
    )
    assert "loki" in _resource_names(repo_root / "k8s/monitoring/loki-fluent-bit.yml", "Deployment")
    assert "fluent-bit" in _resource_names(repo_root / "k8s/monitoring/loki-fluent-bit.yml", "DaemonSet")


def test_istio_routing_enforces_strict_mtls(repo_root: Path) -> None:
    kustomization = yaml.safe_load((repo_root / "k8s/routing/istio/kustomization.yaml").read_text())
    resources = set(kustomization["resources"])
    peer_auth_docs = _load_yaml(repo_root / "k8s/routing/istio/peerauthentication.yaml")
    authz_docs = _load_yaml(repo_root / "k8s/routing/istio/authorizationpolicy.yaml")

    assert "peerauthentication.yaml" in resources
    assert "authorizationpolicy.yaml" in resources
    assert peer_auth_docs[0]["kind"] == "PeerAuthentication"
    assert peer_auth_docs[0]["spec"]["mtls"]["mode"] == "STRICT"
    assert authz_docs[0]["kind"] == "AuthorizationPolicy"


def test_prod_has_resource_quota_and_limit_range(repo_root: Path) -> None:
    base_kustomization = yaml.safe_load((repo_root / "k8s/base/kustomization.yaml").read_text())
    tenant_safety = _load_yaml(repo_root / "k8s/base/tenant-safety.yml")
    kinds = {doc["kind"] for doc in tenant_safety}

    assert "tenant-safety.yml" in base_kustomization["resources"]
    assert {"ResourceQuota", "LimitRange"} <= kinds


def test_pgbouncer_auth_material_is_not_committed_or_configmapped(repo_root: Path) -> None:
    base_kustomization = yaml.safe_load((repo_root / "k8s/base/kustomization.yaml").read_text())
    prod_kustomization = yaml.safe_load((repo_root / "k8s/envs/prod/kustomization.yaml").read_text())
    config = _load_yaml(repo_root / "k8s/base/pgbouncer-config.yml")[0]
    deployment = _load_yaml(repo_root / "k8s/base/pgbouncer.yml")[0]

    assert "pgbouncer-config.yml" in base_kustomization["resources"]
    assert "pgbouncer.yml" in base_kustomization["resources"]
    assert "../../external-secrets/pgbouncer-secrets.yaml" in prod_kustomization["resources"]
    assert not (repo_root / "k8s/base/userlist.txt").exists()
    assert "userlist.txt" not in config.get("data", {})
    assert "md5a8f7c7e8d9e0f1a2b3c4d5e6f7a8b9c" not in config.get("data", {}).get(
        "pgbouncer.ini", ""
    )

    volumes = deployment["spec"]["template"]["spec"]["volumes"]
    auth_volume = next(v for v in volumes if v["name"] == "pgbouncer-auth")
    assert auth_volume["secret"]["secretName"] == "pgbouncer-auth"
    assert "postgres-secret" not in yaml.safe_dump(deployment)


def test_prod_external_secrets_require_secure_datastore_transports(repo_root: Path) -> None:
    layer4 = (repo_root / "k8s/external-secrets/layer4-secrets.yaml").read_text()
    redis = (repo_root / "k8s/external-secrets/redis-secrets.yaml").read_text()
    postgres = (repo_root / "k8s/external-secrets/layer4-secrets.yaml").read_text()
    neo4j = (repo_root / "k8s/external-secrets/neo4j-secrets.yaml").read_text()

    assert "DATABASE_URL: \"postgresql://" in postgres
    assert "sslmode=require" in postgres
    assert "rediss://redis:6379" in layer4
    assert "REDIS_URL: \"rediss://" in redis
    assert 'NEO4J_URI: "{{ .neo4j_uri }}"' in neo4j
    assert "bolt://neo4j:7687" not in layer4

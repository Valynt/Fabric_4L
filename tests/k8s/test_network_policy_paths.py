"""NetworkPolicy and service-identity verification for Kubernetes manifests."""

from __future__ import annotations

from pathlib import Path

import yaml


def _load_documents(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [doc for doc in yaml.safe_load_all(f) if doc]


def _load_single(path: Path) -> dict:
    docs = _load_documents(path)
    assert len(docs) == 1, f"expected exactly one document in {path}"
    return docs[0]


def test_layer4_policy_uses_exact_workload_selectors(repo_root: Path) -> None:
    policy = _load_single(
        repo_root / "k8s" / "base" / "network-policies" / "layer4-policy.yml"
    )
    egress = policy["spec"]["egress"]
    selectors = []
    for rule in egress:
        for peer in rule.get("to", []):
            selector = peer.get("podSelector", {}).get("matchLabels", {})
            if selector:
                selectors.append(selector)

    assert {"app": "layer1-ingestion"} in selectors
    assert {"app": "layer2-extraction"} in selectors
    assert {"app": "layer3-knowledge"} in selectors
    assert {"app": "layer5-ground-truth"} in selectors
    assert {"app": "layer6-benchmarks"} in selectors
    assert {"app": "postgres"} in selectors
    assert {"app": "redis"} in selectors
    assert {"app": "neo4j"} in selectors
    assert {
        "component": "layer1"
    } not in selectors, "broad component selectors must not be used"
    assert {
        "component": "infrastructure"
    } not in selectors, "broad component selectors must not be used"


def test_infra_policy_disallows_namespace_wide_ingress(repo_root: Path) -> None:
    policy = _load_single(
        repo_root / "k8s" / "base" / "network-policies" / "infra-policy.yml"
    )
    ingress_rules = policy["spec"]["ingress"]
    for rule in ingress_rules:
        for src in rule.get("from", []):
            assert (
                "namespaceSelector" not in src or src["namespaceSelector"]
            ), "namespace-wide allow is forbidden"

    allowed_apps = {
        src["podSelector"]["matchLabels"]["app"]
        for src in ingress_rules[0]["from"]
        if "podSelector" in src
    }
    assert allowed_apps == {
        "api-gateway",
        "layer1-ingestion",
        "layer2-extraction",
        "layer3-knowledge",
        "layer4-agents",
        "layer5-ground-truth",
    }


def test_istio_identity_enforcement_for_cross_layer_traffic(repo_root: Path) -> None:
    policy = _load_single(
        repo_root / "k8s" / "routing" / "istio" / "authorizationpolicy.yaml"
    )
    rules = policy["spec"]["rules"]
    principal_rule = next(
        (rule for rule in rules if "from" in rule and "to" in rule), None
    )
    assert (
        principal_rule is not None
    ), "expected principal-bound allow rule for cross-layer traffic"

    principals = set(principal_rule["from"][0]["source"]["principals"])
    expected = {
        "cluster.local/ns/value-fabric/sa/api-gateway",
        "cluster.local/ns/value-fabric/sa/layer1-ingestion",
        "cluster.local/ns/value-fabric/sa/layer2-extraction",
        "cluster.local/ns/value-fabric/sa/layer3-knowledge",
        "cluster.local/ns/value-fabric/sa/layer4-agents",
        "cluster.local/ns/value-fabric/sa/layer5-ground-truth",
        "cluster.local/ns/value-fabric/sa/layer6-benchmarks",
    }
    assert expected.issubset(principals)

    ports = set(principal_rule["to"][0]["operation"]["ports"])
    assert {"8000", "8001", "8005", "8006", "5432", "6379", "7687"}.issubset(ports)

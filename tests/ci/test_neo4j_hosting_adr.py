from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ADR = REPO_ROOT / "docs" / "explanations" / "adr" / "ADR-030-neo4j-hosting-decision.md"
ADR_INDEX = REPO_ROOT / "docs" / "explanations" / "adr" / "README.md"
READINESS_STATUS = REPO_ROOT / "docs" / "validation" / "production_readiness_execution_status.md"
PROD_KUSTOMIZATION = REPO_ROOT / "k8s" / "envs" / "prod" / "kustomization.yaml"
PROD_AURA_PATCH = REPO_ROOT / "k8s" / "envs" / "prod" / "neo4j-aura-patch.yml"


def test_neo4j_hosting_adr_is_accepted_and_indexed() -> None:
    adr = ADR.read_text(encoding="utf-8")
    index = ADR_INDEX.read_text(encoding="utf-8")
    readiness_status = READINESS_STATUS.read_text(encoding="utf-8")

    assert "## Status\n\nAccepted" in adr
    assert "| [ADR-030](./ADR-030-neo4j-hosting-decision.md) | Neo4j Hosting Decision | ✅ Accepted | 2026-06-23 |" in index
    assert "Accepted: managed Neo4j Aura is the production path" in readiness_status
    assert "Evaluate Neo4j Aura vs. Helm fallback" not in readiness_status


def test_production_overlay_uses_aura_patch_instead_of_in_cluster_neo4j() -> None:
    kustomization = PROD_KUSTOMIZATION.read_text(encoding="utf-8")
    patch = PROD_AURA_PATCH.read_text(encoding="utf-8")

    assert "neo4j-aura-patch.yml" in kustomization
    assert "kind: Deployment" in patch
    assert "kind: Service" in patch
    assert "kind: PersistentVolumeClaim" in patch
    assert "$patch: delete" in patch

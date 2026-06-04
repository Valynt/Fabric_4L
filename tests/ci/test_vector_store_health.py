from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "check_vector_store_health.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_vector_store_health", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_minimal_repo(root: Path, *, neo4j_tag: str = "5-community", include_indexes: bool = True, dimension_from_settings: bool = True) -> None:
    (root / "services/layer3-knowledge/src/schema").mkdir(parents=True)
    (root / "services/layer3-knowledge/src/config").mkdir(parents=True)
    (root / "services/layer3-knowledge/src/docs").mkdir(parents=True)
    (root / "docs/reference").mkdir(parents=True)

    (root / "docker-compose.dev.yml").write_text(
        f"services:\n  neo4j:\n    image: neo4j:{neo4j_tag}\n",
        encoding="utf-8",
    )
    index_lines = ""
    if include_indexes:
        index_lines = "\n".join(
            [
                'Index("capability_embedding_idx", "Capability", ["embedding"], "vector"),',
                'Index("usecase_embedding_idx", "UseCase", ["embedding"], "vector"),',
                'Index("persona_embedding_idx", "Persona", ["embedding"], "vector"),',
                'Index("valuedriver_embedding_idx", "ValueDriver", ["embedding"], "vector"),',
            ]
        )
    dimension_line = "embedding_dimension = get_settings().embedding_dimension" if dimension_from_settings else "embedding_dimension = 384"
    (root / "services/layer3-knowledge/src/schema/constraints.py").write_text(
        f"{dimension_line}\n`vector.dimensions`: {{embedding_dimension}}\n{index_lines}\n",
        encoding="utf-8",
    )
    (root / "services/layer3-knowledge/src/schema/initializer.py").write_text(
        "expected = self.settings.embedding_dimension\n`vector.dimensions`: {embedding_dimension}\n",
        encoding="utf-8",
    )
    (root / "services/layer3-knowledge/src/config/settings.py").write_text(
        'embedding_dimension: int = Field(default=384, alias="EMBEDDING_DIMENSION")\n',
        encoding="utf-8",
    )
    (root / "docs/architecture.md").write_text("Layer 3 uses Neo4j native vector indexes.\n", encoding="utf-8")
    (root / "docs/reference/layer3-knowledge-api.md").write_text("Vector search uses Neo4j native vector indexes.\n", encoding="utf-8")
    (root / "services/layer3-knowledge/src/docs/api_documentation.py").write_text("Neo4j native vector indexes\n", encoding="utf-8")
    (root / "docs/Providers.md").write_text("Neo4j native vector indexes are active.\n", encoding="utf-8")


def error_keys(report: dict) -> set[str]:
    return {error["key"] for error in report["errors"]}


def test_neo4j_5_compose_image_is_accepted(tmp_path):
    module = load_module()
    write_minimal_repo(tmp_path, neo4j_tag="5-community")

    report = module.run_static_checks(tmp_path)

    assert report["active_vector_store"] == "neo4j_native"
    assert report["pgvector_required"] is False
    assert report["errors"] == []


def test_non_neo4j_5_compose_image_is_rejected(tmp_path):
    module = load_module()
    write_minimal_repo(tmp_path, neo4j_tag="4.4-community")

    report = module.run_static_checks(tmp_path)

    assert "neo4j_image_not_v5" in error_keys(report)


def test_missing_required_vector_index_declaration_is_rejected(tmp_path):
    module = load_module()
    write_minimal_repo(tmp_path, include_indexes=False)

    report = module.run_static_checks(tmp_path)

    assert "vector_index_declaration_missing" in error_keys(report)


def test_dimension_source_drift_is_rejected(tmp_path):
    module = load_module()
    write_minimal_repo(tmp_path, dimension_from_settings=False)

    report = module.run_static_checks(tmp_path)

    assert "embedding_dimension_source_drift" in error_keys(report)


def test_pgvector_backend_mode_is_rejected_until_supported(tmp_path):
    module = load_module()
    write_minimal_repo(tmp_path)

    report = module.run_static_checks(tmp_path, vector_store_backend="pgvector")

    assert "unsupported_vector_store_backend" in error_keys(report)

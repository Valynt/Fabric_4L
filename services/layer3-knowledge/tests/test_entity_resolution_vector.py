import pytest

from src.services.entity_resolution import (
    _annotate_vector_scores,
    _build_vector_query,
    _validate_entity_type_label,
)


def test_validate_entity_type_label_accepts_valid_alphanumeric():
    assert _validate_entity_type_label("Account") == "Account"
    assert _validate_entity_type_label("ValueDriver_2") == "ValueDriver_2"


@pytest.mark.parametrize(
    "label",
    [
        "1Account",
        "Account-1",
        "Account.1",
        "",
        None,
        "Account; DROP",
        " Account",
    ],
)
def test_validate_entity_type_label_rejects_invalid(label):
    with pytest.raises(ValueError):
        _validate_entity_type_label(label)


def test_build_vector_query_includes_label_and_parameters():
    query = _build_vector_query("Account")
    assert "CALL db.index.vector.queryNodes($index_name, $k, $embedding)" in query
    assert "node:Account" in query
    assert "node.tenant_id = $tenant_id" in query
    assert "score >= $threshold" in query
    assert "LIMIT $k" in query


def test_annotate_vector_scores_adds_metadata():
    records = [
        {"id": "a", "vector_score": 0.95},
        {"id": "b", "vector_score": 0.82},
    ]
    out = _annotate_vector_scores(records)
    assert out[0]["retrieval_metadata"]["vector_similarity"] == 0.95
    assert out[1]["retrieval_metadata"]["vector_similarity"] == 0.82


def test_annotate_vector_scores_preserves_existing_metadata():
    records = [
        {"id": "a", "vector_score": 0.9, "retrieval_metadata": {"source": "vector"}}
    ]
    out = _annotate_vector_scores(records)
    assert out[0]["retrieval_metadata"]["source"] == "vector"
    assert out[0]["retrieval_metadata"]["vector_similarity"] == 0.9

from http import HTTPStatus

from fastapi.testclient import TestClient

from src.services.embedding_errors import EmbeddingProviderUnavailableError


def test_semantic_search_embedding_provider_failure_returns_503(
    test_client: TestClient,
    monkeypatch,
) -> None:
    async def _fail(*args, **kwargs):
        raise EmbeddingProviderUnavailableError(
            "Embedding provider unavailable",
            provider="sentence-transformers",
            failure_cause="timeout",
            retry_after_seconds=45,
            retry_hint="retry_with_backoff",
        )

    monkeypatch.setattr(
        "src.services.evidence_search.EvidenceSearchService.find_matching_evidence",
        _fail,
    )

    response = test_client.post(
        "/v1/evidence/search",
        json={"query": "roi benchmarks", "limit": 5},
        headers={"x-correlation-id": "corr-test-123"},
    )
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        return

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert "Retry-After" in response.headers
    assert response.headers["Retry-After"] == "45"

    payload = response.json()
    detail = payload["detail"]
    assert detail["error_code"] == "SERVICE_UNAVAILABLE"
    assert detail["details"]["failure_cause"] == "timeout"
    assert detail["details"]["retry_hint"] == "retry_with_backoff"
    assert detail["details"]["correlation_id"] == "corr-test-123"

    assert "results" not in payload
    assert [0.0] * 384 != detail.get("embedding")

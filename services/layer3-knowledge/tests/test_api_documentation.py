from src.docs.api_documentation import (
    APIEndpoint,
    APIError,
    APIGuide,
    APITutorial,
    get_documentation,
    get_endpoint_documentation,
    get_error_documentation,
    get_guide,
    get_tutorial,
)


def test_documentation_payload_keeps_typed_sections() -> None:
    documentation = get_documentation()

    assert documentation["overview"]["title"] == "Value Fabric Layer 3 API"
    assert isinstance(documentation["endpoints"]["health"], APIEndpoint)
    assert isinstance(documentation["tutorials"][0], APITutorial)
    assert isinstance(documentation["guides"][0], APIGuide)


def test_endpoint_lookup_is_method_case_insensitive() -> None:
    endpoint = get_endpoint_documentation("/health", "get")

    assert endpoint is not None
    assert endpoint.method == "GET"
    assert endpoint.responses[200]["description"] == "Service is healthy"


def test_error_tutorial_and_guide_lookup() -> None:
    error = get_error_documentation("VALIDATION_ERROR")
    tutorial = get_tutorial("Getting Started with Semantic Search")
    guide = get_guide("Best Practices")

    assert isinstance(error, APIError)
    assert error.status_code == 400
    assert isinstance(tutorial, APITutorial)
    assert tutorial.difficulty == "beginner"
    assert isinstance(guide, APIGuide)
    assert "/v1/search" in guide.related_endpoints


def test_missing_documentation_lookup_returns_none() -> None:
    assert get_endpoint_documentation("/missing", "GET") is None
    assert get_error_documentation("MISSING_ERROR") is None
    assert get_tutorial("Missing tutorial") is None
    assert get_guide("Missing guide") is None

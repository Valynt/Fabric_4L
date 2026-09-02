from layer4_agents.api.routes.state_inspector import _categorize_error

def test_categorize_error():
    assert _categorize_error("A timeout occurred") == "network"
    assert _categorize_error("Invalid query for database") == "database"
    assert _categorize_error("System resource limit reached") == "system"
    assert _categorize_error("Unknown error happened here") == "other"
    assert _categorize_error("IndexError: list index out of range") == "code"
    assert _categorize_error("Unauthorized access forbidden") == "auth"
    assert _categorize_error("Anthropic API failed") == "llm"
    assert _categorize_error("Schema validation failed") == "validation"

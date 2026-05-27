import requests

BASE_URL = "http://localhost:3001"
TIMEOUT = 30

def test_get_api_v1_deliverables_cases_should_return_business_cases():
    """
    Verify that the GET /api/v1/deliverables/cases endpoint returns a list of business cases accessible to the user.
    This endpoint requires authentication; simulate a logged-in user via a placeholder token.
    """
    # Placeholder for an actual auth token; replace with a valid token for real testing
    auth_token = "Bearer valid_auth_token"

    headers = {
        "Authorization": auth_token,
        "Accept": "application/json"
    }

    url = f"{BASE_URL}/api/v1/deliverables/cases"

    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Request to {url} failed: {e}"

    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"

    # Validate that the response data is a list (of business cases)
    assert isinstance(data, list), f"Expected response to be a list, got {type(data)}"

    # If list is not empty, verify that first item has expected keys (basic validation)
    if data:
        required_keys = {"id", "title", "status"}  # example expected fields for business case
        missing_keys = required_keys - data[0].keys()
        assert not missing_keys, f"Missing expected keys in business case: {missing_keys}"

test_get_api_v1_deliverables_cases_should_return_business_cases()
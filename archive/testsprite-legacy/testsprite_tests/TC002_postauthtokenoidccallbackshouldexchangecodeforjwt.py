import requests

BASE_URL = "http://localhost:3001"

def test_post_auth_token_oidc_callback_should_exchange_code_for_jwt():
    url = f"{BASE_URL}/auth/token"
    headers = {
        "Content-Type": "application/json"
    }

    # Simulate valid code exchange
    valid_payload = {
        "code": "valid-auth-code"
    }
    try:
        response = requests.post(url, json=valid_payload, headers=headers, timeout=30)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        json_response = response.json()
        assert "token" in json_response, "JWT token not found in response"
        assert isinstance(json_response["token"], str) and len(json_response["token"]) > 0, "Invalid JWT token format"
    except requests.RequestException as e:
        assert False, f"Request failed with exception: {e}"

    # Simulate invalid code error handling
    invalid_payload = {
        "code": "invalid-auth-code"
    }
    try:
        response_invalid = requests.post(url, json=invalid_payload, headers=headers, timeout=30)
        # Expected to fail with 400 or 401 error (depending on server implementation)
        assert response_invalid.status_code in (400, 401), f"Expected 400 or 401, got {response_invalid.status_code}"
        json_invalid = response_invalid.json()
        assert "error" in json_invalid, "Error message expected in response for invalid code"
    except requests.RequestException as e:
        assert False, f"Request failed with exception: {e}"

    # Simulate expired code error handling
    expired_payload = {
        "code": "expired-auth-code"
    }
    try:
        response_expired = requests.post(url, json=expired_payload, headers=headers, timeout=30)
        # Expected to fail with 400 or 401 error on expired code
        assert response_expired.status_code in (400, 401), f"Expected 400 or 401, got {response_expired.status_code}"
        json_expired = response_expired.json()
        assert "error" in json_expired, "Error message expected in response for expired code"
    except requests.RequestException as e:
        assert False, f"Request failed with exception: {e}"


test_post_auth_token_oidc_callback_should_exchange_code_for_jwt()

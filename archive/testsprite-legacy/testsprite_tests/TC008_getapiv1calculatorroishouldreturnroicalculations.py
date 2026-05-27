import requests

BASE_URL = "http://localhost:3001"
TIMEOUT = 30

# Placeholder credentials for login - should be replaced with valid test credentials
TEST_EMAIL = "testuser@example.com"
TEST_PASSWORD = "TestPassword123!"

def test_get_api_v1_calculator_roi_should_return_roi_calculations():
    # Authenticate to obtain a token (using /auth/token endpoint per PRD)
    auth_url = f"{BASE_URL}/auth/token"
    auth_payload = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "grant_type": "password"
    }
    try:
        auth_resp = requests.post(auth_url, json=auth_payload, timeout=TIMEOUT)
        auth_resp.raise_for_status()
    except Exception as e:
        assert False, f"Authentication failed: {e}"
    auth_data = auth_resp.json()
    token = auth_data.get("accessToken")
    assert token and isinstance(token, str), "Auth response does not contain accessToken"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    roi_calc_url = f"{BASE_URL}/api/v1/calculator/roi"

    try:
        response = requests.get(roi_calc_url, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        assert False, f"HTTP error occurred: {http_err} - Response content: {response.text if response else 'No response'}"
    except Exception as err:
        assert False, f"Other error occurred: {err}"

    result = response.json()

    expected_keys = {"roi", "paybackPeriodMonths", "annualizedReturn", "netPresentValue"}
    assert isinstance(result, dict), "Response is not a JSON object"
    assert expected_keys.issubset(result.keys()), f"Response missing expected keys. Found keys: {result.keys()}"

    assert isinstance(result["roi"], (int, float)), "ROI is not numeric"
    assert isinstance(result["paybackPeriodMonths"], (int, float)), "Payback period is not numeric"
    assert isinstance(result["annualizedReturn"], (int, float)), "Annualized return is not numeric"
    assert isinstance(result["netPresentValue"], (int, float)), "Net present value is not numeric"

    # Additional basic sanity checks
    assert result["roi"] >= 0, "ROI is negative"
    assert result["paybackPeriodMonths"] > 0, "Payback period must be positive"


test_get_api_v1_calculator_roi_should_return_roi_calculations()

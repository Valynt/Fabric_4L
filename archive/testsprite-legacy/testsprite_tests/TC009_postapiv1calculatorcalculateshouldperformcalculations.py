import requests

BASE_URL = "http://localhost:3001"
CALCULATE_ENDPOINT = "/api/v1/calculator/calculate"
TIMEOUT = 30

# Note: Auth is required. This example assumes an authentication token is available.
# Fill in AUTH_TOKEN with a valid token if needed.
AUTH_TOKEN = "your_valid_auth_token_here"

def test_post_api_v1_calculator_calculate_should_perform_calculations():
    url = BASE_URL + CALCULATE_ENDPOINT
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}"
    }

    # Example valid payload with ROI and value model calculation parameters
    payload = {
        "financialInputs": {
            "initialInvestment": 100000,
            "annualRevenueIncrease": 20000,
            "annualCostSavings": 5000,
            "projectLifetimeYears": 5,
            "discountRate": 0.08
        },
        "valueModelParameters": {
            "valueDriverAdjustments": {
                "driverA": 1.2,
                "driverB": 0.85
            },
            "scenario": "base"
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
    except requests.exceptions.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"

    # Validate presence of key calculation results in response
    assert "roi" in data, "Response missing 'roi' field"
    assert isinstance(data["roi"], (int, float)), "'roi' should be a number"

    assert "netPresentValue" in data, "Response missing 'netPresentValue' field"
    assert isinstance(data["netPresentValue"], (int, float)), "'netPresentValue' should be a number"

    assert "valueModelResults" in data, "Response missing 'valueModelResults' field"
    assert isinstance(data["valueModelResults"], dict), "'valueModelResults' should be a dict"

    # Further checks: roi and netPresentValue calculated logically reasonable
    roi = data["roi"]
    npv = data["netPresentValue"]
    value_results = data["valueModelResults"]

    assert roi >= -1 and roi <= 10, f"ROI value {roi} out of expected range"
    assert isinstance(npv, (int, float)), "NPV is not numeric"

    # Check some expected keys inside valueModelResults (example)
    expected_value_keys = ["totalValue", "driversImpact"]
    for key in expected_value_keys:
        assert key in value_results, f"valueModelResults missing '{key}' field"

    assert isinstance(value_results.get("totalValue"), (int, float)), "'totalValue' should be numeric"
    assert isinstance(value_results.get("driversImpact"), dict), "'driversImpact' should be a dict"

test_post_api_v1_calculator_calculate_should_perform_calculations()
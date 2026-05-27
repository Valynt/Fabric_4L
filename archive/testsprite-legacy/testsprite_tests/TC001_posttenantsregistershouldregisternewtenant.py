import requests
import uuid

def test_post_tenants_register_should_register_new_tenant():
    base_url = "http://localhost:3001"
    url = f"{base_url}/tenants/register"
    headers = {
        "Content-Type": "application/json"
    }
    # Prepare a valid tenant registration payload with unique test data
    unique_identifier = str(uuid.uuid4())
    payload = {
        "name": f"Test Tenant {unique_identifier}",
        "email": f"tenant-{unique_identifier}@example.com",
        "password": "StrongPassword!123"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        assert response.status_code == 201 or response.status_code == 200, \
            f"Expected status code 200 or 201 but got {response.status_code}"
        response_json = response.json()
        # Assert the response contains expected success indicators
        assert "id" in response_json, "Response JSON missing 'id' field"
        assert response_json.get("name") == payload["name"], "Tenant name in response does not match"
        assert response_json.get("email") == payload["email"], "Tenant email in response does not match"
        assert "password" not in response_json, "Password should not be returned in response"
    except requests.exceptions.RequestException as e:
        assert False, f"HTTP request failed: {e}"

test_post_tenants_register_should_register_new_tenant()
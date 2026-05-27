import requests

BASE_URL = "http://localhost:3001"
API_PATH = "/api/v1/accounts"
TIMEOUT = 30

def test_post_api_v1_accounts_should_create_account():
    url = f"{BASE_URL}{API_PATH}"
    
    # Sample valid payload to create a new enterprise account
    payload = {
        "name": "Test Enterprise Account",
        "description": "Test account created by automated test",
        "industry": "Technology",
        "website": "https://testenterprise.example.com",
        "address": {
            "street": "123 Test St",
            "city": "Testville",
            "state": "TS",
            "postalCode": "12345",
            "country": "Testland"
        },
        "contact": {
            "name": "Test Contact",
            "email": "contact@testenterprise.example.com",
            "phone": "+1234567890"
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        # Authorization header assumed required; placeholder for JWT token.
        # Replace 'your_jwt_token_here' with a valid token.
        "Authorization": "Bearer your_jwt_token_here"
    }
    
    created_account_id = None

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        assert response.status_code == 201 or response.status_code == 200, f"Unexpected status code: {response.status_code}"
        
        json_response = response.json()
        # Validate response contains expected keys
        assert "id" in json_response, "Response JSON missing 'id'"
        assert json_response.get("name") == payload["name"], "Account name in response does not match payload"
        assert "description" in json_response
        assert "industry" in json_response
        assert "website" in json_response
        assert "address" in json_response and isinstance(json_response["address"], dict)
        assert "contact" in json_response and isinstance(json_response["contact"], dict)
        
        created_account_id = json_response["id"]
    except requests.exceptions.RequestException as e:
        assert False, f"Request failed: {e}"
    finally:
        # Cleanup: delete the created account if ID is available
        if created_account_id:
            delete_url = f"{BASE_URL}{API_PATH}/{created_account_id}"
            try:
                del_response = requests.delete(delete_url, headers=headers, timeout=TIMEOUT)
                assert del_response.status_code == 204, f"Failed to delete account in cleanup, status code: {del_response.status_code}"
            except requests.exceptions.RequestException as e:
                assert False, f"Cleanup delete request failed: {e}"

test_post_api_v1_accounts_should_create_account()

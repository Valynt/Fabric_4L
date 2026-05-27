import requests
from requests.exceptions import RequestException

BASE_URL = "http://localhost:3001"
API_DRIVERS_ENDPOINT = "/api/v1/drivers"
TIMEOUT = 30

AUTH_TOKEN = "your_valid_auth_token_here"

def test_get_api_v1_drivers_account_id_should_return_driver_tree():
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Accept": "application/json"
    }

    account_id = None
    created_account_id = None

    try:
        create_account_url = f"{BASE_URL}/api/v1/accounts"
        new_account_payload = {
            "name": "Test Account for Driver Tree"
        }
        response = requests.post(create_account_url, json=new_account_payload, headers=headers, timeout=TIMEOUT)
        assert response.status_code == 201, f"Account creation failed: {response.text}"
        account_data = response.json()
        created_account_id = account_data.get("id")
        assert created_account_id is not None, "Account ID missing in creation response"

        account_id = created_account_id

        driver_tree_url = f"{BASE_URL}{API_DRIVERS_ENDPOINT}/{account_id}"
        response = requests.get(driver_tree_url, headers=headers, timeout=TIMEOUT)
        assert response.status_code == 200, f"Failed to get driver tree: {response.text}"
        driver_tree_data = response.json()
        assert isinstance(driver_tree_data, dict), "Driver tree response is not a JSON object"
        assert "id" in driver_tree_data, "Driver tree data missing 'id'"
        assert driver_tree_data.get("accountId", None) == account_id, "Driver tree accountId mismatch"
        assert "nodes" in driver_tree_data and isinstance(driver_tree_data["nodes"], list), "Driver tree missing nodes list"

    except RequestException as e:
        assert False, f"HTTP Request failed: {str(e)}"
    finally:
        if created_account_id:
            try:
                delete_account_url = f"{BASE_URL}/api/v1/accounts/{created_account_id}"
                del_response = requests.delete(delete_account_url, headers=headers, timeout=TIMEOUT)
                assert del_response.status_code in (200, 204), f"Failed to delete test account: {del_response.text}"
            except RequestException as e:
                print(f"Cleanup failed: {str(e)}")

test_get_api_v1_drivers_account_id_should_return_driver_tree()

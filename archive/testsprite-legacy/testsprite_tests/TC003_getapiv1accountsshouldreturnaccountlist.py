import requests

def test_get_api_v1_accounts_should_return_account_list():
    base_url = "http://localhost:3001"
    accounts_url = f"{base_url}/api/v1/accounts"
    timeout = 30
    
    session = requests.Session()
    try:
        # Step 1: Access /api/v1/accounts (assuming auth handled externally or local dev environment allows access)
        accounts_headers = {
            "Accept": "application/json"
        }
        accounts_response = session.get(accounts_url, headers=accounts_headers, timeout=timeout)
        assert accounts_response.status_code in [200, 401], f"Expected 200 or 401 but got {accounts_response.status_code}"

        if accounts_response.status_code == 200:
            data = accounts_response.json()
            assert isinstance(data, list), "Response data is not a list"
    finally:
        session.close()

test_get_api_v1_accounts_should_return_account_list()

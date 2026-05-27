import requests

BASE_URL = "http://localhost:3001"
TIMEOUT = 30

def test_get_api_v1_intelligence_signals_should_return_account_signals():
    session = requests.Session()
    try:
        # Step 1: Skip login due to no documented API POST /login in PRD
        # Step 2: Get list of accounts to fetch an accountId
        accounts_url = f"{BASE_URL}/api/v1/accounts"
        accounts_response = session.get(accounts_url, timeout=TIMEOUT)
        assert accounts_response.status_code == 200, f"Failed to get accounts: {accounts_response.text}"
        accounts_data = accounts_response.json()
        assert isinstance(accounts_data, list), "Accounts response is not a list"
        assert len(accounts_data) > 0, "No accounts found for the user"
        account_id = accounts_data[0].get("id")
        assert account_id is not None, "Account ID missing in accounts list"
        
        # Step 3: Call GET /api/v1/intelligence/signals without params (accountId not supported)
        signals_url = f"{BASE_URL}/api/v1/intelligence/signals"
        signals_response = session.get(signals_url, timeout=TIMEOUT)
        assert signals_response.status_code == 200, f"Failed to get intelligence signals: {signals_response.text}"

        signals_data = signals_response.json()
        assert signals_data is not None, "Signals data is None"
        assert isinstance(signals_data, list), "Signals data is not a list"

    finally:
        session.close()

test_get_api_v1_intelligence_signals_should_return_account_signals()

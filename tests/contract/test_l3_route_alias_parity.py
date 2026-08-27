import os

import requests

LAYER3_API_URL = os.getenv("LAYER3_API_URL", "http://localhost:8003").rstrip("/")
AUTH_HEADERS = {
    "X-Service-Auth": os.getenv("SERVICE_AUTH_SECRET", ""),
    "X-Tenant-ID": os.getenv(
        "RUNTIME_CONTRACT_TENANT_ID",
        "00000000-0000-4000-8000-000000000001",
    ),
}


def test_graphrag_aliases_match():
    payload = {"query": "q", "max_hops": 2, "max_results": 5}
    canonical = requests.post(
        f"{LAYER3_API_URL}/v1/query/graph", json=payload, headers=AUTH_HEADERS, timeout=30
    )
    alias = requests.post(
        f"{LAYER3_API_URL}/v1/graphrag", json=payload, headers=AUTH_HEADERS, timeout=30
    )
    assert canonical.status_code == alias.status_code == 200
    assert canonical.json()["query"] == alias.json()["query"]


def test_search_aliases_match():
    payload = {"query": "q", "search_type": "hybrid", "top_k": 3}
    canonical = requests.post(
        f"{LAYER3_API_URL}/v1/search/hybrid", json=payload, headers=AUTH_HEADERS, timeout=30
    )
    legacy = requests.post(
        f"{LAYER3_API_URL}/v1/search", json=payload, headers=AUTH_HEADERS, timeout=30
    )
    assert canonical.status_code == legacy.status_code == 200
    assert canonical.json()["search_type"] == legacy.json()["search_type"]

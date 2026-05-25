"""
Standalone webhook signature verification test.

Generates a test Svix signature and verifies it against the same logic
used in services/api/app/routers/clerk_webhooks.py.

Run: python scripts/test_webhook_signature.py
"""
import base64
import hashlib
import hmac
import json
import time


def _verify_svix_signature(*, secret: str, headers: dict[str, str], body: bytes) -> bool:
    """Port of the backend webhook signature verifier."""
    svix_id = headers.get("svix-id")
    svix_timestamp = headers.get("svix-timestamp")
    svix_signature = headers.get("svix-signature")
    if not (svix_id and svix_timestamp and svix_signature):
        raise ValueError("Missing Svix headers")

    ts = int(svix_timestamp)
    now = int(time.time())
    if abs(now - ts) > 300:
        raise ValueError("Timestamp expired (>5 min)")

    if secret.startswith("whsec_"):
        key = base64.b64decode(secret[len("whsec_"):])
    else:
        key = secret.encode()

    signed_payload = f"{svix_id}.{svix_timestamp}.".encode() + body
    expected = hmac.new(key, signed_payload, hashlib.sha256).digest()
    expected_sig = base64.b64encode(expected).decode()

    for sig_entry in svix_signature.split(" "):
        if "," not in sig_entry:
            continue
        version, value = sig_entry.split(",", 1)
        if version != "v1":
            continue
        if hmac.compare_digest(value.strip(), expected_sig):
            return True
    raise ValueError("Invalid signature")


def generate_svix_signature(*, secret: str, body: bytes) -> dict[str, str]:
    """Generate valid Svix headers for testing."""
    svix_id = f"msg_test_{int(time.time() * 1000)}"
    svix_timestamp = str(int(time.time()))

    if secret.startswith("whsec_"):
        key = base64.b64decode(secret[len("whsec_"):])
    else:
        key = secret.encode()

    signed_payload = f"{svix_id}.{svix_timestamp}.".encode() + body
    expected = hmac.new(key, signed_payload, hashlib.sha256).digest()
    expected_sig = base64.b64encode(expected).decode()

    return {
        "svix-id": svix_id,
        "svix-timestamp": svix_timestamp,
        "svix-signature": f"v1,{expected_sig}",
    }


def main():
    # Generate a test secret
    raw_key = hashlib.sha256(b"test-key").digest()
    test_secret = "whsec_" + base64.b64encode(raw_key).decode()
    print(f"Test secret: {test_secret[:20]}...")

    # Build a sample webhook payload
    payload = {
        "type": "user.created",
        "data": {
            "id": "user_test_001",
            "email_addresses": [{"id": "email_1", "email_address": "test@example.com"}],
            "primary_email_address_id": "email_1",
            "first_name": "Test",
            "last_name": "User",
        },
    }
    body = json.dumps(payload).encode("utf-8")

    # Generate valid headers
    headers = generate_svix_signature(secret=test_secret, body=body)
    print(f"svix-id: {headers['svix-id']}")
    print(f"svix-timestamp: {headers['svix-timestamp']}")
    print(f"svix-signature: {headers['svix-signature'][:40]}...")

    # Verify the signature
    try:
        _verify_svix_signature(secret=test_secret, headers=headers, body=body)
        print("\n[PASS] Signature verification PASSED")
    except ValueError as e:
        print(f"\n[FAIL] Signature verification FAILED: {e}")
        return 1

    # Test with wrong secret
    bad_secret = "whsec_" + base64.b64encode(b"wrong-key").decode()
    try:
        _verify_svix_signature(secret=bad_secret, headers=headers, body=body)
        print("[FAIL] Should have rejected bad secret")
        return 1
    except ValueError:
        print("[PASS] Correctly rejected bad secret")

    # Test with tampered body
    tampered_body = json.dumps({"type": "user.deleted"}).encode("utf-8")
    try:
        _verify_svix_signature(secret=test_secret, headers=headers, body=tampered_body)
        print("[FAIL] Should have rejected tampered body")
        return 1
    except ValueError:
        print("[PASS] Correctly rejected tampered body")

    # Test with expired timestamp
    old_headers = dict(headers)
    old_headers["svix-timestamp"] = str(int(time.time()) - 400)
    try:
        _verify_svix_signature(secret=test_secret, headers=old_headers, body=body)
        print("[FAIL] Should have rejected expired timestamp")
        return 1
    except ValueError:
        print("[PASS] Correctly rejected expired timestamp")

    print("\n[OK] All webhook signature tests passed")
    return 0


if __name__ == "__main__":
    exit(main())

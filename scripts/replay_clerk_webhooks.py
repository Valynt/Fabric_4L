#!/usr/bin/env python3
"""Clerk Webhook Dead-Letter Queue (DLQ) Replay Tool.

Allows operations engineers to inspect, filter, and replay failed Clerk
webhook events from the DLQ endpoint or a saved JSON export.

Usage:
    # List unhandled DLQ events
    python scripts/replay_clerk_webhooks.py list --url http://localhost:8000

    # Replay all DLQ events to the webhook endpoint
    python scripts/replay_clerk_webhooks.py replay --url http://localhost:8000 --secret whsec_...

    # Replay from a local export file
    python scripts/replay_clerk_webhooks.py replay --file dlq_export.json --url http://localhost:8000 --secret whsec_...
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import logging
import os
import sys
import time
from typing import Any

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("clerk_dlq_replay")


def sign_svix_payload(secret: str, event_id: str, timestamp: int, payload_bytes: bytes) -> str:
    """Generate a valid Svix v1 signature for webhook replay."""
    if secret.startswith("whsec_"):
        key = base64.b64decode(secret[len("whsec_") :])
    else:
        key = secret.encode("utf-8")

    signed_payload = f"{event_id}.{timestamp}.".encode("utf-8") + payload_bytes
    sig = base64.b64encode(hmac.new(key, signed_payload, hashlib.sha256).digest()).decode("utf-8")
    return f"v1,{sig}"


def list_dlq(base_url: str) -> list[dict[str, Any]]:
    """Fetch DLQ records from the API gateway."""
    url = f"{base_url.rstrip('/')}/internal/webhooks/clerk/dlq"
    try:
        resp = httpx.get(url, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        records = data.get("records", [])
        logger.info("Found %d total DLQ records (%d unresolved)", len(records), data.get("unresolved_count", 0))
        for r in records:
            logger.info("  [DLQ ID: %s] event_id=%s type=%s reason=%s retry_count=%d",
                        r.get("id"), r.get("event_id"), r.get("event_type"), r.get("error_reason"), r.get("retry_count", 0))
        return records
    except Exception as exc:
        logger.error("Failed to fetch DLQ records from %s: %s", url, exc)
        return []


def replay_event(base_url: str, secret: str, record: dict[str, Any]) -> bool:
    """Replay a single DLQ event to the webhook receiver."""
    url = f"{base_url.rstrip('/')}/internal/webhooks/clerk"
    event_id = record.get("event_id") or f"replay_{int(time.time())}"
    payload = record.get("payload", {})
    payload_bytes = json.dumps(payload).encode("utf-8")
    ts = int(time.time())
    sig = sign_svix_payload(secret, event_id, ts, payload_bytes)

    headers = {
        "Content-Type": "application/json",
        "svix-id": event_id,
        "svix-timestamp": str(ts),
        "svix-signature": sig,
    }

    try:
        resp = httpx.post(url, content=payload_bytes, headers=headers, timeout=15.0)
        if resp.status_code in (200, 204):
            logger.info("Successfully replayed event %s (type=%s)", event_id, record.get("event_type"))
            return True
        logger.warning("Replay of event %s returned status %d: %s", event_id, resp.status_code, resp.text)
        return False
    except Exception as exc:
        logger.error("Error replaying event %s: %s", event_id, exc)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Clerk Webhook DLQ Replay CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List DLQ records")
    list_parser.add_argument("--url", default=os.getenv("FABRIC_API_URL", "http://localhost:8000"), help="Base API URL")

    replay_parser = subparsers.add_parser("replay", help="Replay DLQ records")
    replay_parser.add_argument("--url", default=os.getenv("FABRIC_API_URL", "http://localhost:8000"), help="Base API URL")
    replay_parser.add_argument("--secret", default=os.getenv("CLERK_WEBHOOK_SECRET", ""), help="Clerk webhook Svix secret")
    replay_parser.add_argument("--file", help="Path to local DLQ JSON file export to replay")
    replay_parser.add_argument("--event-id", help="Filter replay to specific event_id")

    args = parser.parse_args()

    if args.command == "list":
        list_dlq(args.url)
        return 0

    if args.command == "replay":
        secret = args.secret or os.getenv("CLERK_WEBHOOK_SECRET")
        if not secret:
            logger.error("CLERK_WEBHOOK_SECRET is required to generate replay signatures.")
            return 1

        records = []
        if args.file:
            with open(args.file, "r", encoding="utf-8") as f:
                records = json.load(f)
        else:
            records = list_dlq(args.url)

        if args.event_id:
            records = [r for r in records if r.get("event_id") == args.event_id]

        if not records:
            logger.info("No records to replay.")
            return 0

        success_count = 0
        for r in records:
            if replay_event(args.url, secret, r):
                success_count += 1

        logger.info("Replay completed: %d/%d succeeded.", success_count, len(records))
        return 0 if success_count == len(records) else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

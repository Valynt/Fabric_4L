#!/usr/bin/env python3
"""Verify that public /api/v1 requests reach the JSON API gateway, not the SPA."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ALLOWED_STATUSES = {200, 401, 403, 404}
DEFAULT_PATHS = ("/api/v1/auth/health", "/api/v1/accounts/routing-smoke-nonexistent")


@dataclass(frozen=True)
class ProbeResult:
    path: str
    status: int
    content_type: str


def probe(
    base_url: str,
    path: str,
    timeout: float = 10.0,
    *,
    authorization: str | None = None,
    cookie: str | None = None,
) -> ProbeResult:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    headers = {"Accept": "application/json"}
    if authorization:
        headers["Authorization"] = authorization
    if cookie:
        headers["Cookie"] = cookie
    request = Request(url, headers=headers)
    try:
        response = urlopen(request, timeout=timeout)
    except HTTPError as exc:
        response = exc
    except URLError as exc:
        raise RuntimeError(f"{path}: request failed: {exc.reason}") from exc

    with response:
        status = response.status
        content_type = response.headers.get_content_type().lower()
        body = response.read().decode("utf-8", errors="replace")

    if status not in ALLOWED_STATUSES:
        raise RuntimeError(f"{path}: unexpected HTTP status {status}")
    if content_type != "application/json" and not content_type.endswith("+json"):
        raise RuntimeError(f"{path}: expected JSON Content-Type, got {content_type!r}")
    if "<!doctype html" in body.lower() or "<html" in body.lower():
        raise RuntimeError(f"{path}: API request returned frontend HTML")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{path}: response body is not valid JSON") from exc
    if not isinstance(payload, (dict, list)):
        raise RuntimeError(f"{path}: expected a structured JSON response")

    return ProbeResult(path=path, status=status, content_type=content_type)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Public application origin")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--path", action="append", dest="paths")
    args = parser.parse_args()
    authorization = os.getenv("EDGE_SMOKE_AUTHORIZATION")
    cookie = os.getenv("EDGE_SMOKE_COOKIE")

    try:
        results = [
            probe(
                args.base_url,
                path,
                args.timeout,
                authorization=authorization,
                cookie=cookie,
            )
            for path in (args.paths or DEFAULT_PATHS)
        ]
    except RuntimeError as exc:
        print(f"production-edge-smoke: FAIL: {exc}", file=sys.stderr)
        return 1

    for result in results:
        print(
            f"production-edge-smoke: PASS: {result.path} -> {result.status} {result.content_type}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

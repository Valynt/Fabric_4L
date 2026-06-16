# Shared Auth-Bypass Hardening & Clerk Webhook Rate-Limiting Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the persistent auth-bypass attack surface and add IP-based rate limiting to the unauthenticated Clerk webhook endpoint.

**Architecture:** Consolidate the four legacy bypass flags into one canonical check that fails closed outside `ENVIRONMENT=local`. Add a small, dependency-light IP rate-limiter that works even when no tenant context exists and handles `X-Forwarded-For` safely.

**Tech Stack:** Python 3.12, FastAPI, Pydantic Settings, `limits` (already used by TenantRateLimitMiddleware).

---

## Task 1: Canonical auth-bypass flag helpers

**Files:**
- Modify: `packages/shared/src/value_fabric/shared/identity/auth_mode.py`
- Modify: `packages/shared/src/value_fabric/shared/startup/validator.py`
- Modify: `packages/shared/src/value_fabric/shared/security/config.py`
- Test: `packages/shared/tests/test_auth_bypass_flags.py` (create)

- [ ] **Step 1: Write the failing test**

Create `packages/shared/tests/test_auth_bypass_flags.py`:

```python
import os
import pytest

from value_fabric.shared.identity.auth_mode import (
    _bypass_flags_are_set,
    _raise_if_bypass_in_nonlocal_env,
)


@pytest.mark.parametrize("flag", [
    "DEV_AUTH_BYPASS",
    "ALLOW_INSECURE_DEV_AUTH_BYPASS",
    "ALLOW_DEV_AUTH_BYPASS",
    "AUTH_BYPASS_ENABLED",
])
def test_bypass_flag_detected_when_set(flag, monkeypatch):
    monkeypatch.setenv(flag, "true")
    assert _bypass_flags_are_set() == {flag}


def test_no_bypass_flags_detected_by_default(monkeypatch):
    for flag in ["DEV_AUTH_BYPASS", "ALLOW_INSECURE_DEV_AUTH_BYPASS", "ALLOW_DEV_AUTH_BYPASS", "AUTH_BYPASS_ENABLED"]:
        monkeypatch.delenv(flag, raising=False)
    assert _bypass_flags_are_set() == set()


def test_nonlocal_env_raises_when_bypass_set(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    with pytest.raises(RuntimeError, match="auth bypass flags"):
        _raise_if_bypass_in_nonlocal_env(service_name="test-service")


def test_local_env_allows_bypass_with_warning(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("DEV_AUTH_BYPASS", "true")
    # Should not raise
    _raise_if_bypass_in_nonlocal_env(service_name="test-service")
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
cd /home/bunnyshell/Fabric_4L
python -m pytest packages/shared/tests/test_auth_bypass_flags.py -v
```

Expected: failures because `_bypass_flags_are_set` and `_raise_if_bypass_in_nonlocal_env` do not exist.

- [ ] **Step 3: Implement the canonical helpers in `auth_mode.py`**

Modify `packages/shared/src/value_fabric/shared/identity/auth_mode.py` (replace the `_warn_if_legacy_flags` body and add the new helpers):

```python
import os
from typing import Set

logger = logging.getLogger(__name__)

_BYPASS_FLAGS = (
    "DEV_AUTH_BYPASS",
    "ALLOW_INSECURE_DEV_AUTH_BYPASS",
    "ALLOW_DEV_AUTH_BYPASS",
    "AUTH_BYPASS_ENABLED",
)

_TRUE_VALUES = {"true", "1", "yes", "on", "i_understand_risk"}
_EXPLICIT_LOCAL_ENVIRONMENTS = frozenset({"local", "development", "dev", "test", "testing", "ci"})


def _flag_value_is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in _TRUE_VALUES


def _bypass_flags_are_set() -> Set[str]:
    """Return the set of auth-bypass env flags that are currently enabled."""
    active: Set[str] = set()
    for flag in _BYPASS_FLAGS:
        if _flag_value_is_truthy(os.getenv(flag)):
            active.add(flag)
    return active


def _raise_if_bypass_in_nonlocal_env(*, service_name: str) -> None:
    """Fail closed when any auth-bypass flag is set outside an explicit local/test environment."""
    env = os.getenv("ENVIRONMENT", "production").strip().lower()
    if env in _EXPLICIT_LOCAL_ENVIRONMENTS:
        active = _bypass_flags_are_set()
        if active:
            logger.warning(
                "Auth bypass flags are enabled in %s environment for service %s: %s. "
                "These flags are ignored by the platform but should be removed before deploying to production.",
                env,
                service_name,
                ", ".join(sorted(active)),
            )
        return

    active = _bypass_flags_are_set()
    if active:
        joined = ", ".join(sorted(active))
        raise RuntimeError(
            f"{service_name} startup rejected: production-like environment cannot enable auth bypass flags: {joined}."
        )


def _warn_if_legacy_flags() -> None:
    """Keep the existing warning behavior for backwards compatibility."""
    active = _bypass_flags_are_set()
    for flag in active:
        logger.warning(
            "Legacy auth bypass flag %s is set but dev auth bypass has been "
            "permanently removed from the platform. Remove this flag from your environment.",
            flag,
        )
```

- [ ] **Step 4: Refactor `startup/validator.py` to use the helper**

Modify `packages/shared/src/value_fabric/shared/startup/validator.py`:

```python
from value_fabric.shared.identity.auth_mode import _bypass_flags_are_set, _raise_if_bypass_in_nonlocal_env


def reject_insecure_bypass_in_production(*, service_name: str, settings: Any | None = None) -> None:
    """Fail closed when production-like runtimes enable auth bypass toggles."""
    # First check: if settings explicitly say local/test, allow but warn.
    if settings is not None and hasattr(settings, "is_production_like"):
        if not bool(getattr(settings, "is_production_like")):
            _raise_if_bypass_in_nonlocal_env(service_name=service_name)
            return
    elif settings is not None and hasattr(settings, "effective_environment"):
        env = str(getattr(settings, "effective_environment")).strip().lower()
        if env in _EXPLICIT_LOCAL_TEST_ENVIRONMENTS:
            _raise_if_bypass_in_nonlocal_env(service_name=service_name)
            return
    elif settings is not None and hasattr(settings, "environment"):
        env = str(getattr(settings, "environment")).strip().lower()
        if env in _EXPLICIT_LOCAL_TEST_ENVIRONMENTS:
            _raise_if_bypass_in_nonlocal_env(service_name=service_name)
            return

    # No local/test signal from settings; use runtime ENVIRONMENT.
    _raise_if_bypass_in_nonlocal_env(service_name=service_name)
```

(Keep `_BYPASS_ENV_FLAGS`, `_BYPASS_SETTINGS_FIELDS`, `_flag_is_truthy`, and `_is_explicit_local_or_test_environment` for compatibility, but the new helper drives the fatal decision.)

- [ ] **Step 5: Refactor `security/config.py` to use the helper**

In `packages/shared/src/value_fabric/shared/security/config.py`, replace the inline bypass-flag checks in `validate_authentication()` (lines 202–241) with:

```python
from value_fabric.shared.identity.auth_mode import _bypass_flags_are_set, _raise_if_bypass_in_nonlocal_env

# ... inside validate_authentication() ...

# Auth bypass flags must never be enabled in production-like envs.
try:
    _raise_if_bypass_in_nonlocal_env(service_name="ProductionSafetyValidator")
except RuntimeError as exc:
    self.errors.append(str(exc))

# Also keep the explicit per-flag checks as warnings/errors in development.
active_flags = _bypass_flags_are_set()
if active_flags:
    if self.environment == "development":
        warnings.warn(
            f"Auth bypass flags are enabled in development: {', '.join(sorted(active_flags))}",
            RuntimeWarning,
            stacklevel=2,
        )
        self.errors.append(
            f"Auth bypass flags are enabled in development: {', '.join(sorted(active_flags))}. "
            "Remove them before deploying to production-like environments."
        )
```

- [ ] **Step 6: Update `.env.example` comments**

Find the bypass-flag entries in `.env.example` and ensure each comment reads:

```bash
# LOCAL DEV ONLY — will fail startup in production
# DEV_AUTH_BYPASS=true
```

If the flags are not present, append them at the bottom of the auth section:

```bash
# LOCAL DEV ONLY — will fail startup in production
# DEV_AUTH_BYPASS=false
# ALLOW_DEV_AUTH_BYPASS=false
# AUTH_BYPASS_ENABLED=false
# ALLOW_INSECURE_DEV_AUTH_BYPASS=false
```

- [ ] **Step 7: Run the tests**

```bash
python -m pytest packages/shared/tests/test_auth_bypass_flags.py -v
```

Expected: PASS.

- [ ] **Step 8: Run the broader shared tests**

```bash
python -m pytest packages/shared/tests -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add packages/shared/src/value_fabric/shared/identity/auth_mode.py \
        packages/shared/src/value_fabric/shared/startup/validator.py \
        packages/shared/src/value_fabric/shared/security/config.py \
        packages/shared/tests/test_auth_bypass_flags.py \
        .env.example
git commit -m "security: consolidate auth-bypass flag checks and fail closed outside local"
```

---

## Task 2: IP-based rate limiting for Clerk webhooks

**Files:**
- Create: `packages/shared/src/value_fabric/shared/rate_limiting/ip_limiter.py`
- Modify: `services/api/app/routers/clerk_webhooks.py`
- Modify: `packages/shared/src/value_fabric/shared/rate_limiting/middleware.py` (optional: remove the unconditional tenant-context skip if a global IP limit is configured)
- Test: `services/api/tests/test_clerk_webhook_rate_limit.py` (create)

- [ ] **Step 1: Write the failing test**

Create `services/api/tests/test_clerk_webhook_rate_limit.py`:

```python
import os
import time
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from value_fabric.shared.rate_limiting.ip_limiter import (
    IPRateLimitDependency,
    get_client_ip,
)


@pytest.fixture
def app_with_limit():
    app = FastAPI()
    limiter = IPRateLimitDependency(requests_per_minute=2)

    @app.post("/clerk")
    async def clerk(request: Request, _=limiter):
        return {"ok": True}

    return app


def test_client_ip_prefers_first_non_private_x_forwarded_for():
    request = Request(scope={
        "type": "http",
        "headers": [(b"x-forwarded-for", b"203.0.113.1, 10.0.0.1, 192.168.1.1")],
        "client": ("127.0.0.1", 12345),
    })
    assert get_client_ip(request) == "203.0.113.1"


def test_rate_limit_allows_under_threshold(app_with_limit):
    client = TestClient(app_with_limit)
    for _ in range(2):
        r = client.post("/clerk", headers={"X-Forwarded-For": "1.2.3.4"})
        assert r.status_code == 200


def test_rate_limit_blocks_over_threshold(app_with_limit):
    client = TestClient(app_with_limit)
    for _ in range(2):
        client.post("/clerk", headers={"X-Forwarded-For": "1.2.3.4"})
    r = client.post("/clerk", headers={"X-Forwarded-For": "1.2.3.4"})
    assert r.status_code == 429


def test_rate_limit_tracks_different_ips_separately(app_with_limit):
    client = TestClient(app_with_limit)
    for ip in ["1.2.3.4", "5.6.7.8"]:
        r = client.post("/clerk", headers={"X-Forwarded-For": ip})
        assert r.status_code == 200
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
python -m pytest services/api/tests/test_clerk_webhook_rate_limit.py -v
```

Expected: failures because `ip_limiter.py` does not exist.

- [ ] **Step 3: Implement the IP rate limiter**

Create `packages/shared/src/value_fabric/shared/rate_limiting/ip_limiter.py`:

```python
from __future__ import annotations

"""IP-based rate limiting for unauthenticated endpoints.

This intentionally does not depend on tenant context, so it can protect
webhooks and other anonymous paths.
"""

import ipaddress
from typing import Any

from fastapi import HTTPException, Request, status
from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter


_DEFAULT_TRUSTED_PROXY_HOPS = int(os.getenv("RATE_LIMIT_TRUSTED_PROXY_HOPS", "0"))


class IPRateLimitDependency:
    """FastAPI dependency that rate-limits by client IP.

    Uses the first non-private IP in X-Forwarded-For, falling back to
    request.client.host. The number of trusted proxy hops is configurable
    via RATE_LIMIT_TRUSTED_PROXY_HOPS.
    """

    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self._storage = MemoryStorage()
        self._limiter = MovingWindowRateLimiter(self._storage)
        self._limit = parse(f"{requests_per_minute} per minute")

    async def __call__(self, request: Request) -> None:
        client_ip = get_client_ip(request)
        if not self._limiter.hit(self._limit, client_ip, "global"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down.",
            )


def _is_private_ip(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


def get_client_ip(request: Request, trusted_proxy_hops: int | None = None) -> str:
    """Return the most trustworthy client IP for rate limiting.

    1. Parse X-Forwarded-For (right-most = nearest proxy).
    2. Skip `trusted_proxy_hops` entries from the right.
    3. Return the first remaining non-private IP from the left, or fall back
       to the immediate peer address.
    """
    hops = _DEFAULT_TRUSTED_PROXY_HOPS if trusted_proxy_hops is None else trusted_proxy_hops
    forwarded = request.headers.get("x-forwarded-for", "")
    candidates = [part.strip() for part in forwarded.split(",") if part.strip()]

    # Drop untrusted proxies from the right (the ones closest to the app).
    if candidates and hops > 0:
        candidates = candidates[:-hops]

    for candidate in candidates:
        if not _is_private_ip(candidate):
            return candidate

    # If every forwarded entry is private, fall back to the direct peer.
    peer = request.client
    return peer.host if peer and peer.host else "unknown"
```

Add the missing `import os` at the top of the file:

```python
import os
```

- [ ] **Step 4: Apply the rate limiter to the Clerk webhook**

Modify `services/api/app/routers/clerk_webhooks.py`:

```python
from value_fabric.shared.rate_limiting.ip_limiter import IPRateLimitDependency

_clerk_ip_limiter = IPRateLimitDependency(
    requests_per_minute=int(os.getenv("CLERK_WEBHOOK_RATE_LIMIT_PER_MINUTE", "30"))
)


@router.post("/clerk", status_code=status.HTTP_204_NO_CONTENT)
async def clerk_webhook(request: Request, _limit: None = Depends(_clerk_ip_limiter)) -> None:
    ...
```

Make sure `Depends` is imported from `fastapi` at the top of the file:

```python
from fastapi import APIRouter, Depends, HTTPException, Request, status
```

- [ ] **Step 5: Document the new env var in `.env.example`**

Append to `.env.example` in the Clerk/auth section:

```bash
# Clerk webhook IP rate limit (requests per minute). Increase only if Clerk docs recommend higher.
CLERK_WEBHOOK_RATE_LIMIT_PER_MINUTE=30
```

- [ ] **Step 6: Run the tests**

```bash
python -m pytest services/api/tests/test_clerk_webhook_rate_limit.py -v
```

Expected: PASS.

- [ ] **Step 7: Run API service tests**

```bash
python -m pytest services/api/tests -v
```

Expected: PASS (or no new failures).

- [ ] **Step 8: Commit**

```bash
git add packages/shared/src/value_fabric/shared/rate_limiting/ip_limiter.py \
        services/api/app/routers/clerk_webhooks.py \
        services/api/tests/test_clerk_webhook_rate_limit.py \
        .env.example
git commit -m "security: add IP-based rate limiting to Clerk webhook endpoint"
```

---

## Task 3: Final verification for this plan

- [ ] Run the shared + API test suites together:

```bash
python -m pytest packages/shared/tests services/api/tests -v
```

Expected: PASS.

- [ ] Commit any test-env fixes:

```bash
git commit -m "test: update shared/api test env for auth-bypass and rate-limit changes"
```

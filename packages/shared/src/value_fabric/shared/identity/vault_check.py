"""Async Vault health and secret-access verification helpers."""

import asyncio
import logging
import os
import time
from collections import Counter
from typing import Any, List
from urllib.parse import urlparse

import httpx

from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.security.config import is_production, is_staging

logger = logging.getLogger(__name__)

# In-memory cache for Vault secrets to avoid repeated lookups
_vault_secret_cache: dict[str, tuple[str, float]] = {}
_VAULT_CACHE_TTL_SECONDS = 300  # 5 minutes

# Transport policy
_VAULT_CONNECT_TIMEOUT_SECONDS = 3.0
_VAULT_READ_TIMEOUT_SECONDS = 5.0
_VAULT_MAX_RETRIES = 3
_VAULT_BACKOFF_SECONDS = 0.25

# Structured in-process metrics sink
_vault_metrics: Counter[str] = Counter()


class VaultConfigurationError(RuntimeError):
    """Raised when Vault transport/configuration is invalid for environment."""


class VaultSecretResolutionError(RuntimeError):
    """Raised when a critical Vault secret cannot be resolved."""


def _is_production_like() -> bool:
    return is_production() or is_staging()


def _record_metric(event: str, **dimensions: str) -> None:
    key = event
    if dimensions:
        suffix = ",".join(f"{k}={v}" for k, v in sorted(dimensions.items()))
        key = f"{event}|{suffix}"
    _vault_metrics[key] += 1


def _validate_vault_transport(vault_addr: str) -> None:
    parsed = urlparse(vault_addr)
    scheme = (parsed.scheme or "").lower()
    if _is_production_like() and scheme != "https":
        _record_metric("vault.transport.rejected", environment="prod_like", scheme=scheme or "missing")
        raise VaultConfigurationError(
            "VAULT_ADDR must use https in production/staging environments"
        )


def _parse_vault_ref(ref: str) -> tuple[str, str] | None:
    if not ref.startswith("vault:"):
        return None
    path_part = ref[6:]
    if "#" in path_part:
        path, key = path_part.split("#", 1)
    elif "." in path_part and "/" not in path_part.split(".")[-1]:
        path, key = path_part.rsplit(".", 1)
    else:
        path = path_part
        key = "value"
    return (path.lstrip("/"), key)


async def _vault_get_with_retry(client: httpx.AsyncClient, url: str, headers: dict[str, str]) -> httpx.Response | None:
    last_exc: Exception | None = None
    for attempt in range(1, _VAULT_MAX_RETRIES + 1):
        try:
            response = await client.get(url, headers=headers)
            _record_metric("vault.http.request", status=str(response.status_code), attempt=str(attempt))
            return response
        except (httpx.HTTPError, OSError) as exc:
            last_exc = exc
            _record_metric("vault.http.retry", attempt=str(attempt), error=exc.__class__.__name__)
            if attempt < _VAULT_MAX_RETRIES:
                await asyncio.sleep(_VAULT_BACKOFF_SECONDS * attempt)
    if last_exc:
        logger.warning("Vault request failed after retries", extra={"url": url, "error": str(last_exc)})
        _record_metric("vault.http.failed", error=last_exc.__class__.__name__)
    return None


async def resolve_vault_secret(ref: str) -> str | None:
    parsed = _parse_vault_ref(ref)
    if parsed is None:
        return None

    path, key = parsed
    cache_key = f"{path}#{key}"
    critical = _is_production_like()

    vault_addr = os.getenv("VAULT_ADDR", "")
    token = os.getenv("VAULT_TOKEN", "")

    if vault_addr:
        _validate_vault_transport(vault_addr)

    cached = _vault_secret_cache.get(cache_key)
    if cached:
        value, cached_at = cached
        if time.time() - cached_at < _VAULT_CACHE_TTL_SECONDS:
            _record_metric("vault.cache.hit")
            return value

    if not vault_addr or not token:
        _record_metric("vault.config.missing", missing="addr_or_token")
        if critical:
            raise VaultSecretResolutionError("Missing VAULT_ADDR or VAULT_TOKEN in production/staging")
        return None

    timeout = httpx.Timeout(connect=_VAULT_CONNECT_TIMEOUT_SECONDS, read=_VAULT_READ_TIMEOUT_SECONDS, write=_VAULT_READ_TIMEOUT_SECONDS, pool=_VAULT_READ_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout) as client:
        headers = {"X-Vault-Token": token}
        url = f"{vault_addr.rstrip('/')}/v1/{path}"
        resp = await _vault_get_with_retry(client, url, headers)
        if resp is None:
            if critical:
                raise VaultSecretResolutionError(f"Unable to reach Vault for secret ref: {ref}")
            return None

        if resp.status_code != 200:
            _record_metric("vault.secret.http_error", status=str(resp.status_code))
            if critical:
                raise VaultSecretResolutionError(
                    f"Vault returned HTTP {resp.status_code} for secret ref: {ref}"
                )
            return None

        data = resp.json()
        secret_data = data.get("data", {}).get("data", {})
        value = secret_data.get(key)

        if value:
            _vault_secret_cache[cache_key] = (value, time.time())
            _record_metric("vault.secret.resolved")
            return value

        _record_metric("vault.secret.missing_key", key=key)
        if critical:
            raise VaultSecretResolutionError(f"Secret key '{key}' missing for ref: {ref}")
        return None


def clear_vault_cache() -> None:
    _vault_secret_cache.clear()


async def check_vault_health(vault_addr: str) -> bool:
    token = os.getenv("VAULT_TOKEN", "")
    headers = {"X-Vault-Token": token} if token else {}
    try:
        _validate_vault_transport(vault_addr)
    except VaultConfigurationError:
        return False

    timeout = httpx.Timeout(connect=_VAULT_CONNECT_TIMEOUT_SECONDS, read=_VAULT_READ_TIMEOUT_SECONDS, write=_VAULT_READ_TIMEOUT_SECONDS, pool=_VAULT_READ_TIMEOUT_SECONDS)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{vault_addr.rstrip('/')}/v1/sys/health", headers=headers)
            return resp.status_code in (200, 429, 473)
    except Exception:
        return False


is_vault_healthy = check_vault_health


async def verify_secret_access(vault_addr: str, paths: List[str]) -> bool:
    token = os.getenv("VAULT_TOKEN", "")
    if not token:
        return False
    try:
        _validate_vault_transport(vault_addr)
    except VaultConfigurationError:
        return False

    headers = {"X-Vault-Token": token}
    timeout = httpx.Timeout(connect=_VAULT_CONNECT_TIMEOUT_SECONDS, read=_VAULT_READ_TIMEOUT_SECONDS, write=_VAULT_READ_TIMEOUT_SECONDS, pool=_VAULT_READ_TIMEOUT_SECONDS)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for path in paths:
                url = f"{vault_addr.rstrip('/')}/v1/{path.lstrip('/')}"
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    return False
            return True
    except Exception:
        return False


class get_vault_healthResult(TypedDictModel):
    error: Any
    initialized: Any | None = None
    reachable: bool
    sealed: Any | None = None
    standby: Any | None = None
    status: str
    version: Any | None = None


async def get_vault_health() -> get_vault_healthResult:
    vault_addr = os.environ.get("VAULT_ADDR", "http://localhost:8200")
    try:
        _validate_vault_transport(vault_addr)
    except VaultConfigurationError as exc:
        return get_vault_healthResult.model_validate(
            {"reachable": False, "status": "unreachable", "error": type(exc).__name__}
        )

    timeout = httpx.Timeout(connect=_VAULT_CONNECT_TIMEOUT_SECONDS, read=_VAULT_READ_TIMEOUT_SECONDS, write=_VAULT_READ_TIMEOUT_SECONDS, pool=_VAULT_READ_TIMEOUT_SECONDS)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{vault_addr.rstrip('/')}/v1/sys/health")
            if resp.status_code == 200:
                data = resp.json()
                return get_vault_healthResult.model_validate(
                    {
                        "reachable": True,
                        "status": "healthy",
                        "initialized": data.get("initialized"),
                        "sealed": data.get("sealed"),
                        "standby": data.get("standby"),
                        "version": data.get("version"),
                        "error": None,
                    }
                )
            return get_vault_healthResult.model_validate(
                {"reachable": False, "status": "unreachable", "error": f"HTTP {resp.status_code}"}
            )
    except Exception as exc:
        return get_vault_healthResult.model_validate(
            {"reachable": False, "status": "unreachable", "error": type(exc).__name__}
        )

"""
Layer 3 Knowledge Graph integration client for Layer 5.

Responsibilities:
  - Sync approved TruthObjects to the Layer 3 KG as :GroundTruth nodes
  - Link GroundTruth nodes to existing :Capability / :Outcome / :ValueDriver nodes
  - Query Layer 3 for entity context when creating truth objects
  - Handle connection failures gracefully (Layer 5 is authoritative; KG sync is best-effort)

Layer 3 API base URL is configured via LAYER3_BASE_URL env var (default: http://localhost:8003).
"""

import asyncio
import json
import logging
from typing import Any
from uuid import UUID

import httpx
from pydantic import ValidationError

from metrics.prometheus_metrics import get_metrics

from metrics.prometheus_metrics import get_metrics

from ..config import get_settings

logger = logging.getLogger(__name__)

ERR_LAYER3_HTTP_CLIENT = "L5_LAYER3_HTTP_CLIENT_ERROR"
ERR_LAYER3_TIMEOUT = "L5_LAYER3_TIMEOUT"
ERR_LAYER3_CONTRACT_INVALID = "L5_LAYER3_CONTRACT_INVALID"
ERR_LAYER3_POLICY_DENIED = "L5_LAYER3_POLICY_DENIED"
ERR_LAYER3_TENANT_MISMATCH = "L5_LAYER3_TENANT_MISMATCH"
ERR_LAYER3_SERVER_ERROR = "L5_LAYER3_SERVER_ERROR"


class Layer3ClientError(RuntimeError):
    """Base error for Layer 3 sync failures that need explicit API handling."""

    error_code = ERR_LAYER3_HTTP_CLIENT
    status_code = 502

    def __init__(
        self,
        message: str,
        *,
        tenant_id: UUID | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.tenant_id = tenant_id
        self.request_id = request_id


class Layer3PolicyDeniedError(Layer3ClientError):
    """Raised when Layer 3 rejects a request for auth, policy, or governance reasons."""

    error_code = ERR_LAYER3_POLICY_DENIED
    status_code = 403


class Layer3TenantMismatchError(Layer3ClientError):
    """Raised when Layer 3 returns data scoped to a different tenant."""

    error_code = ERR_LAYER3_TENANT_MISMATCH
    status_code = 403


class Layer3ContractValidationError(Layer3ClientError):
    """Raised when Layer 3 returns a malformed or incompatible response contract."""

    error_code = ERR_LAYER3_CONTRACT_INVALID
    status_code = 502


def _log_context(
    *,
    tenant_id: UUID | None,
    truth_object_id: UUID | None = None,
    request_id: str | None = None,
    error_code: str,
    transition: str | None = None,
    sync_status: str | None = None,
    attempt: int | None = None,
    status_code: int | None = None,
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "tenant_id": str(tenant_id) if tenant_id is not None else None,
        "truth_object_id": (
            str(truth_object_id) if truth_object_id is not None else None
        ),
        "error_code": error_code,
        "transition": transition,
        "sync_status": sync_status,
        "attempt": attempt,
        "upstream_status_code": status_code,
    }


# ---------------------------------------------------------------------------
# Node type mapping
# ---------------------------------------------------------------------------

# Maps Layer 5 ClaimType → Layer 3 node label for relationship creation
CLAIM_TYPE_TO_KG_LABEL: dict[str, str] = {
    "cost_savings_baseline": "ValueDriver",
    "revenue_impact": "ValueDriver",
    "efficiency_gain": "ValueDriver",
    "risk_reduction": "ValueDriver",
    "compliance_requirement": "Outcome",
    "customer_outcome": "Outcome",
    "technical_capability": "Capability",
    "market_benchmark": "ValueDriver",
    "persona_pain_point": "Persona",
    "value_driver_metric": "ValueDriver",
    "other": "Entity",
}


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class Layer3Client:
    """
    Async HTTP client for Layer 3 Knowledge Graph API.

    All methods return None on failure and log a warning — Layer 5 must
    remain operational even when Layer 3 is unavailable.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._base_url = self._settings.layer3_base_url.rstrip("/")
        self._timeout = self._settings.layer3_timeout_seconds
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._settings.layer3_api_key:
            self._headers["Authorization"] = f"Bearer {self._settings.layer3_api_key}"
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """Return (or lazily create) the persistent HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                headers=self._headers,
            )
        return self._client

    async def close(self) -> None:
        """Close the persistent HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def ping(self) -> bool:
        """Return True if Layer 3 is reachable."""
        try:
            client = self._get_client()
            resp = await client.get(f"{self._base_url}/health", headers=self._headers)
            return resp.status_code == 200
        except httpx.TimeoutException as exc:
            logger.debug(
                "layer3_ping_timeout",
                extra=_log_context(tenant_id=None, error_code=ERR_LAYER3_TIMEOUT),
            )
            return False
        except httpx.RequestError as exc:
            logger.debug(
                "layer3_ping_http_client_error",
                extra=_log_context(tenant_id=None, error_code=ERR_LAYER3_HTTP_CLIENT),
            )
            return False

    # ------------------------------------------------------------------
    # Sync TruthObject → Knowledge Graph
    # ------------------------------------------------------------------

    async def sync_truth_object(
        self,
        truth_object_id: UUID,
        tenant_id: UUID,
        claim: str,
        claim_type: str,
        confidence: float,
        status: str,
        maturity_level: int,
        value: dict | None = None,
        applies_to: dict | None = None,
        source_count: int = 0,
        request_id: str | None = None,
    ) -> str | None:
        """
        Create or update a :GroundTruth node in the Layer 3 Knowledge Graph.

        Returns the KG node ID on success, None on failure.

        The node is created with the Cypher pattern:
          MERGE (g:GroundTruth {truth_object_id: $id, tenant_id: $org_id})
          SET g += $properties
          RETURN g.id
        """
        if not self._settings.layer3_sync_enabled:
            metrics = get_metrics()
            if metrics:
                metrics.increment_kg_sync_outcome(
                    sync_status="disabled", transition=f"{status}->kg_sync"
                )
            logger.debug(
                "Layer 3 sync disabled — skipping sync for %s", truth_object_id
            )
            return None

        payload = {
            "node_type": "GroundTruth",
            "properties": {
                "truth_object_id": str(truth_object_id),
                "tenant_id": str(tenant_id),
                "claim": claim,
                "claim_type": claim_type,
                "confidence": confidence,
                "status": status,
                "maturity_level": maturity_level,
                "source_count": source_count,
                "value": value,
                "applies_to": applies_to,
            },
            "merge_keys": ["truth_object_id", "tenant_id"],
        }

        transition = f"{status}->kg_sync"
        max_retries = 3
        for attempt in range(max_retries):
            try:
                client = self._get_client()
                resp = await client.post(
                    f"{self._base_url}/api/v1/nodes",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                data = self._parse_node_response(
                    resp,
                    tenant_id=tenant_id,
                    truth_object_id=truth_object_id,
                    request_id=request_id,
                )
                node_id = data["node_id"]
                logger.info(
                    "Synced TruthObject %s to Layer 3 KG as node %s",
                    truth_object_id,
                    node_id,
                    extra=_log_context(
                        tenant_id=tenant_id,
                        truth_object_id=truth_object_id,
                        request_id=request_id,
                        error_code="L5_LAYER3_SYNC_SUCCESS",
                        transition=transition,
                        sync_status="success",
                    ),
                )
                metrics = get_metrics()
                if metrics:
                    metrics.increment_kg_sync(status="success")
                    metrics.increment_kg_sync_outcome(
                        sync_status="success", transition=transition
                    )
                logger.info(
                    "kg sync outcome",
                    extra={
                        **_log_context(
                            tenant_id=tenant_id,
                            truth_object_id=truth_object_id,
                            request_id=request_id,
                            error_code="L5_LAYER3_SYNC_SUCCESS",
                            transition=transition,
                            sync_status="success",
                        ),
                    },
                )
                return node_id
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                # Authz/policy failures are security events, not operational outages.
                if status_code in {401, 403, 451}:
                    self._record_sync_failure("policy_denied", transition)
                    logger.warning(
                        "layer3_policy_denied",
                        extra=_log_context(
                            tenant_id=tenant_id,
                            truth_object_id=truth_object_id,
                            request_id=request_id,
                            error_code=ERR_LAYER3_POLICY_DENIED,
                            transition=transition,
                            sync_status="policy_denied",
                            attempt=attempt + 1,
                            status_code=status_code,
                        ),
                    )
                    raise Layer3PolicyDeniedError(
                        "Layer 3 policy denied Ground Truth sync",
                        tenant_id=tenant_id,
                    ) from exc

                # Other 4xx errors indicate a bad sync request, but do not block Layer 5.
                if 400 <= status_code < 500:
                    self._record_sync_failure("client_error", transition)
                    logger.warning(
                        "layer3_client_error",
                        extra=_log_context(
                            tenant_id=tenant_id,
                            truth_object_id=truth_object_id,
                            request_id=request_id,
                            error_code=ERR_LAYER3_HTTP_CLIENT,
                            transition=transition,
                            sync_status="client_error",
                            attempt=attempt + 1,
                            status_code=status_code,
                        ),
                    )
                    return None

                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        "Layer 3 sync attempt %d/%d failed with HTTP %d, retrying in %ds",
                        attempt + 1,
                        max_retries,
                        status_code,
                        wait_time,
                        extra=_log_context(
                            tenant_id=tenant_id,
                            truth_object_id=truth_object_id,
                            request_id=request_id,
                            error_code=ERR_LAYER3_SERVER_ERROR,
                            transition=transition,
                            sync_status="retrying",
                            attempt=attempt + 1,
                            status_code=status_code,
                        ),
                    )
                    await asyncio.sleep(wait_time)
                    continue

                self._record_sync_failure("server_error", transition)
                logger.warning(
                    "Layer 3 sync failed for TruthObject %s after %d attempts: HTTP %d",
                    truth_object_id,
                    max_retries,
                    status_code,
                    extra=_log_context(
                        tenant_id=tenant_id,
                        truth_object_id=truth_object_id,
                        request_id=request_id,
                        error_code=ERR_LAYER3_SERVER_ERROR,
                        transition=transition,
                        sync_status="server_error",
                        attempt=attempt + 1,
                        status_code=status_code,
                    ),
                )
                return None
            except httpx.TimeoutException as exc:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        "Layer 3 sync attempt %d/%d timed out, retrying in %ds",
                        attempt + 1,
                        max_retries,
                        wait_time,
                        extra=_log_context(
                            tenant_id=tenant_id,
                            truth_object_id=truth_object_id,
                            request_id=request_id,
                            error_code=ERR_LAYER3_TIMEOUT,
                            transition=transition,
                            sync_status="retrying",
                            attempt=attempt + 1,
                        ),
                    )
                    await asyncio.sleep(wait_time)
                    continue

                self._record_sync_failure("timeout", transition)
                logger.warning(
                    "layer3_timeout",
                    extra=_log_context(
                        tenant_id=tenant_id,
                        truth_object_id=truth_object_id,
                        request_id=request_id,
                        error_code=ERR_LAYER3_TIMEOUT,
                        transition=transition,
                        sync_status="timeout",
                        attempt=attempt + 1,
                    ),
                )
                return None
            except httpx.RequestError as exc:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        "Layer 3 sync attempt %d/%d failed (%s), retrying in %ds",
                        attempt + 1,
                        max_retries,
                        exc,
                        wait_time,
                        extra=_log_context(
                            tenant_id=tenant_id,
                            truth_object_id=truth_object_id,
                            request_id=request_id,
                            error_code=ERR_LAYER3_HTTP_CLIENT,
                            transition=transition,
                            sync_status="retrying",
                            attempt=attempt + 1,
                        ),
                    )
                    await asyncio.sleep(wait_time)
                    continue

                self._record_sync_failure("exception", transition)
                logger.warning(
                    "layer3_http_client_error",
                    extra=_log_context(
                        tenant_id=tenant_id,
                        truth_object_id=truth_object_id,
                        request_id=request_id,
                        error_code=ERR_LAYER3_HTTP_CLIENT,
                        transition=transition,
                        sync_status="failed",
                        attempt=attempt + 1,
                    ),
                )
                logger.warning(
                    "kg sync outcome",
                    extra=_log_context(
                        tenant_id=tenant_id,
                        truth_object_id=truth_object_id,
                        request_id=request_id,
                        error_code=ERR_LAYER3_HTTP_CLIENT,
                        transition=transition,
                        sync_status="failed",
                    ),
                )
                return None
            except Layer3TenantMismatchError:
                self._record_sync_failure("tenant_mismatch", transition)
                logger.warning(
                    "kg sync outcome",
                    extra=_log_context(
                        tenant_id=tenant_id,
                        truth_object_id=truth_object_id,
                        request_id=request_id,
                        error_code=ERR_LAYER3_TENANT_MISMATCH,
                        transition=transition,
                        sync_status="tenant_mismatch",
                    ),
                )
                raise
            except Layer3ContractValidationError:
                self._record_sync_failure("contract_invalid", transition)
                logger.warning(
                    "kg sync outcome",
                    extra=_log_context(
                        tenant_id=tenant_id,
                        truth_object_id=truth_object_id,
                        request_id=request_id,
                        error_code=ERR_LAYER3_CONTRACT_INVALID,
                        transition=transition,
                        sync_status="contract_invalid",
                    ),
                )
                return None
        return None

    def _record_sync_failure(self, sync_status: str, transition: str) -> None:
        metrics = get_metrics()
        if metrics:
            metrics.increment_kg_sync(status=sync_status)
            metrics.increment_kg_sync_outcome(
                sync_status=sync_status,
                transition=transition,
            )

    def _parse_node_response(
        self,
        resp: httpx.Response,
        *,
        tenant_id: UUID,
        truth_object_id: UUID,
        request_id: str | None = None,
    ) -> dict[str, str]:
        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "layer3_contract_invalid_json",
                extra=_log_context(
                    tenant_id=tenant_id,
                    truth_object_id=truth_object_id,
                    request_id=request_id,
                    error_code=ERR_LAYER3_CONTRACT_INVALID,
                    sync_status="contract_invalid",
                ),
            )
            raise Layer3ContractValidationError(
                "Layer 3 returned invalid JSON for Ground Truth node sync",
                tenant_id=tenant_id,
            ) from exc

        if not isinstance(data, dict):
            logger.warning(
                "layer3_contract_invalid_shape",
                extra=_log_context(
                    tenant_id=tenant_id,
                    truth_object_id=truth_object_id,
                    request_id=request_id,
                    error_code=ERR_LAYER3_CONTRACT_INVALID,
                    sync_status="contract_invalid",
                ),
            )
            raise Layer3ContractValidationError(
                "Layer 3 node sync response must be a JSON object",
                tenant_id=tenant_id,
            )

        node_id = data.get("id") or data.get("node_id")
        if not isinstance(node_id, str) or not node_id.strip():
            logger.warning(
                "layer3_contract_missing_node_id",
                extra=_log_context(
                    tenant_id=tenant_id,
                    truth_object_id=truth_object_id,
                    request_id=request_id,
                    error_code=ERR_LAYER3_CONTRACT_INVALID,
                    sync_status="contract_invalid",
                ),
            )
            raise Layer3ContractValidationError(
                "Layer 3 node sync response is missing id/node_id",
                tenant_id=tenant_id,
            )

        response_tenant = data.get("tenant_id")
        properties = data.get("properties")
        if response_tenant is None and isinstance(properties, dict):
            response_tenant = properties.get("tenant_id")
        if response_tenant is not None and str(response_tenant) != str(tenant_id):
            logger.error(
                "layer3_tenant_mismatch",
                extra=_log_context(
                    tenant_id=tenant_id,
                    truth_object_id=truth_object_id,
                    request_id=request_id,
                    error_code=ERR_LAYER3_TENANT_MISMATCH,
                    sync_status="tenant_mismatch",
                ),
            )
            raise Layer3TenantMismatchError(
                "Layer 3 returned a Ground Truth node for a different tenant",
                tenant_id=tenant_id,
            )

        return {"node_id": node_id}

    # ------------------------------------------------------------------
    # Link GroundTruth node to existing KG entities
    # ------------------------------------------------------------------

    async def link_to_entity(
        self,
        kg_node_id: str,
        target_entity_id: str,
        relationship_type: str = "GROUNDS",
        properties: dict | None = None,
    ) -> bool:
        """
        Create a relationship between a GroundTruth node and an existing KG entity.

        Default relationship: (GroundTruth)-[:GROUNDS]->(Entity)

        Returns True on success.
        """
        if not self._settings.layer3_sync_enabled:
            return False

        payload = {
            "from_node_id": kg_node_id,
            "to_node_id": target_entity_id,
            "relationship_type": relationship_type,
            "properties": properties or {},
        }

        # Retry with exponential backoff for transient failures
        max_retries = 3
        for attempt in range(max_retries):
            try:
                client = self._get_client()
                resp = await client.post(
                    f"{self._base_url}/api/v1/relationships",
                    json=payload,
                    headers=self._headers,
                )
                resp.raise_for_status()
                logger.info(
                    "Linked KG node %s -[%s]-> %s",
                    kg_node_id,
                    relationship_type,
                    target_entity_id,
                )
                return True
            except httpx.HTTPStatusError as exc:
                # Don't retry 4xx errors
                if 400 <= exc.response.status_code < 500:
                    logger.warning(
                        "Layer 3 link failed: %s -[%s]-> %s: HTTP %d",
                        kg_node_id,
                        relationship_type,
                        target_entity_id,
                        exc.response.status_code,
                    )
                    return False
                # Retry 5xx on non-final attempts
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                    continue
                logger.warning(
                    "Layer 3 link failed after %d attempts: %s -[%s]-> %s: HTTP %d",
                    max_retries,
                    kg_node_id,
                    relationship_type,
                    target_entity_id,
                    exc.response.status_code,
                )
                return False
            except httpx.TimeoutException as exc:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                    continue
                logger.warning(
                    "layer3_link_timeout",
                    extra=_log_context(
                        tenant_id=None,
                        request_id=request_id,
                        error_code=ERR_LAYER3_TIMEOUT,
                        sync_status="timeout",
                        attempt=attempt + 1,
                    ),
                )
                return False
            except httpx.RequestError as exc:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                    continue
                logger.warning(
                    "layer3_link_http_client_error",
                    extra=_log_context(
                        tenant_id=None,
                        request_id=request_id,
                        error_code=ERR_LAYER3_HTTP_CLIENT,
                        sync_status="failed",
                        attempt=attempt + 1,
                    ),
                )
                return False

    # ------------------------------------------------------------------
    # Query Layer 3 for entity context
    # ------------------------------------------------------------------

    async def get_entity_context(
        self,
        entity_id: str,
        tenant_id: UUID,
    ) -> dict[str, Any] | None:
        """
        Fetch entity metadata from Layer 3 to enrich a TruthObject.

        Returns the entity dict or None if not found / unavailable.
        """
        request_tenant = str(tenant_id)
        try:
            client = self._get_client()
            resp = await client.get(
                f"{self._base_url}/api/v1/entities/{entity_id}",
                params={"tenant_id": str(tenant_id)},
                headers=self._headers,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict):
                logger.warning(
                    "layer3_entity_context_contract_invalid",
                    extra=_log_context(
                        tenant_id=tenant_id,
                        request_id=request_id,
                        error_code=ERR_LAYER3_CONTRACT_INVALID,
                        sync_status="contract_invalid",
                    ),
                )
                return None
            response_tenant = data.get("tenant_id")
            if response_tenant is not None and str(response_tenant) != str(tenant_id):
                logger.error(
                    "layer3_entity_context_tenant_mismatch",
                    extra=_log_context(
                        tenant_id=tenant_id,
                        request_id=request_id,
                        error_code=ERR_LAYER3_TENANT_MISMATCH,
                        sync_status="tenant_mismatch",
                    ),
                )
                raise Layer3TenantMismatchError(
                    "Layer 3 returned entity context for a different tenant",
                    tenant_id=tenant_id,
                )
            return data
        except httpx.HTTPStatusError as exc:
            logger.debug(
                "layer3_entity_context_http_status",
                extra=_log_context(
                    tenant_id=tenant_id,
                    error_code=(
                        ERR_LAYER3_SERVER_ERROR
                        if exc.response.status_code >= 500
                        else ERR_LAYER3_HTTP_CLIENT
                    ),
                    status_code=exc.response.status_code,
                ),
            )
            return None
        except httpx.TimeoutException as exc:
            logger.debug(
                "layer3_entity_context_timeout",
                extra=_log_context(tenant_id=tenant_id, error_code=ERR_LAYER3_TIMEOUT),
            )
            return None
        except httpx.RequestError as exc:
            logger.debug(
                "layer3_entity_context_http_client_error",
                extra=_log_context(
                    tenant_id=tenant_id, error_code=ERR_LAYER3_HTTP_CLIENT
                ),
            payload = resp.json()
            if not isinstance(payload, dict):
                raise ValidationError.from_exception_data(
                    "Layer3EntityContext",
                    [
                        {
                            "type": "dict_type",
                            "loc": ("response",),
                            "msg": "Layer 3 entity context must be an object",
                            "input": payload,
                        }
                    ],
                )
            response_tenant = payload.get("tenant_id")
            if response_tenant is not None and str(response_tenant) != request_tenant:
                logger.warning(
                    "Layer 3 entity context tenant mismatch",
                    extra={
                        "error_code": L3_ERR_CONTRACT,
                        "request_id": None,
                        "tenant_id": request_tenant,
                        "entity_id": entity_id,
                        "response_tenant_id": str(response_tenant),
                    },
                )
                return None
            return payload
        except httpx.TimeoutException as exc:
            logger.warning(
                "Layer 3 entity context fetch timed out",
                extra={
                    "error_code": L3_ERR_TIMEOUT,
                    "request_id": None,
                    "tenant_id": request_tenant,
                    "entity_id": entity_id,
                },
            )
            logger.debug("Layer 3 timeout details for entity %s: %s", entity_id, exc)
            return None
        except httpx.HTTPError as exc:
            logger.warning(
                "Layer 3 entity context HTTP client failure",
                extra={
                    "error_code": L3_ERR_HTTP_CLIENT,
                    "request_id": None,
                    "tenant_id": request_tenant,
                    "entity_id": entity_id,
                },
            )
            logger.debug("Layer 3 HTTP client failure for entity %s: %s", entity_id, exc)
            return None
        except ValidationError as exc:
            logger.warning(
                "Layer 3 entity context contract validation failed",
                extra={
                    "error_code": L3_ERR_CONTRACT,
                    "request_id": None,
                    "tenant_id": request_tenant,
                    "entity_id": entity_id,
                },
            )
            logger.debug("Layer 3 contract validation details for entity %s: %s", entity_id, exc)
            return None
        except Exception as exc:
            logger.debug("Layer 3 entity context fetch failed for %s: %s", entity_id, exc)
            return None
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "layer3_entity_context_contract_invalid_json",
                extra=_log_context(
                    tenant_id=tenant_id,
                    request_id=request_id,
                    error_code=ERR_LAYER3_CONTRACT_INVALID,
                    sync_status="contract_invalid",
                ),
            )
            logger.debug("Layer 3 HTTP client failure for entity %s: %s", entity_id, exc)
            return None
        except ValidationError as exc:
            logger.warning(
                "Layer 3 entity context contract validation failed",
                extra={
                    "error_code": L3_ERR_CONTRACT,
                    "request_id": None,
                    "tenant_id": request_tenant,
                    "entity_id": entity_id,
                },
            )
            logger.debug("Layer 3 contract validation details for entity %s: %s", entity_id, exc)
            return None
        except Exception as exc:
            logger.debug("Layer 3 entity context fetch failed for %s: %s", entity_id, exc)
            return None

    # ------------------------------------------------------------------
    # Bulk sync helper (called by background task)
    # ------------------------------------------------------------------

    async def bulk_sync_approved(
        self,
        truth_objects: list[dict[str, Any]],
    ) -> dict[str, str | None]:
        """
        Sync a list of approved TruthObjects to Layer 3.

        Returns a mapping of truth_object_id → kg_node_id (or None on failure).
        """
        results: dict[str, str | None] = {}
        for obj in truth_objects:
            node_id = await self.sync_truth_object(
                truth_object_id=obj["id"],
                tenant_id=obj["tenant_id"],
                claim=obj["claim"],
                claim_type=obj["claim_type"],
                confidence=obj["confidence"],
                status=obj["status"],
                maturity_level=obj["maturity_level"],
                value=obj.get("value"),
                applies_to=obj.get("applies_to"),
                source_count=obj.get("source_count", 0),
            )
            results[str(obj["id"])] = node_id
        return results


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_client: Layer3Client | None = None


def get_layer3_client() -> Layer3Client:
    """Return the shared Layer3Client singleton."""
    global _client
    if _client is None:
        _client = Layer3Client()
    return _client

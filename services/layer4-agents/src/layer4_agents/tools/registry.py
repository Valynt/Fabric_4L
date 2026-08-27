from __future__ import annotations

"""Tool registry for managing and executing 24+ skills.

Provides centralized tool registration, discovery, and execution.
"""


import asyncio
import hashlib
import logging
import os
import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextvars import Token
from typing import Any, Literal
from uuid import UUID, uuid4

from value_fabric.shared.identity.context import (
    AUTH_SOURCE_SERVICE_ACCOUNT,
    RequestContext,
    _current_context,
    get_request_context,
    set_request_context,
)
from value_fabric.shared.identity.policy_registry import authorize_action, get_tool_action

# CONTRACT §2.4: Canonical ToolResult from shared package (migration in progress)
from value_fabric.shared.identity.tool_contract import ToolError as CanonicalToolError
from value_fabric.shared.identity.tool_contract import ToolMetadata as CanonicalToolMetadata
from value_fabric.shared.identity.tool_contract import ToolResult as CanonicalToolResult
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..models.tool_schemas import ToolCategory, ToolSchema
from ..observability import Layer4EventContext, Layer4LifecycleLogger


class ToolResult(TypedDictModel):
    """Structured result for tool execution with contract-compliant error handling.

    DEPRECATED: Migrate to CanonicalToolResult from tool_contract.py for cross-layer
    consistency. This local class is kept for backward compatibility during transition.

    Replaces exception-based error handling with structured error results
    per Contract §2.4. All tools should return or wrap results in this format.

    Attributes:
        status: "success" or "error"
        data: Result data on success (arbitrary dict structure)
        error: Error information on failure
        metadata: Execution metadata (timing, trace_id, etc.)
    """

    status: Literal["success", "error"]
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None

    @classmethod
    def success(
        cls,
        data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Create a success result."""
        return cls(status="success", data=data, error=None, metadata=metadata)

    @classmethod
    def failure(
        cls,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
        recoverable: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Create an error result.

        Args:
            code: Machine-readable error code (e.g., "VALIDATION_ERROR")
            message: Human-readable error message (safe, no secrets)
            details: Optional structured error details
            trace_id: Correlation ID for debugging
            recoverable: Whether the error is retryable
            metadata: Optional metadata dict (if not provided, will be built from trace_id)
        """
        error_dict: dict[str, Any] = {
            "code": code,
            "message": message,
            "recoverable": recoverable,
        }
        if details:
            error_dict["details"] = details

        if metadata is None and trace_id:
            metadata = {"trace_id": trace_id}

        return cls(status="error", data=None, error=error_dict, metadata=metadata)

    def is_success(self) -> bool:
        """Check if result is successful."""
        return self.status == "success"

    def is_error(self) -> bool:
        """Check if result is an error."""
        return self.status == "error"

    def to_canonical(self) -> CanonicalToolResult[Any]:
        """Convert local ToolResult to canonical shared ToolResult (CONTRACT §2.4).

        Use this when crossing layer boundaries or serializing to the agent registry.
        """
        error = None
        if self.error:
            error = CanonicalToolError(
                code=str(self.error.get("code", "UNKNOWN")),
                message=str(self.error.get("message", "Unknown error")),
                recoverable=bool(self.error.get("recoverable", False)),
                details=self.error.get("details") or {},
            )
        metadata = None
        if self.metadata:
            metadata = CanonicalToolMetadata(
                execution_time_ms=float(self.metadata.get("execution_time_ms", 0.0)),
                tenant_id=self.metadata.get("tenant_id"),
                tool_version=str(self.metadata.get("tool_version", "1.0.0")),
                trace_id=str(self.metadata.get("trace_id", "")),
            )
        return CanonicalToolResult(
            status=self.status,
            data=self.data,
            error=error,
            metadata=metadata,
        )


class ToolRegistry_get_all_schemasResult(TypedDictModel):
    pass


class get_tool_metadataResult(TypedDictModel):
    category: Any
    description: Any
    name: Any
    tenant_scoped: Any


logger = logging.getLogger(__name__)
lifecycle_logger = Layer4LifecycleLogger(logger)

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(secret|token|password|api[_-]?key|authorization|credential|private[_-]?key)",
    re.IGNORECASE,
)


def _safe_metadata(
    *,
    trace_id: str | None = None,
    tenant_id: str | None = None,
    request_id: str | None = None,
    execution_time_ms: int | None = None,
) -> dict[str, Any]:
    """Build trace metadata without copying untrusted inputs."""
    metadata: dict[str, Any] = {
        "trace_id": trace_id or request_id or str(uuid4()),
    }
    if request_id:
        metadata["request_id"] = request_id
    if tenant_id:
        metadata["tenant_id"] = tenant_id
    if execution_time_ms is not None:
        metadata["execution_time_ms"] = execution_time_ms
    return metadata


def _safe_input_keys(input_dict: dict[str, Any]) -> list[str]:
    """Expose only non-sensitive input key names in diagnostic details."""
    return [
        key if not _SENSITIVE_KEY_PATTERN.search(str(key)) else "[redacted]"
        for key in input_dict.keys()
    ]


def _coerce_uuid_string(value: Any) -> str | None:
    """Return a normalized UUID string, or None for malformed tenant values."""
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return None


def _has_internal_execution_envelope(input_dict: dict[str, Any]) -> bool:
    """Validate the minimum workflow envelope required for internal tenant context."""
    return all(input_dict.get(key) for key in ("workflow_id", "run_id", "trace_id"))


def _extract_auth_error_info(exc: Exception) -> tuple[str, str, Any]:
    """Extract normalized error code, message, and details from an auth exception."""
    status_code = getattr(exc, "status_code", 403)
    detail = getattr(exc, "detail", None)
    code = "AUTHENTICATION_REQUIRED" if status_code == 401 else "INSUFFICIENT_SCOPE"
    if isinstance(detail, dict):
        message = detail.get("message", type(exc).__name__)
    elif detail is not None:
        message = str(detail)
    else:
        message = type(exc).__name__
    return code, message, detail


def _record_tool_auth_failure_metric(tool_name: str, tenant_id: Any) -> None:
    """Safely increment the tool auth failure Prometheus metric if available."""
    try:
        from ..metrics.prometheus_metrics import get_metrics

        metrics = get_metrics()
        if metrics:
            metrics.increment_tool_auth_failure(
                tool_name=tool_name,
                tenant_id=str(tenant_id) if tenant_id else "unknown",
            )
    except asyncio.CancelledError:
        raise
    except Exception:
        pass


class ToolError(Exception):
    """Raised when a tool execution fails."""

    pass


class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not found."""

    pass


class ToolValidationError(ToolError, ValueError):
    """Raised when tool input validation fails."""

    pass


class TenantSpoofingError(ToolValidationError):
    """Raised when a tenant_id is supplied that does not match the authenticated context.

    Subclass of :class:`ToolValidationError` (and therefore :class:`ValueError`) so it is
    treated as an input/validation failure and is mapped by ``BaseTool.run`` to a stable
    structured ``TENANT_SPOOFING_DETECTED`` error code without an exception stack trace.
    """

    pass


class ToolRegistrationError(ToolValidationError):
    """Raised when tool registration constraint is violated."""

    pass


class BaseTool(ABC):
    """Base class for all tools.

    All tools must inherit from this class and implement:
    - name: Tool identifier
    - category: ToolCategory
    - description: Human-readable description
    - input_schema: Pydantic model class for input
    - output_schema: Pydantic model class for output
    - execute(): The actual tool implementation

    Example:
        class MyTool(BaseTool):
            name = "my_tool"
            category = ToolCategory.UTILITY
            description = "Does something useful"
            input_schema = MyToolInput
            output_schema = MyToolOutput

            async def execute(self, input_data: MyToolInput) -> MyToolOutput:
                # Implementation here
                return MyToolOutput(result="success")
    """

    name: str = ""
    category: ToolCategory = ToolCategory.UTILITY
    description: str = ""
    input_schema: type | None = None
    output_schema: type | None = None
    timeout_seconds: int = 30
    requires_auth: bool = False
    requires_tenant: bool = False  # Task 2.3: Tenant enforcement flag

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize tool with optional configuration.

        Args:
            config: Tool-specific configuration (may include tenant_id)
        """
        self.config = config or {}
        self._initialized = True

    def get_tenant_id(self) -> str | None:
        """Extract tenant_id from config (Task 2.3).

        Returns:
            Tenant ID if set in config, None otherwise
        """
        return self.config.get("tenant_id")

    @abstractmethod
    async def execute(self, input_data: Any) -> Any:
        """Execute the tool with validated input.

        Args:
            input_data: Validated input (input_schema instance)

        Returns:
            Output (output_schema instance)

        Raises:
            ToolError: If execution fails
        """
        pass

    def get_schema(self) -> ToolSchema:
        """Get the tool schema for registration."""
        return ToolSchema(
            name=self.name,
            category=self.category,
            description=self.description,
            input_schema=self.input_schema.model_json_schema() if self.input_schema else {},
            output_schema=self.output_schema.model_json_schema() if self.output_schema else {},
            timeout_seconds=self.timeout_seconds,
            requires_auth=self.requires_auth,
        )

    async def run(self, input_dict: dict[str, Any], trace_id: str | None = None) -> ToolResult:
        """Run the tool with raw input dict (validates first).

        CONTRACT §2.4: Returns structured ToolResult instead of raising exceptions.
        All errors are captured and returned as structured error results.

        Args:
            input_dict: Raw input parameters
            trace_id: Optional correlation ID for debugging

        Returns:
            ToolResult with status, data, and error information
        """
        start_time = asyncio.get_event_loop().time()
        request_id = input_dict.get("request_id")
        tenant_id = self.get_tenant_id() or input_dict.get("tenant_id")
        base_metadata = _safe_metadata(
            trace_id=trace_id or input_dict.get("trace_id"),
            request_id=request_id,
            tenant_id=tenant_id,
        )

        if self.input_schema is None:
            return ToolResult.failure(
                code="CONFIGURATION_ERROR",
                message=f"Tool '{self.name}' has no input schema defined",
                metadata=base_metadata,
                recoverable=False,
            )

        # Validate input
        try:
            validated_input = self.input_schema(**input_dict)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.info("Tool input validation failed: %s", self.name, exc_info=e)
            return ToolResult.failure(
                code="INPUT_VALIDATION_ERROR",
                message=f"Invalid input for tool '{self.name}'",
                details={"input_keys": _safe_input_keys(input_dict)},
                metadata=base_metadata,
                recoverable=False,
            )

        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                self.execute(validated_input), timeout=self.timeout_seconds
            )
        except TimeoutError:
            elapsed_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            metadata = _safe_metadata(
                trace_id=trace_id or input_dict.get("trace_id"),
                request_id=request_id,
                tenant_id=tenant_id,
                execution_time_ms=elapsed_ms,
            )
            return ToolResult.failure(
                code="TOOL_TIMEOUT",
                message=f"Tool '{self.name}' timed out after {self.timeout_seconds}s",
                recoverable=True,
                metadata=metadata,
            )
        except asyncio.CancelledError:
            raise
        except TenantSpoofingError as e:
            # Security hardening: map tenant spoofing to a stable structured
            # failure code without logging an exception stack trace.
            logger.warning("Tenant spoofing rejected by tool %s: %s", self.name, e)
            # Only use the authenticated/config tenant here, never the untrusted
            # request-supplied tenant_id, to avoid tenant-id poisoning via the
            # failure metadata/logs. Prefer the request-context tenant (trusted)
            # when available, then fall back to the tool config tenant.
            request_ctx = get_request_context()
            trusted_tenant_id = getattr(request_ctx, "tenant_id", None) or self.get_tenant_id()
            # Normalize to str: _safe_metadata and the ToolMetadata contract expect a
            # string tenant_id, but RequestContext.tenant_id can be a UUID.
            trusted_tenant_id = str(trusted_tenant_id) if trusted_tenant_id else None
            elapsed_ms = int((asyncio.get_running_loop().time() - start_time) * 1000)
            return ToolResult.failure(
                code="TENANT_SPOOFING_DETECTED",
                message=str(e),
                recoverable=False,
                metadata=_safe_metadata(
                    trace_id=trace_id or input_dict.get("trace_id"),
                    request_id=request_id,
                    tenant_id=trusted_tenant_id,
                    execution_time_ms=elapsed_ms,
                ),
            )
        except Exception:
            # Log the full exception internally, return safe error to caller
            logger.exception("Tool execution failed: %s", self.name)
            elapsed_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            metadata = _safe_metadata(
                trace_id=trace_id or input_dict.get("trace_id"),
                request_id=request_id,
                tenant_id=tenant_id,
                execution_time_ms=elapsed_ms,
            )
            return ToolResult.failure(
                code="TOOL_EXECUTION_ERROR",
                message=f"Tool '{self.name}' execution failed",
                recoverable=False,
                metadata=metadata,
            )

        # Convert result to dict
        if hasattr(result, "model_dump") or hasattr(result, "dict"):
            result_data = result.model_dump()
        elif isinstance(result, dict):
            result_data = result
        else:
            result_data = {"result": result}

        elapsed_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        return ToolResult.success(
            data=result_data,
            metadata=_safe_metadata(
                trace_id=trace_id or input_dict.get("trace_id"),
                request_id=request_id,
                tenant_id=tenant_id,
                execution_time_ms=elapsed_ms,
            ),
        )


class TenantAwareTool(BaseTool):
    """Base class for tools that require tenant context (Task 2.3).

    Tools that access tenant-scoped data (knowledge graph, CRM, etc.)
    should inherit from this class to ensure tenant isolation.

    Example:
        class QueryGraphTool(TenantAwareTool):
            name = "query_graph"
            requires_tenant = True

            async def execute(self, input_data: QueryInput) -> QueryOutput:
                tenant_id = self.get_tenant_id()
                # Use tenant_id for all queries
                ...
    """

    requires_tenant: bool = True

    def validate_tenant_context(self) -> tuple[str | None, ToolResult | None]:
        """Validate that tenant context is present.

        Returns:
            Tuple of (tenant_id, error_result). If error_result is not None,
            validation failed and the error should be returned.
        """
        tenant_id = self.get_tenant_id()
        if tenant_id:
            return tenant_id, None
        if self.requires_tenant:
            return None, ToolResult.failure(
                code="TENANT_CONTEXT_MISSING",
                message=f"Tool '{self.name}' requires tenant context but no tenant_id provided",
                recoverable=False,
                metadata=_safe_metadata(),
            )
        return "", None

    async def run(self, input_dict: dict[str, Any], trace_id: str | None = None) -> ToolResult:
        """Run tool with tenant validation (Task 2.3).

        Validates tenant context before executing. Returns structured ToolResult
        per Contract §2.4 instead of raising exceptions.
        """
        # Validate tenant context before execution
        tenant_id, error = self.validate_tenant_context()
        if error:
            return error

        # Pass trace_id through to base run
        return await super().run(input_dict, trace_id=trace_id)


class ToolRegistry:
    """Central registry for all tools.

    Manages tool registration, discovery, and execution.

    Example:
        registry = ToolRegistry()

        # Register tools
        registry.register(MyTool())
        registry.register_batch([ToolA(), ToolB()])

        # Execute tool
        result = await registry.execute("my_tool", {"param": "value"})

        # List available tools
        tools = registry.list_tools()
    """

    def __init__(self, redis_client: Any | None = None):
        """Initialize empty registry.

        Args:
            redis_client: Optional async Redis client. When provided, tool
                idempotency results are persisted to Redis with a 24-hour TTL
                instead of an in-memory dictionary.
        """
        self._tools: dict[str, BaseTool] = {}
        # In local/dev/test environments callers may opt out of human-in-the-loop
        # approval for irreversible CRM/INTEGRATION tools by setting
        # LAYER4_AUTO_APPROVE_IRREVERSIBLE_TOOLS=true.  This must never be enabled
        # in production-like environments.
        auto_approve = os.getenv("LAYER4_AUTO_APPROVE_IRREVERSIBLE_TOOLS", "").lower() in (
            "true",
            "1",
            "yes",
        )
        if auto_approve:
            environment = (
                os.getenv("ENVIRONMENT", os.getenv("ENV", os.getenv("APP_ENV", ""))).strip().lower()
            )
            if environment == "production":
                raise RuntimeError(
                    "unsafe_production_configuration: "
                    "LAYER4_AUTO_APPROVE_IRREVERSIBLE_TOOLS must never be enabled in "
                    "production-like environments (tool approval bypass; same "
                    "fail-closed doctrine as INV-SEC-001 dev auth bypass flags)"
                )
            self._approval_required_categories: set[ToolCategory] = set()
        else:
            self._approval_required_categories = {
                ToolCategory.CRM,
                ToolCategory.INTEGRATION,
            }
        self._redis_client = redis_client
        self._idempotency_cache: dict[tuple[str, str, str], ToolResult] = {}
        self._idempotency_ttl_seconds = int(
            os.getenv("LAYER4_TOOL_IDEMPOTENCY_TTL_SECONDS", "86400")
        )

    def _idempotency_key(self, tenant_id: str | None, tool_name: str, idempotency_key: str) -> str:
        """Return a deterministic Redis key for a tool idempotency entry."""
        raw = f"{tenant_id or 'unknown'}:{tool_name}:{idempotency_key}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"l4:tool:idempotency:{digest}"

    async def _get_cached_result(
        self, tenant_id: str | None, tool_name: str, idempotency_key: str
    ) -> ToolResult | None:
        """Fetch a cached tool result, preferring Redis when configured."""
        if self._redis_client is not None:
            try:
                cached = await self._redis_client.get(
                    self._idempotency_key(tenant_id, tool_name, idempotency_key)
                )
                if cached:
                    return ToolResult.model_validate_json(cached)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Redis idempotency fetch failed; continuing without cache")
        else:
            return self._idempotency_cache.get((tenant_id, tool_name, idempotency_key))
        return None

    async def _set_cached_result(
        self,
        tenant_id: str | None,
        tool_name: str,
        idempotency_key: str,
        result: ToolResult,
    ) -> None:
        """Store a tool result, preferring Redis when configured."""
        if self._redis_client is not None:
            try:
                await self._redis_client.set(
                    self._idempotency_key(tenant_id, tool_name, idempotency_key),
                    result.model_dump_json(),
                    ex=self._idempotency_ttl_seconds,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Redis idempotency store failed; result not cached")
        else:
            self._idempotency_cache[(tenant_id, tool_name, idempotency_key)] = result

    def register(self, tool: BaseTool) -> None:
        """Register a single tool.

        Args:
            tool: Tool instance to register

        Raises:
            ToolRegistrationError: If tool name is empty or already registered
        """
        if not tool.name:
            raise ToolRegistrationError("Tool must have a name")

        if tool.name in self._tools:
            raise ToolRegistrationError(f"Tool '{tool.name}' is already registered")

        self._tools[tool.name] = tool

    def register_batch(self, tools: list[BaseTool]) -> None:
        """Register multiple tools at once.

        Args:
            tools: List of tool instances
        """
        for tool in tools:
            self.register(tool)

    def unregister(self, tool_name: str) -> None:
        """Remove a tool from registry.

        Args:
            tool_name: Name of tool to remove
        """
        if tool_name in self._tools:
            del self._tools[tool_name]

    def get(self, tool_name: str) -> BaseTool:
        """Get a tool by name.

        Args:
            tool_name: Tool identifier

        Returns:
            Tool instance

        Raises:
            ToolNotFoundError: If tool not found
        """
        if tool_name not in self._tools:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found")
        return self._tools[tool_name]

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is registered.

        Args:
            tool_name: Tool identifier

        Returns:
            True if tool exists
        """
        return tool_name in self._tools

    async def _authorize_tool_or_fail(
        self,
        tool_action: Any,
        request_context: Any,
        tenant_id: Any,
        tool_name: str,
        trace_id: Any,
    ) -> ToolResult | None:
        """Authorize a tool action and return a failure ToolResult on denial.

        CancelledError is re-raised so task cancellation is never swallowed.
        This helper lives outside ``execute`` so the contract linter can
        distinguish cancellation hygiene from unstructured tool errors.
        """
        try:
            authorize_action(
                tool_action, request_context, target_tenant_id=str(tenant_id) if tenant_id else None
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            code, message, detail = _extract_auth_error_info(exc)
            _record_tool_auth_failure_metric(tool_name, tenant_id)
            return ToolResult.failure(
                code=code,
                message=message,
                details=detail if isinstance(detail, dict) else {"detail": detail},
                recoverable=False,
                metadata=_safe_metadata(
                    trace_id=trace_id, tenant_id=str(tenant_id) if tenant_id else None
                ),
            )
        return None

    def _resolve_execution_tenant(
        self,
        *,
        tool: BaseTool,
        tool_name: str,
        input_dict: dict[str, Any],
        request_context: Any,
        trace_id: str | None,
    ) -> tuple[str | None, ToolResult | None]:
        """Resolve the trusted tenant for a tool execution.

        Authenticated request context wins over configured or raw input values.
        Raw input tenant IDs are trusted only for internal workflow envelopes.
        """
        configured_tenant_id = tool.get_tenant_id()
        input_tenant_id = input_dict.get("tenant_id")
        context_tenant_id = (
            str(request_context.tenant_id)
            if request_context and request_context.tenant_id
            else None
        )

        if context_tenant_id:
            claimed_tenant_id = configured_tenant_id or input_tenant_id
            if claimed_tenant_id and str(claimed_tenant_id) != context_tenant_id:
                return None, ToolResult.failure(
                    code="TENANT_CONTEXT_MISMATCH",
                    message=f"Tool '{tool_name}' tenant_id does not match request context",
                    recoverable=False,
                    metadata=_safe_metadata(
                        trace_id=trace_id,
                        tenant_id=str(claimed_tenant_id),
                    ),
                )
            return context_tenant_id, None

        tenant_source = configured_tenant_id or input_tenant_id
        tenant_id = _coerce_uuid_string(tenant_source)
        if tenant_source and tenant_id is None:
            return None, ToolResult.failure(
                code="TENANT_CONTEXT_INVALID",
                message=f"Tool '{tool_name}' received malformed tenant context",
                recoverable=False,
                metadata=_safe_metadata(trace_id=trace_id),
            )
        if (
            tenant_id
            and not configured_tenant_id
            and not _has_internal_execution_envelope(input_dict)
        ):
            return None, ToolResult.failure(
                code="TENANT_CONTEXT_UNTRUSTED",
                message=f"Tool '{tool_name}' tenant context requires approved request or workflow execution context",
                recoverable=False,
                metadata=_safe_metadata(trace_id=trace_id, tenant_id=tenant_id),
            )
        return tenant_id, None

    def _enforce_approval_policy(
        self,
        *,
        tool_name: str,
        tool_category: ToolCategory,
        input_dict: dict[str, Any],
        workflow_id: str | None,
        tenant_id: str,
        user_id: str | None,
        trace_id: str | None,
    ) -> ToolResult | None:
        """Enforce human-in-the-loop approval policy for restricted categories."""
        approval_required = tool_category in self._approval_required_categories
        if not approval_required:
            return None

        approved = input_dict.get("approval_decision") == "approved"
        if not approved:
            self._emit_policy_audit_event(
                workflow_id=workflow_id,
                tenant_id=tenant_id,
                user_id=user_id,
                tool_name=tool_name,
                approval_decision="denied",
            )
            return ToolResult.failure(
                code="APPROVAL_REQUIRED",
                message=f"Tool '{tool_name}' requires approval before execution",
                recoverable=False,
                metadata=_safe_metadata(trace_id=trace_id, tenant_id=tenant_id),
            )

        self._emit_policy_audit_event(
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            user_id=user_id,
            tool_name=tool_name,
            approval_decision="approved",
        )
        return None

    @staticmethod
    def _tool_lifecycle_context(
        *,
        tool: BaseTool,
        tenant_id: str,
        trace_id: str | None,
        workflow_id: str | None,
    ) -> Layer4EventContext:
        request_id = str(trace_id or workflow_id or "tool")
        return Layer4EventContext(
            request_id=request_id,
            trace_id=request_id,
            tenant_id=str(tenant_id or "unknown"),
            workflow_id=str(workflow_id or "unknown"),
            run_id=str(workflow_id or "unknown"),
            provider_name=str(type(tool).__name__),
        )

    async def _run_tool_with_context(
        self,
        *,
        tool: BaseTool,
        tool_name: str,
        input_dict: dict[str, Any],
        request_context: Any,
        tenant_id: str,
        trace_id: str | None,
        workflow_id: str | None,
    ) -> ToolResult:
        """Run a tool with lifecycle logging and workflow RequestContext propagation."""
        lifecycle_context = self._tool_lifecycle_context(
            tool=tool,
            tenant_id=tenant_id,
            trace_id=trace_id,
            workflow_id=workflow_id,
        )
        lifecycle_logger.emit(stage="tool-call", context=lifecycle_context)

        internal_context_token: Token | None = None
        if request_context is None:
            internal_context_token = set_request_context(
                RequestContext(
                    tenant_id=tenant_id,
                    user_id=input_dict.get("user_id") or "workflow-executor",
                    roles=["service"],
                    source=AUTH_SOURCE_SERVICE_ACCOUNT,
                    auth_source=AUTH_SOURCE_SERVICE_ACCOUNT,
                    request_id=str(trace_id or workflow_id or "tool"),
                    trace_id=str(trace_id) if trace_id else None,
                    service_account_id="layer4-tool-registry",
                    service_account_scopes=[f"tool:{tool_name}"],
                    raw={
                        "workflow_id": workflow_id,
                        "run_id": input_dict.get("run_id"),
                        "tool_name": tool_name,
                    },
                )
            )
        try:
            result = await tool.run(input_dict, trace_id=trace_id)
        finally:
            if internal_context_token is not None:
                _current_context.reset(internal_context_token)

        lifecycle_logger.emit(
            stage="tool-result",
            context=lifecycle_context,
            tool_success=result.is_success(),
        )
        return result

    async def execute(self, tool_name: str, input_dict: dict[str, Any]) -> ToolResult:
        """Execute a tool by name.

        SECURITY: This is an orchestration method that dispatches to tool implementations.
        It does NOT execute SQL. The tool_name is validated against registered tools,
        and input_dict is validated via Pydantic schemas before reaching tool logic.

        When ``AUDIT_LEDGER_MODE=enabled``, emits a ``TOOL_INVOCATION`` audit event
        with request/response hashing for the GATE audit ledger.

        CONTRACT §2.4: Returns structured ToolResult with error handling instead of
        raising exceptions.

        Args:
            tool_name: Tool identifier (validated against registry)
            input_dict: Raw input parameters (validated via Pydantic schemas)

        Returns:
            ToolResult with status, data, and error information
        """
        try:
            tool = self.get(tool_name)
        except ToolNotFoundError:
            logger.warning("tool_not_found", extra={"error_code": "TOOL_NOT_FOUND"})
            return ToolResult.failure(
                code="TOOL_NOT_FOUND",
                message="Tool not found",
                recoverable=False,
            )

        trace_id = input_dict.get("trace_id")
        workflow_id = input_dict.get("workflow_id")
        idempotency_key = input_dict.get("idempotency_key")
        request_context = get_request_context()
        user_id = (
            str(request_context.user_id) if request_context and request_context.user_id else None
        )
        tool_action = get_tool_action(tool_name)

        tenant_id, tenant_error = self._resolve_execution_tenant(
            tool=tool,
            tool_name=tool_name,
            input_dict=input_dict,
            request_context=request_context,
            trace_id=trace_id,
        )
        if tenant_error is not None:
            return tenant_error

        if tool_action:
            auth_result = await self._authorize_tool_or_fail(
                tool_action=tool_action,
                request_context=request_context,
                tenant_id=tenant_id,
                tool_name=tool_name,
                trace_id=trace_id,
            )
            if auth_result is not None:
                return auth_result

        if not tenant_id:
            return ToolResult.failure(
                code="TENANT_CONTEXT_MISSING",
                message=f"Tool '{tool_name}' requires tenant context",
                recoverable=False,
                metadata=_safe_metadata(trace_id=trace_id),
            )
        tenant_id = str(tenant_id)
        if tool.category in self._approval_required_categories and not idempotency_key:
            return ToolResult.failure(
                code="IDEMPOTENCY_KEY_REQUIRED",
                message=f"Tool '{tool_name}' requires idempotency_key for irreversible operation",
                recoverable=False,
                metadata=_safe_metadata(trace_id=trace_id, tenant_id=tenant_id),
            )

        approval_failure = self._enforce_approval_policy(
            tool_name=tool_name,
            tool_category=tool.category,
            input_dict=input_dict,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            user_id=user_id,
            trace_id=trace_id,
        )
        if approval_failure is not None:
            return approval_failure

        if idempotency_key:
            cached = await self._get_cached_result(tenant_id, tool_name, str(idempotency_key))
            if cached is not None:
                return cached

        # Task 2.3: Log tenant context for tools that require it
        if tool.requires_tenant:
            if tenant_id:
                logger.debug(f"Executing tenant-aware tool '{tool_name}' for tenant {tenant_id}")
            else:
                logger.warning(f"Executing tenant-aware tool '{tool_name}' without tenant context")

        # GATE Phase 1: Instrument with TOOL_INVOCATION audit events
        ledger_enabled = os.getenv("AUDIT_LEDGER_MODE") == "enabled"
        request_hash: str | None = None
        start_time: float = 0.0

        if ledger_enabled:
            from value_fabric.shared.crypto.canonical import canonical_hash

            request_hash = canonical_hash({"tool_name": tool_name, "input": input_dict})
            start_time = asyncio.get_running_loop().time()

        response_hash: str | None = None

        result = await self._run_tool_with_context(
            tool=tool,
            tool_name=tool_name,
            input_dict=input_dict,
            request_context=request_context,
            tenant_id=tenant_id,
            trace_id=trace_id,
            workflow_id=workflow_id,
        )
        if idempotency_key:
            await self._set_cached_result(tenant_id, tool_name, str(idempotency_key), result)

        if ledger_enabled:
            from value_fabric.shared.crypto.canonical import canonical_hash as _ch

            response_hash = _ch(result.model_dump())
            elapsed_ms = int((asyncio.get_running_loop().time() - start_time) * 1000)
            self._emit_tool_invocation_audit(
                tool_name=tool_name,
                tool=tool,
                request_hash=request_hash,
                response_hash=response_hash,
                elapsed_ms=elapsed_ms,
                outcome="success" if result.is_success() else "failure",
                tenant_id=tenant_id,
                trace_id=trace_id,
            )

        return result

    @staticmethod
    def _emit_policy_audit_event(
        *,
        workflow_id: str | None,
        tenant_id: str | None,
        user_id: str | None,
        tool_name: str,
        approval_decision: str,
    ) -> None:
        logger.info(
            "tool_policy_decision workflow_id=%s tenant_id=%s user_id=%s tool_name=%s approval_decision=%s",
            workflow_id,
            tenant_id,
            user_id,
            tool_name,
            approval_decision,
        )

    @staticmethod
    def _emit_tool_invocation_audit(
        tool_name: str,
        tool: BaseTool,
        request_hash: str | None,
        response_hash: str | None,
        elapsed_ms: int,
        outcome: str,
        tenant_id: str | None,
        trace_id: str | None,
    ) -> None:
        """Fire-and-forget TOOL_INVOCATION audit event."""
        from value_fabric.shared.audit.emitter import emit_audit_event
        from value_fabric.shared.audit.models import AuditAction, AuditOutcome, ToolInvocationRecord

        record = ToolInvocationRecord(
            tool_name=tool_name,
            tool_manifest_hash=getattr(tool, "manifest_hash", None),
            request_hash=request_hash or "",
            response_hash=response_hash,
            execution_time_ms=elapsed_ms,
            tenant_id=tenant_id,
            trace_id=trace_id,
        )
        asyncio.create_task(
            emit_audit_event(
                action=AuditAction.TOOL_INVOCATION,
                outcome=AuditOutcome.SUCCESS if outcome == "success" else AuditOutcome.FAILURE,
                resource_type="tool",
                resource_id=tool_name,
                tenant_id=UUID(tenant_id) if tenant_id else None,
                request_id=trace_id,
                details=record.model_dump(),
                chain_id=f"{tenant_id or 'global'}:{tool_name}",
            )
        )

    def list_tools(
        self, category: ToolCategory | None = None, search: str | None = None
    ) -> list[ToolSchema]:
        """List available tools with optional filtering.

        Args:
            category: Filter by category
            search: Filter by name/description search term

        Returns:
            List of tool schemas
        """
        tools = list(self._tools.values())

        if category:
            tools = [t for t in tools if t.category == category]

        if search:
            search_lower = search.lower()
            tools = [
                t
                for t in tools
                if search_lower in t.name.lower() or search_lower in t.description.lower()
            ]

        return [t.get_schema() for t in tools]

    def get_all_schemas(self) -> dict[str, ToolSchema]:
        """Get all tool schemas as dictionary.

        Returns:
            Dict mapping tool names to schemas
        """
        return ToolRegistry_get_all_schemasResult.model_validate(
            {name: tool.get_schema() for name, tool in self._tools.items()}
        )

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()


# Global registry instance
_global_registry: ToolRegistry | None = None


def get_global_registry(redis_client: Any | None = None) -> ToolRegistry:
    """Get the global tool registry (creates if needed).

    Args:
        redis_client: Optional async Redis client to back the idempotency cache.
            Only used when the global registry is first created.
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry(redis_client=redis_client)
    return _global_registry


def reset_global_registry() -> None:
    """Reset the global registry (useful for testing)."""
    global _global_registry
    _global_registry = None


def tool(
    name: str,
    category: ToolCategory,
    description: str,
    input_schema: type,
    output_schema: type,
    timeout_seconds: int = 30,
):
    """Decorator to create a tool from a function.

    Example:
        @tool(
            name="multiply",
            category=ToolCategory.CALCULATION,
            description="Multiply two numbers",
            input_schema=MultiplyInput,
            output_schema=MultiplyOutput
        )
        async def multiply(input_data: MultiplyInput) -> MultiplyOutput:
            return MultiplyOutput(result=input_data.a * input_data.b)
    """

    def decorator(func: Callable) -> type[BaseTool]:
        class DynamicTool(BaseTool):
            _name = name
            _category = category
            _description = description
            _input_schema = input_schema
            _output_schema = output_schema
            _timeout = timeout_seconds

            async def execute(self, input_data: Any) -> Any:
                return await func(input_data)

        # Set class attributes
        DynamicTool.name = name
        DynamicTool.category = category
        DynamicTool.description = description
        DynamicTool.input_schema = input_schema
        DynamicTool.output_schema = output_schema
        DynamicTool.timeout_seconds = timeout_seconds

        return DynamicTool

    return decorator


# ═══════════════════════════════════════════════════════════════════════════
# Helper Methods for Testing and Discovery
# ═══════════════════════════════════════════════════════════════════════════


def get_all_tools(registry: ToolRegistry) -> dict[str, Callable]:
    """Get all registered tools.

    Args:
        registry: ToolRegistry instance

    Returns:
        Dictionary mapping tool names to tool functions
    """
    tools = {}
    for tool_instance in registry._tools.values():
        tools[tool_instance.name] = tool_instance.execute
    return tools


def get_tool_metadata(registry: ToolRegistry, tool_name: str) -> dict:
    """Get metadata for a tool.

    Args:
        registry: ToolRegistry instance
        tool_name: Name of tool

    Returns:
        Tool metadata including tenant_scoped flag
    """
    if tool_name not in registry._tools:
        raise ToolNotFoundError(f"Tool {tool_name} not found")

    tool_instance = registry._tools[tool_name]

    # Check if tool is tenant-scoped (has tenant_id parameter)
    import inspect

    sig = inspect.signature(tool_instance.execute)
    tenant_scoped = "tenant_id" in sig.parameters

    return get_tool_metadataResult.model_validate(
        {
            "name": tool_instance.name,
            "category": tool_instance.category,
            "description": tool_instance.description,
            "tenant_scoped": tenant_scoped,
        }
    )


def get_available_tools(registry: ToolRegistry, context: RequestContext) -> list[str]:
    """Get tools available to user based on permissions.

    Args:
        registry: ToolRegistry instance
        context: Request context with permissions

    Returns:
        List of tool names user can access
    """
    available = []

    for tool_name, tool_class in registry._tools.items():
        _metadata = get_tool_metadata(registry, tool_name)

        # Admin-only tools
        admin_tools = {"delete_tenant", "suspend_tenant", "grant_permission"}
        if tool_name in admin_tools:
            if "admin" in context.permissions:
                available.append(tool_name)
            continue

        # Write tools
        write_tools = {"update_entity", "delete_entity"}
        if tool_name in write_tools:
            if "write" in context.permissions or "admin" in context.permissions:
                available.append(tool_name)
            continue

        # Read tools (available to all authenticated users)
        available.append(tool_name)

    return available


# Monkey-patch methods onto ToolRegistry class
ToolRegistry.get_all_tools = lambda self: get_all_tools(self)
ToolRegistry.get_tool_metadata = lambda self, name: get_tool_metadata(self, name)
ToolRegistry.get_available_tools = lambda self, context: get_available_tools(self, context)

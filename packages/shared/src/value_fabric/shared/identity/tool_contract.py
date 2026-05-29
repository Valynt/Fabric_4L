"""Tool contract enforcement for Layer 4 agents.

CONTRACT.md §2.4 - Tool Invocation Boundary
Ensures all tools return structured ToolResult instead of raising exceptions.
"""

from __future__ import annotations

import functools
import inspect
import logging
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar, ParamSpec, Generic

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


@dataclass(frozen=True)
class ToolError:
    """Structured error for tool failures."""

    code: str
    message: str
    recoverable: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolMetadata:
    """Metadata for tool execution."""

    execution_time_ms: float
    tenant_id: str | None
    tool_version: str
    trace_id: str


@dataclass(frozen=True)
class ToolResult(Generic[T]):
    """Canonical tool result structure.

    CONTRACT.md §2.4 - All tools must return this shape.
    """

    status: str  # "success" | "error" | "partial"
    data: T | None = None
    error: ToolError | None = None
    metadata: ToolMetadata | None = None

    @classmethod
    def success(
        cls,
        data: T,
        execution_time_ms: float,
        tenant_id: str | None = None,
        tool_version: str = "1.0.0",
        trace_id: str = "",
    ) -> "ToolResult[T]":
        """Create a success result."""
        return cls(
            status="success",
            data=data,
            metadata=ToolMetadata(
                execution_time_ms=execution_time_ms,
                tenant_id=tenant_id,
                tool_version=tool_version,
                trace_id=trace_id,
            ),
        )

    @classmethod
    def error(
        cls,
        code: str,
        message: str,
        recoverable: bool = False,
        details: dict[str, Any] | None = None,
        execution_time_ms: float = 0.0,
        tenant_id: str | None = None,
        tool_version: str = "1.0.0",
        trace_id: str = "",
    ) -> "ToolResult[Any]":
        """Create an error result."""
        return cls(
            status="error",
            error=ToolError(
                code=code,
                message=message,
                recoverable=recoverable,
                details=details or {},
            ),
            metadata=ToolMetadata(
                execution_time_ms=execution_time_ms,
                tenant_id=tenant_id,
                tool_version=tool_version,
                trace_id=trace_id,
            ),
        )

    @classmethod
    def partial(
        cls,
        data: T,
        code: str,
        message: str,
        execution_time_ms: float,
        tenant_id: str | None = None,
        tool_version: str = "1.0.0",
        trace_id: str = "",
    ) -> "ToolResult[T]":
        """Create a partial success result."""
        return cls(
            status="partial",
            data=data,
            error=ToolError(
                code=code,
                message=message,
                recoverable=True,
            ),
            metadata=ToolMetadata(
                execution_time_ms=execution_time_ms,
                tenant_id=tenant_id,
                tool_version=tool_version,
                trace_id=trace_id,
            ),
        )


class ToolContractViolation(Exception):
    """Raised when a tool violates the canonical contract."""

    pass


def tool(
    name: str | None = None,
    version: str = "1.0.0",
    recoverable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, ToolResult[T]]]:
    """Decorator to enforce ToolResult contract on tool functions.

    CONTRACT.md §2.4 - Tool Invocation Boundary

    This decorator:
    1. Wraps exceptions into structured ToolResult.error()
    2. Measures execution time for metadata
    3. Validates return type is ToolResult
    4. Injects tenant context from request scope

    Args:
        name: Tool name (defaults to function name)
        version: Tool version for metadata
        recoverable_exceptions: Exception types that should be marked recoverable

    Example:
        @tool(name="search_entities", version="1.2.0")
        async def search_entities(query: str) -> ToolResult[list[Entity]]:
            # If this raises, it becomes ToolResult.error()
            results = await db.search(query)
            return ToolResult.success(data=results, ...)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, ToolResult[T]]:
        tool_name = name or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> ToolResult[T]:
            start_time = time.time()
            trace_id = _generate_trace_id()

            # Get tenant context if available
            tenant_id = _get_current_tenant_id()

            try:
                result = await func(*args, **kwargs)

                # If function already returns ToolResult, validate it
                if isinstance(result, ToolResult):
                    return result

                # Wrap raw return in ToolResult.success
                execution_time_ms = (time.time() - start_time) * 1000
                return ToolResult.success(
                    data=result,  # type: ignore
                    execution_time_ms=execution_time_ms,
                    tenant_id=tenant_id,
                    tool_version=version,
                    trace_id=trace_id,
                )

            except Exception as e:
                execution_time_ms = (time.time() - start_time) * 1000
                is_recoverable = isinstance(e, recoverable_exceptions)

                logger.warning(
                    "Tool %s failed: %s (recoverable=%s)",
                    tool_name,
                    repr(e),
                    is_recoverable,
                    exc_info=True,
                )

                return ToolResult.error(
                    code=_exception_to_code(e),
                    message=repr(e),
                    recoverable=is_recoverable,
                    details={
                        "exception_type": type(e).__name__,
                        "traceback": traceback.format_exc(),
                    },
                    execution_time_ms=execution_time_ms,
                    tenant_id=tenant_id,
                    tool_version=version,
                    trace_id=trace_id,
                )

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> ToolResult[T]:
            start_time = time.time()
            trace_id = _generate_trace_id()
            tenant_id = _get_current_tenant_id()

            try:
                result = func(*args, **kwargs)

                if isinstance(result, ToolResult):
                    return result

                execution_time_ms = (time.time() - start_time) * 1000
                return ToolResult.success(
                    data=result,  # type: ignore
                    execution_time_ms=execution_time_ms,
                    tenant_id=tenant_id,
                    tool_version=version,
                    trace_id=trace_id,
                )

            except Exception as e:
                execution_time_ms = (time.time() - start_time) * 1000
                is_recoverable = isinstance(e, recoverable_exceptions)

                logger.warning(
                    "Tool %s failed: %s (recoverable=%s)",
                    tool_name,
                    repr(e),
                    is_recoverable,
                    exc_info=True,
                )

                return ToolResult.error(
                    code=_exception_to_code(e),
                    message=repr(e),
                    recoverable=is_recoverable,
                    details={
                        "exception_type": type(e).__name__,
                        "traceback": traceback.format_exc(),
                    },
                    execution_time_ms=execution_time_ms,
                    tenant_id=tenant_id,
                    tool_version=version,
                    trace_id=trace_id,
                )

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            wrapper = async_wrapper
        else:
            wrapper = sync_wrapper

        # Mark as tool for registry discovery
        wrapper._is_tool = True  # type: ignore
        wrapper._tool_name = tool_name  # type: ignore
        wrapper._tool_version = version  # type: ignore

        return wrapper

    return decorator


def _generate_trace_id() -> str:
    """Generate a unique trace ID for tool execution."""
    import uuid

    return f"tool-{uuid.uuid4().hex[:16]}"


def _get_current_tenant_id() -> str | None:
    """Get tenant ID from current request context if available."""
    try:
        # Try to import and use shared identity context
        from .context import RequestContext

        # This would need integration with async context vars
        # For now, return None - implement based on your context propagation
        return None
    except ImportError:
        return None


def _exception_to_code(e: Exception) -> str:
    """Convert exception to error code."""
    exception_type = type(e).__name__
    code_map = {
        "ValueError": "INVALID_INPUT",
        "TypeError": "TYPE_ERROR",
        "KeyError": "MISSING_KEY",
        "IndexError": "INDEX_OUT_OF_RANGE",
        "AttributeError": "ATTRIBUTE_ERROR",
        "ConnectionError": "CONNECTION_FAILED",
        "TimeoutError": "TIMEOUT",
        "PermissionError": "PERMISSION_DENIED",
        "FileNotFoundError": "NOT_FOUND",
        "NotImplementedError": "NOT_IMPLEMENTED",
    }
    return code_map.get(exception_type, f"{exception_type.upper()}_ERROR")


def is_tool_result(obj: Any) -> bool:
    """Check if object is a valid ToolResult."""
    return isinstance(obj, ToolResult)


def validate_tool_result(result: Any, tool_name: str) -> ToolResult[Any]:
    """Validate and coerce value to ToolResult.

    Raises:
        ToolContractViolation: If result cannot be converted to ToolResult
    """
    if isinstance(result, ToolResult):
        return result

    raise ToolContractViolation(
        f"Tool {tool_name} returned {type(result).__name__} instead of ToolResult. "
        "All tools must return ToolResult.success(), ToolResult.error(), or ToolResult.partial()."
    )


__all__ = [
    "ToolResult",
    "ToolError",
    "ToolMetadata",
    "tool",
    "is_tool_result",
    "validate_tool_result",
    "ToolContractViolation",
]

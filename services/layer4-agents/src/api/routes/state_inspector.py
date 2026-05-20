"""State Inspector API for debugging and analyzing workflow state.

Provides endpoints for:
- Full state retrieval with schema metadata
- State history/audit trail
- Output data inspection
- Error analysis
- Performance metrics per node
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from typing import Any

try:
    from dateutil import parser as dateutil_parser
except ImportError:
    dateutil_parser = None

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from ...engine.executor import OrchestrationController
from .workflows import get_executor

logger = logging.getLogger(__name__)
state_inspector_router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class FieldInfo(BaseModel):
    """Information about a state field."""

    name: str
    type: str
    size_bytes: int | None = None
    is_null: bool = False
    has_default: bool = False
    description: str | None = None


class StateSchemaResponse(BaseModel):
    """State schema with metadata."""

    workflow_id: str = Field(..., alias="workflow_id")
    state_type: str = Field(..., description="Concrete state class name")
    fields: list[FieldInfo]
    required_fields: list[str]
    computed_fields: list[str]
    field_count: int


class StateValueResponse(BaseModel):
    """Full state value with field-by-field breakdown."""

    workflow_id: str = Field(..., alias="workflow_id")
    timestamp: str
    status: str
    current_node: str | None
    values: dict[str, Any] = Field(..., description="Field values keyed by field name")
    value_metadata: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Metadata for each field (type, size, etc.)"
    )


class OutputDataInspectorResponse(BaseModel):
    """Detailed inspection of output_data field."""

    workflow_id: str = Field(..., alias="workflow_id")
    output_keys: list[str]
    output_summary: dict[str, Any]
    data_types: dict[str, str]
    data_sizes: dict[str, int]
    nested_depth: dict[str, int]
    has_large_data: bool
    large_data_keys: list[str]


class ErrorAnalysisResponse(BaseModel):
    """Analysis of workflow errors."""

    workflow_id: str = Field(..., alias="workflow_id")
    error_count: int
    errors: list[dict[str, Any]]
    error_categories: dict[str, int]
    has_critical_errors: bool
    first_error_at: str | None
    last_error_at: str | None
    error_pattern: str | None


class NodeMetrics(BaseModel):
    """Metrics for a single node execution."""

    node_name: str
    execution_count: int
    total_duration_ms: int
    avg_duration_ms: float
    min_duration_ms: int
    max_duration_ms: int
    success_count: int
    error_count: int
    success_rate: float


class PerformanceMetricsResponse(BaseModel):
    """Performance metrics for workflow execution."""

    workflow_id: str = Field(..., alias="workflow_id")
    total_duration_ms: int | None
    node_metrics: list[NodeMetrics]
    slowest_node: str | None
    fastest_node: str | None
    nodes_with_errors: list[str]


class StateHistoryEntry(BaseModel):
    """Single entry in state history."""

    timestamp: str
    node_name: str | None
    status: str
    changed_fields: list[str]
    field_snapshots: dict[str, Any]


class StateHistoryResponse(BaseModel):
    """History of state changes."""

    workflow_id: str = Field(..., alias="workflow_id")
    history: list[StateHistoryEntry]
    total_changes: int
    field_change_frequency: dict[str, int]


# ============================================================================
# API Routes
# ============================================================================


@state_inspector_router.get(
    "/workflows/{workflow_id}/state/schema",
    response_model=StateSchemaResponse,
    tags=["state-inspector"],
)
async def get_state_schema(
    workflow_id: str,
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> StateSchemaResponse:
    """Get the schema of a workflow's state.

    Returns field definitions, types, and metadata for the concrete
    state class (ROIAgentState, WhitespaceAgentState, etc.).

    Example:
        GET /v1/workflows/wf-123/state/schema

        Returns:
        {
            "workflow_id": "wf-123",
            "state_type": "ROIAgentState",
            "fields": [
                {"name": "workflow_id", "type": "str", "is_null": false},
                {"name": "calculation_results", "type": "list", "is_null": false}
            ],
            "required_fields": ["workflow_type", "status"],
            "computed_fields": ["is_paused", "can_resume"],
            "field_count": 15
        }
    """
    state = await executor.state_manager.load_state(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    # Extract schema from Pydantic model
    schema = state.model_json_schema()
    fields = []

    for field_name, field_info in state.model_fields.items():
        annotation = field_info.annotation
        type_name = str(annotation) if annotation else "unknown"

        # Get field value for size estimation
        value = getattr(state, field_name, None)
        size = _estimate_size(value)

        fields.append(
            FieldInfo(
                name=field_name,
                type=type_name,
                size_bytes=size,
                is_null=value is None,
                has_default=field_info.default is not None,
                description=field_info.description,
            )
        )

    # Determine required and computed fields
    required = schema.get("required", [])
    computed = ["is_paused", "can_resume", "pause_summary"]  # Methods that return values

    return StateSchemaResponse(
        workflow_id=workflow_id,
        state_type=state.__class__.__name__,
        fields=fields,
        required_fields=required,
        computed_fields=computed,
        field_count=len(fields),
    )


@state_inspector_router.get(
    "/workflows/{workflow_id}/state/values",
    response_model=StateValueResponse,
    tags=["state-inspector"],
)
async def get_state_values(
    workflow_id: str,
    include_nulls: bool = Query(True, description="Include null-valued fields"),
    max_string_length: int = Query(500, description="Truncate strings longer than this"),
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> StateValueResponse:
    """Get full state values with field-by-field breakdown.

    Returns the complete state with metadata about each field.
    Useful for debugging and understanding current execution state.

    Example:
        GET /v1/workflows/wf-123/state/values?max_string_length=200
    """
    state = await executor.state_manager.load_state(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    state_dict = state.model_dump()
    values = {}
    metadata = {}

    for field_name, value in state_dict.items():
        if value is None and not include_nulls:
            continue

        # Truncate large values
        processed_value = _truncate_value(value, max_string_length)
        values[field_name] = processed_value

        # Build metadata
        metadata[field_name] = {
            "type": type(value).__name__ if value is not None else "None",
            "size_bytes": _estimate_size(value),
            "is_empty": _is_empty(value),
            "has_nested": isinstance(value, (dict, list)) and len(value) > 0 if value else False,
        }

    return StateValueResponse(
        workflow_id=workflow_id,
        timestamp=datetime.now(UTC).isoformat(),
        status=state.status.value if hasattr(state.status, "value") else str(state.status),
        current_node=state.current_node,
        values=values,
        value_metadata=metadata,
    )


@state_inspector_router.get(
    "/workflows/{workflow_id}/state/outputs",
    response_model=OutputDataInspectorResponse,
    tags=["state-inspector"],
)
async def inspect_output_data(
    workflow_id: str,
    max_depth: int = Query(3, description="Maximum recursion depth for nested objects"),
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> OutputDataInspectorResponse:
    """Deep inspection of output_data field.

    Analyzes the accumulated output data, identifying data types,
    sizes, and nested structures. Useful for debugging data flow
    between nodes.

    Example:
        GET /v1/workflows/wf-123/state/outputs

        Returns:
        {
            "workflow_id": "wf-123",
            "output_keys": ["prospect_data", "benchmarks", "calculations"],
            "output_summary": {...},
            "data_types": {"prospect_data": "dict", "benchmarks": "list"},
            "data_sizes": {"prospect_data": 2048, "benchmarks": 1024},
            "nested_depth": {"prospect_data": 3, "benchmarks": 2},
            "has_large_data": false,
            "large_data_keys": []
        }
    """
    state = await executor.state_manager.load_state(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    output_data = state.output_data if hasattr(state, "output_data") else {}

    output_keys = list(output_data.keys())
    data_types = {}
    data_sizes = {}
    nested_depth = {}
    large_data_keys = []

    for key, value in output_data.items():
        data_types[key] = type(value).__name__
        size = _estimate_size(value)
        data_sizes[key] = size
        nested_depth[key] = _calculate_depth(value, max_depth)

        if size > 10000:  # 10KB threshold
            large_data_keys.append(key)

    return OutputDataInspectorResponse(
        workflow_id=workflow_id,
        output_keys=output_keys,
        output_summary=_summarize_output(output_data),
        data_types=data_types,
        data_sizes=data_sizes,
        nested_depth=nested_depth,
        has_large_data=len(large_data_keys) > 0,
        large_data_keys=large_data_keys,
    )


@state_inspector_router.get(
    "/workflows/{workflow_id}/state/errors",
    response_model=ErrorAnalysisResponse,
    tags=["state-inspector"],
)
async def analyze_errors(
    workflow_id: str,
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> ErrorAnalysisResponse:
    """Analyze workflow errors with categorization.

    Provides detailed analysis of all errors encountered during
    workflow execution, categorized by type and severity.

    Example:
        GET /v1/workflows/wf-123/state/errors
    """
    state = await executor.state_manager.load_state(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    errors = state.errors if hasattr(state, "errors") else []

    # Categorize errors
    categories = {}
    categorized_errors = []

    for i, error in enumerate(errors):
        category = _categorize_error(error)
        categories[category] = categories.get(category, 0) + 1

        categorized_errors.append(
            {
                "index": i,
                "error": error,
                "category": category,
                "is_critical": category in ["system", "data"],
            }
        )

    # Find error patterns
    pattern = None
    if len(errors) > 2:
        pattern = _detect_error_pattern(errors)

    return ErrorAnalysisResponse(
        workflow_id=workflow_id,
        error_count=len(errors),
        errors=categorized_errors,
        error_categories=categories,
        has_critical_errors=any(e.get("is_critical") for e in categorized_errors),
        first_error_at=None,  # Would need timestamps in errors
        last_error_at=None,
        error_pattern=pattern,
    )


@state_inspector_router.get(
    "/workflows/{workflow_id}/state/performance",
    response_model=PerformanceMetricsResponse,
    tags=["state-inspector"],
)
async def get_performance_metrics(
    workflow_id: str,
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> PerformanceMetricsResponse:
    """Get performance metrics for workflow execution.

    Analyzes execution history to provide node-level performance metrics
    including duration statistics and error rates.

    Example:
        GET /v1/workflows/wf-123/state/performance
    """
    # Get execution history
    history = await executor.state_manager.get_history(workflow_id, limit=100)

    if not history:
        return PerformanceMetricsResponse(
            workflow_id=workflow_id,
            total_duration_ms=None,
            node_metrics=[],
            slowest_node=None,
            fastest_node=None,
            nodes_with_errors=[],
        )

    # Aggregate metrics per node
    node_stats: dict[str, dict[str, Any]] = {}

    for entry in history:
        node_name = entry.get("node_id", "unknown")
        duration = entry.get("duration_ms", 0)

        if node_name not in node_stats:
            node_stats[node_name] = {"durations": [], "errors": 0, "successes": 0}

        node_stats[node_name]["durations"].append(duration)

        # Check if this entry represents an error
        output_summary = entry.get("output_summary", "")
        if "error" in output_summary.lower():
            node_stats[node_name]["errors"] += 1
        else:
            node_stats[node_name]["successes"] += 1

    # Calculate metrics
    node_metrics = []
    for node_name, stats in node_stats.items():
        durations = stats["durations"]
        total = len(durations)

        node_metrics.append(
            NodeMetrics(
                node_name=node_name,
                execution_count=total,
                total_duration_ms=sum(durations),
                avg_duration_ms=sum(durations) / total if total > 0 else 0,
                min_duration_ms=min(durations) if durations else 0,
                max_duration_ms=max(durations) if durations else 0,
                success_count=stats["successes"],
                error_count=stats["errors"],
                success_rate=stats["successes"] / total if total > 0 else 0,
            )
        )

    # Find extremes
    if node_metrics:
        sorted_by_avg = sorted(node_metrics, key=lambda x: x.avg_duration_ms, reverse=True)
        slowest_node = sorted_by_avg[0].node_name if sorted_by_avg else None
        fastest_node = sorted_by_avg[-1].node_name if sorted_by_avg else None

        nodes_with_errors = [m.node_name for m in node_metrics if m.error_count > 0]
    else:
        slowest_node = fastest_node = None
        nodes_with_errors = []

    # Calculate total duration
    total_duration = None
    if len(history) >= 2 and dateutil_parser:
        first_ts = history[-1].get("timestamp", "")
        last_ts = history[0].get("timestamp", "")
        try:
            first_dt = dateutil_parser.isoparse(first_ts) if first_ts else None
            last_dt = dateutil_parser.isoparse(last_ts) if last_ts else None
            if first_dt and last_dt:
                total_duration = int((last_dt - first_dt).total_seconds() * 1000)
        except (ValueError, TypeError):
            pass

    return PerformanceMetricsResponse(
        workflow_id=workflow_id,
        total_duration_ms=total_duration,
        node_metrics=node_metrics,
        slowest_node=slowest_node,
        fastest_node=fastest_node,
        nodes_with_errors=nodes_with_errors,
    )


@state_inspector_router.get(
    "/workflows/{workflow_id}/state/history",
    response_model=StateHistoryResponse,
    tags=["state-inspector"],
)
async def get_state_history(
    workflow_id: str,
    limit: int = Query(50, ge=1, le=100),
    executor: OrchestrationController = Depends(get_executor),
    _ctx: RequestContext = Depends(require_authenticated),
) -> StateHistoryResponse:
    """Get history of state changes over time.

    Returns a timeline of state changes, showing which fields
    changed at each step of execution.

    Example:
        GET /v1/workflows/wf-123/state/history?limit=20
    """
    history = await executor.state_manager.get_history(workflow_id, limit=limit)

    entries = []
    field_change_frequency: dict[str, int] = {}

    for entry in history:
        node_name = entry.get("node_id")

        # Determine which fields likely changed (based on node type)
        changed_fields = _infer_changed_fields(node_name)

        for field in changed_fields:
            field_change_frequency[field] = field_change_frequency.get(field, 0) + 1

        entries.append(
            StateHistoryEntry(
                timestamp=entry.get("timestamp", datetime.now(UTC).isoformat()),
                node_name=node_name,
                status=entry.get("status", "unknown"),
                changed_fields=changed_fields,
                field_snapshots={"output_summary": entry.get("output_summary", "")},
            )
        )

    return StateHistoryResponse(
        workflow_id=workflow_id,
        history=entries,
        total_changes=len(entries),
        field_change_frequency=field_change_frequency,
    )


# ============================================================================
# Helper Functions
# ============================================================================


def _estimate_size(value: Any) -> int:
    """Estimate memory size of a value in bytes."""
    if value is None:
        return 0
    try:
        return sys.getsizeof(value)
    except (TypeError, ValueError):
        return 0


def _truncate_value(value: Any, max_length: int) -> Any:
    """Truncate large values for display."""
    if isinstance(value, str) and len(value) > max_length:
        return value[:max_length] + f"... ({len(value) - max_length} more chars)"

    if isinstance(value, (list, dict)):
        str_repr = str(value)
        if len(str_repr) > max_length * 2:
            if isinstance(value, list):
                return f"<list[{len(value)}]>"
            else:
                return f"<dict[{len(value)} keys]>"

    return value


def _is_empty(value: Any) -> bool:
    """Check if a value is considered empty."""
    if value is None:
        return True
    if isinstance(value, (list, dict, str)):
        return len(value) == 0
    return False


def _calculate_depth(value: Any, max_depth: int = 5, current_depth: int = 0) -> int:
    """Calculate nesting depth of a value."""
    if current_depth >= max_depth:
        return current_depth

    if isinstance(value, dict):
        if not value:
            return current_depth
        return max(_calculate_depth(v, max_depth, current_depth + 1) for v in value.values())

    if isinstance(value, list):
        if not value:
            return current_depth
        return max(_calculate_depth(v, max_depth, current_depth + 1) for v in value)

    return current_depth


def _summarize_output(output_data: dict) -> dict[str, Any]:
    """Create a summary of output data."""
    summary = {}
    for key, value in output_data.items():
        if isinstance(value, list):
            summary[key] = f"list[{len(value)}]"
        elif isinstance(value, dict):
            summary[key] = f"dict[{len(value)} keys]"
        elif isinstance(value, (int, float)):
            summary[key] = value
        elif isinstance(value, str):
            summary[key] = value[:50] + "..." if len(value) > 50 else value
        else:
            summary[key] = str(value)[:50]
    return summary


def _categorize_error(error: str) -> str:
    """Categorize an error string."""
    error_lower = error.lower()

    if any(x in error_lower for x in ["timeout", "connection", "network", "http"]):
        return "network"
    elif any(x in error_lower for x in ["database", "sql", "query", "db"]):
        return "database"
    elif any(x in error_lower for x in ["validation", "invalid", "schema", "format"]):
        return "validation"
    elif any(x in error_lower for x in ["permission", "auth", "unauthorized", "forbidden"]):
        return "auth"
    elif any(x in error_lower for x in ["llm", "model", "openai", "anthropic"]):
        return "llm"
    elif any(x in error_lower for x in ["keyerror", "indexerror", "typeerror", "attributeerror"]):
        return "code"
    elif any(x in error_lower for x in ["memory", "disk", "cpu", "resource"]):
        return "system"
    else:
        return "other"


def _detect_error_pattern(errors: list[str]) -> str | None:
    """Detect patterns in error messages."""
    if len(errors) < 2:
        return None

    # Check for repeated same error
    if len(set(errors)) == 1:
        return "repeated_same_error"

    # Check for escalation
    categories = [_categorize_error(e) for e in errors]
    if len(set(categories)) > 1:
        return "escalating_different_errors"

    # Check for retry pattern
    if len(errors) >= 3 and len(set(errors[-3:])) == 1:
        return "persistent_error_with_retries"

    return "multiple_distinct_errors"


def _infer_changed_fields(node_name: str | None) -> list[str]:
    """Infer which fields likely changed based on node name."""
    if not node_name:
        return ["unknown"]

    node_field_map = {
        "DOCUMENT_INGESTION": ["input_data", "metadata"],
        "FINANCIAL_EXTRACTION": ["extracted_data", "output_data"],
        "VALUE_TREE_PROJECTION": ["projections", "value_drivers"],
        "WHITESPACE_IDENTIFICATION": ["gaps", "opportunities"],
        "ACCOUNT_PLAN_GENERATION": ["account_plan", "recommendations"],
        "FORMULA_RETRIEVAL": ["formulas", "variables"],
        "ROI_COMPUTATION": ["calculation_results", "aggregated_roi"],
        "OUTPUT_GENERATION": ["final_output", "document"],
    }

    return node_field_map.get(node_name, ["output_data"])

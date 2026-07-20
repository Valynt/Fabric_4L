# Structured Logging Standard — Fabric_4L v1.2.0

> **Audit note (2026-07-18):** The implementation examples reference `fabric4l.observability.logging_config` and a service name pattern (`fabric4l.layer1.ingestion`) that do not match the current shared package layout. The canonical logging module is under `packages/shared/src/value_fabric/shared/observability/`. Update examples before relying on this standard for new services.

**Author:** SRE Team (Staff+)  
**Status:** Production-Ready  
**Enforcement:** Required for all 6 backend layers + frontend  
**Last Updated:** 2024-06-15

---

## Table of Contents

1. [Standard JSON Log Format](#standard-json-log-format)
2. [Mandatory Fields Specification](#mandatory-fields-specification)
3. [Python Implementation (structlog)](#python-implementation-structlog)
4. [Event Catalog](#event-catalog)
5. [Tenant ID Hashing](#tenant-id-hashing)
6. [Trace Context Correlation](#trace-context-correlation)
7. [Validation & Testing](#validation--testing)
8. [Example Log Output](#example-log-output)
9. [Loki Query Patterns](#loki-query-patterns)

---

## Standard JSON Log Format

All services MUST emit JSON-structured logs. No plain text logs are permitted in production.

### Top-Level Schema

```json
{
  "timestamp": "2024-06-15T14:30:00.000Z",
  "level": "INFO",
  "service_name": "fabric4l.layer1.ingestion",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "tenant_id": "a1b2c3d4e5f67890",
  "event": "api.request_completed",
  "message": "Document ingestion request completed successfully",
  "duration_ms": 142.5,
  "request_path": "/api/v1/documents/ingest",
  "response_status": 200,
  "http_method": "POST",
  "user_agent": "Mozilla/5.0...",
  "source_ip": "10.0.1.45",
  "correlation_id": "req-uuid-1234",
  "environment": "production",
  "host": "l1-ingestion-7d9f4b8c5-x2k9m",
  "version": "1.2.0"
}
```

### Field Requirements

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | string (ISO 8601 UTC) | **MANDATORY** | Event timestamp in UTC |
| `level` | enum | **MANDATORY** | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `service_name` | string (FQSN) | **MANDATORY** | Fully-qualified service name |
| `trace_id` | string (32 hex) | **MANDATORY** | OpenTelemetry trace ID or `"null"` |
| `span_id` | string (16 hex) | **MANDATORY** | OpenTelemetry span ID or `"null"` |
| `tenant_id` | string (16 hex) | **MANDATORY** | SHA-256 hashed tenant ID (first 16 chars) |
| `event` | string (snake_case) | **MANDATORY** | Structured event name (see Event Catalog) |
| `message` | string | **MANDATORY** | Human-readable description |
| `duration_ms` | float | optional | Operation duration in milliseconds |
| `request_path` | string | optional | HTTP path or RPC method name |
| `response_status` | integer | optional | HTTP status code or gRPC status code |
| `http_method` | string | optional | HTTP method (GET, POST, etc.) |
| `user_agent` | string | optional | Client user agent |
| `source_ip` | string | optional | Client IP address (anonymized) |
| `correlation_id` | string (UUID) | optional | Request correlation ID |
| `environment` | string | **MANDATORY** | `development`, `staging`, `production` |
| `host` | string | **MANDATORY** | Pod/node hostname |
| `version` | string (semver) | **MANDATORY** | Service version |

---

## Mandatory Fields Specification

### timestamp

```python
# ISO 8601 UTC with millisecond precision
from datetime import datetime, timezone

timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
# Result: "2024-06-15T14:30:00.123Z"
```

### level

| Level | Numeric Value | When to Use |
|-------|--------------|-------------|
| `DEBUG` | 10 | Detailed diagnostics, development only |
| `INFO` | 20 | Normal operations, business events |
| `WARNING` | 30 | Recoverable issues, degraded performance |
| `ERROR` | 40 | Failed operations, exceptions caught |
| `CRITICAL` | 50 | System-wide failures, data loss, security incidents |

### service_name (Fully-Qualified Service Name)

Format: `fabric4l.layer{N}.{service_identifier}`

| Layer | service_name Example |
|-------|---------------------|
| L1 | `fabric4l.layer1.ingestion` |
| L2 | `fabric4l.layer2.extraction` |
| L3 | `fabric4l.layer3.knowledge` |
| L4 | `fabric4l.layer4.agents` |
| L5 | `fabric4l.layer5.groundtruth` |
| L6 | `fabric4l.layer6.benchmarks` |
| Frontend | `fabric4l.frontend.react` |

### trace_id & span_id

Populated from the OpenTelemetry context. If no trace is active, use `"null"`.

### tenant_id

Hashed for privacy. See [Tenant ID Hashing](#tenant-id-hashing) section.

### event

Structured event names using dot-notation. See [Event Catalog](#event-catalog).

---

## Python Implementation (structlog)

### Installation

```txt
# requirements-logging.txt
structlog==24.1.0
python-json-logger==2.0.7
```

### Configuration

Create `fabric4l/observability/logging_config.py`:

```python
"""
Structured logging configuration for Fabric_4L.

Usage:
    from fabric4l.observability.logging_config import configure_logging, get_logger
    configure_logging(service_name="fabric4l.layer1.ingestion", version="1.2.0")
    logger = get_logger()
    logger.info("Document ingested", event="document.ingested", document_id="doc-123")
"""

import hashlib
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from opentelemetry import trace
from structlog.contextvars import merge_contextvars
from structlog.processors import (
    add_log_level,
    dict_tracebacks,
    TimeStamper,
    StackInfoRenderer,
    format_exc_info,
    JSONRenderer,
)
from structlog.stdlib import (
    BoundLogger,
    LoggerFactory,
    add_logger_name,
    ExtraAdder,
    filter_by_level,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
ENVIRONMENT = os.getenv("DEPLOYMENT_ENVIRONMENT", "development")
HOSTNAME = os.getenv("HOSTNAME", "unknown")


# ---------------------------------------------------------------------------
# Custom Processors
# ---------------------------------------------------------------------------

def add_timestamp(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Add ISO 8601 UTC timestamp with millisecond precision."""
    event_dict["timestamp"] = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%f"
    )[:-3] + "Z"
    return event_dict


def add_otel_trace_info(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Add OpenTelemetry trace_id and span_id from current context."""
    span = trace.get_current_span()
    span_context = span.get_span_context()

    if span_context.is_valid:
        event_dict["trace_id"] = format(span_context.trace_id, "032x")
        event_dict["span_id"] = format(span_context.span_id, "016x")
    else:
        event_dict["trace_id"] = "null"
        event_dict["span_id"] = "null"

    return event_dict


def hash_tenant_id(logger: Any, method_name: str, event_dict: dict) -> dict:
    """
    Hash tenant_id for privacy compliance.
    Raw tenant_id should be passed as 'tenant_id_raw' and will be
    replaced with sha256(tenant_id_raw)[:16].
    """
    tenant_id_raw = event_dict.pop("tenant_id_raw", None)
    if tenant_id_raw:
        hashed = hashlib.sha256(str(tenant_id_raw).encode("utf-8")).hexdigest()[:16]
        event_dict["tenant_id"] = hashed
    else:
        event_dict["tenant_id"] = "anonymous"
    return event_dict


def add_service_context(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Add service_name, environment, host, and version."""
    event_dict["environment"] = ENVIRONMENT
    event_dict["host"] = HOSTNAME
    # service_name and version should be set during configuration
    return event_dict


def filter_sensitive_keys(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Remove potentially sensitive keys from log output."""
    SENSITIVE_KEYS = {
        "password", "secret", "token", "api_key", "authorization",
        "credit_card", "ssn", "email", "phone",
    }
    for key in SENSITIVE_KEYS:
        if key in event_dict:
            event_dict[key] = "[REDACTED]"
    return event_dict


def rename_event_key(logger: Any, method_name: str, event_dict: dict) -> dict:
    """
    structlog uses 'event' as the message key by default.
    We keep it but also add a 'message' alias for compatibility.
    """
    if "event" in event_dict and isinstance(event_dict["event"], str):
        event_dict["message"] = event_dict.pop("event")
    return event_dict


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def configure_logging(
    service_name: str,
    version: str = "1.2.0",
    log_level: Optional[str] = None,
) -> None:
    """
    Configure structlog for JSON structured logging.

    Args:
        service_name: Fully-qualified service name (e.g., "fabric4l.layer1.ingestion")
        version: Service semantic version
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    level = (log_level or LOG_LEVEL).upper()

    # Shared processors for both stdlib and structlog
    shared_processors = [
        merge_contextvars,
        filter_by_level,
        add_timestamp,
        add_log_level,
        add_service_context,
        add_otel_trace_info,
        hash_tenant_id,
        filter_sensitive_keys,
        StackInfoRenderer(),
        format_exc_info,
        dict_tracebacks,
    ]

    # Pre-rename processors
    structlog_processors = shared_processors + [
        rename_event_key,
        # Add service_name and version as bound context
    ]

    # Configure structlog
    structlog.configure(
        processors=structlog_processors + [JSONRenderer()],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        context_class=dict,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level),
    )

    # Store service context for all log entries
    structlog.contextvars.bind_contextvars(
        service_name=service_name,
        version=version,
    )


def get_logger(name: Optional[str] = None) -> BoundLogger:
    """Get a configured structlog logger."""
    return structlog.get_logger(name)


# ---------------------------------------------------------------------------
# Context Manager for Request Scoping
# ---------------------------------------------------------------------------

from contextlib import contextmanager
from typing import Generator

@contextmanager
def log_request_context(
    tenant_id: str,
    request_path: str,
    http_method: str = "GET",
    correlation_id: Optional[str] = None,
) -> Generator[None, None, None]:
    """
    Context manager to bind request-scoped fields to all logs within scope.

    Usage:
        with log_request_context(
            tenant_id="tenant-acme",
            request_path="/api/v1/documents",
            http_method="POST",
            correlation_id=str(uuid.uuid4()),
        ):
            logger.info("Processing request", event="request.started")
            # ... all logs in this block will include tenant, path, etc.
            logger.info("Request complete", event="request.completed", duration_ms=150)
    """
    token = structlog.contextvars.bind_contextvars(
        tenant_id_raw=tenant_id,
        request_path=request_path,
        http_method=http_method,
        correlation_id=correlation_id or "auto",
    )
    try:
        yield
    finally:
        structlog.contextvars.unbind_contextvars(
            "tenant_id_raw", "request_path", "http_method", "correlation_id"
        )
```

### FastAPI Integration

```python
"""
FastAPI middleware for automatic request logging with structured events.
"""

import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from fabric4l.observability.logging_config import get_logger, log_request_context

logger = get_logger()


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every request with full structured context.
    """

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))
        tenant_id = request.headers.get("x-tenant-id", "anonymous")
        start_time = time.monotonic()

        with log_request_context(
            tenant_id=tenant_id,
            request_path=request.url.path,
            http_method=request.method,
            correlation_id=correlation_id,
        ):
            logger.info(
                f"{request.method} {request.url.path} started",
                event="api.request_started",
                source_ip=self._anonymize_ip(request.client.host) if request.client else None,
                user_agent=request.headers.get("user-agent", ""),
            )

            try:
                response = await call_next(request)
                duration_ms = (time.monotonic() - start_time) * 1000

                logger.info(
                    f"{request.method} {request.url.path} completed",
                    event="api.request_completed",
                    response_status=response.status_code,
                    duration_ms=round(duration_ms, 2),
                    response_size=len(response.body) if hasattr(response, "body") else 0,
                )
                return response

            except Exception as exc:
                duration_ms = (time.monotonic() - start_time) * 1000
                logger.error(
                    f"{request.method} {request.url.path} failed",
                    event="api.request_failed",
                    response_status=500,
                    duration_ms=round(duration_ms, 2),
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                    exc_info=True,
                )
                raise

    @staticmethod
    def _anonymize_ip(ip: str) -> str:
        """Anonymize IP by removing last octet (IPv4) or last 4 groups (IPv6)."""
        if "." in ip:  # IPv4
            return ".".join(ip.split(".")[:3]) + ".0"
        return ip  # IPv6 — keep as-is for now


# Add to FastAPI app:
# app.add_middleware(StructuredLoggingMiddleware)
```

---

## Event Catalog

### Naming Convention

`{domain}.{subdomain}.{action}`

### Authentication & Authorization

| Event | Level | Description | Additional Fields |
|-------|-------|-------------|-------------------|
| `auth.login_success` | INFO | User login successful | `user_id`, `auth_method` |
| `auth.login_failed` | WARNING | Login attempt failed | `user_id`, `reason`, `source_ip` |
| `auth.logout` | INFO | User logged out | `user_id`, `session_duration_ms` |
| `auth.token_refreshed` | INFO | JWT token refreshed | `user_id` |
| `auth.token_expired` | WARNING | JWT token expired | `user_id` |
| `auth.permission_denied` | WARNING | Authorization check failed | `user_id`, `required_permission`, `resource` |
| `auth.session_created` | INFO | New session created | `user_id`, `session_id` |
| `auth.session_revoked` | INFO | Session revoked | `user_id`, `session_id`, `reason` |

### Database Operations

| Event | Level | Description | Additional Fields |
|-------|-------|-------------|-------------------|
| `db.query_executed` | DEBUG | SQL query executed | `query_hash`, `table`, `rows_affected` |
| `db.query_slow` | WARNING | Query exceeded threshold | `query_hash`, `duration_ms`, `threshold_ms` |
| `db.transaction_committed` | DEBUG | Transaction committed | `transaction_id`, `duration_ms` |
| `db.transaction_rolled_back` | WARNING | Transaction rolled back | `transaction_id`, `reason` |
| `db.connection_acquired` | DEBUG | Connection from pool acquired | `pool_size`, `available` |
| `db.connection_released` | DEBUG | Connection returned to pool | `pool_size`, `available` |
| `db.connection_pool_exhausted` | ERROR | No connections available | `pool_size`, `waiters` |
| `db.migration_applied` | INFO | Schema migration applied | `migration_version`, `direction` |

### API & HTTP

| Event | Level | Description | Additional Fields |
|-------|-------|-------------|-------------------|
| `api.request_started` | INFO | HTTP request received | `source_ip`, `user_agent` |
| `api.request_completed` | INFO | HTTP request completed | `response_status`, `duration_ms` |
| `api.request_failed` | ERROR | HTTP request failed with exception | `response_status`, `error_type` |
| `api.rate_limit_hit` | WARNING | Rate limit exceeded | `limit`, `window`, `retry_after` |
| `api.validation_failed` | WARNING | Request validation failed | `field_errors` |
| `api.timeout` | ERROR | Request timed out | `timeout_ms`, `endpoint` |

### Document Ingestion (L1)

| Event | Level | Description | Additional Fields |
|-------|-------|-------------|-------------------|
| `document.ingest_started` | INFO | Document ingestion started | `document_id`, `source`, `doc_type` |
| `document.ingest_completed` | INFO | Document ingested successfully | `document_id`, `duration_ms`, `size_bytes` |
| `document.ingest_failed` | ERROR | Document ingestion failed | `document_id`, `error_type`, `stage` |
| `document.crawl_started` | INFO | Web crawl started | `url`, `depth`, `max_pages` |
| `document.crawl_completed` | INFO | Web crawl completed | `pages_crawled`, `duration_ms` |
| `document.parse_completed` | INFO | Document parsing completed | `document_id`, `parser`, `extracted_text_bytes` |

### Entity Extraction (L2)

| Event | Level | Description | Additional Fields |
|-------|-------|-------------|-------------------|
| `extraction.pipeline_started` | INFO | Extraction pipeline started | `document_id`, `model` |
| `extraction.entities_found` | INFO | Entities extracted | `document_id`, `entity_count`, `entity_types` |
| `extraction.relations_found` | INFO | Relations extracted | `document_id`, `relation_count` |
| `extraction.pipeline_completed` | INFO | Extraction completed | `document_id`, `duration_ms` |
| `extraction.model_loaded` | INFO | ML model loaded | `model_name`, `load_duration_ms` |

### Knowledge Graph (L3)

| Event | Level | Description | Additional Fields |
|-------|-------|-------------|-------------------|
| `graph.node_created` | DEBUG | Node created in graph | `node_id`, `labels` |
| `graph.node_merged` | DEBUG | Node merged (MERGE) | `node_id`, `labels` |
| `graph.relationship_created` | DEBUG | Relationship created | `start_node`, `end_node`, `rel_type` |
| `graph.query_executed` | DEBUG | Cypher query executed | `query_hash`, `duration_ms` |
| `graph.vector_index_searched` | INFO | Vector similarity search | `query_embedding_size`, `top_k`, `duration_ms` |
| `graph.sync_completed` | INFO | Graph sync completed | `nodes_synced`, `relationships_synced` |

### Agent Workflows (L4)

| Event | Level | Description | Additional Fields |
|-------|-------|-------------|-------------------|
| `agent.workflow_started` | INFO | Workflow execution started | `workflow_id`, `workflow_type`, `trigger` |
| `agent.workflow_step_executed` | DEBUG | Workflow step completed | `workflow_id`, `step_name`, `duration_ms` |
| `agent.workflow_completed` | INFO | Workflow finished successfully | `workflow_id`, `duration_ms`, `step_count` |
| `agent.workflow_failed` | ERROR | Workflow failed | `workflow_id`, `error_type`, `failed_step` |
| `agent.workflow_retrying` | WARNING | Workflow retrying | `workflow_id`, `attempt`, `max_retries` |
| `agent.llm_call_started` | DEBUG | LLM API call started | `provider`, `model`, `prompt_tokens_est` |
| `agent.llm_call_completed` | INFO | LLM API call completed | `provider`, `model`, `prompt_tokens`, `completion_tokens`, `cost_usd` |
| `agent.llm_call_failed` | ERROR | LLM API call failed | `provider`, `model`, `error_type`, `retryable` |
| `agent.tool_called` | DEBUG | External tool invoked | `tool_name`, `parameters` |
| `agent.checkpoint_saved` | DEBUG | Workflow state checkpointed | `workflow_id`, `checkpoint_id` |
| `agent.checkpoint_recovered` | INFO | Workflow recovered from checkpoint | `workflow_id`, `checkpoint_id` |

### Ground Truth (L5)

| Event | Level | Description | Additional Fields |
|-------|-------|-------------|-------------------|
| `validation.task_created` | INFO | Validation task created | `task_id`, `entity_id`, `validator_assigned` |
| `validation.submitted` | INFO | Validation decision submitted | `task_id`, `decision`, `reviewer_id` |
| `validation.overridden` | WARNING | Validation overridden by admin | `task_id`, `original_decision`, `new_decision` |
| `validation.batch_completed` | INFO | Batch validation completed | `batch_id`, `tasks_count`, `accuracy_score` |

### Benchmarks (L6)

| Event | Level | Description | Additional Fields |
|-------|-------|-------------|-------------------|
| `benchmark.run_started` | INFO | Benchmark run started | `benchmark_name`, `dataset_size` |
| `benchmark.iteration_completed` | DEBUG | Single iteration done | `iteration`, `score`, `duration_ms` |
| `benchmark.run_completed` | INFO | Full benchmark done | `benchmark_name`, `avg_score`, `duration_ms` |
| `benchmark.regression_detected` | WARNING | Score below threshold | `benchmark_name`, `score`, `threshold`, `previous_score` |

### System & Infrastructure

| Event | Level | Description | Additional Fields |
|-------|-------|-------------|-------------------|
| `system.startup` | INFO | Service started | `startup_duration_ms`, `config_version` |
| `system.shutdown` | INFO | Service shutting down | `reason`, `uptime_seconds` |
| `system.health_check` | DEBUG | Health check executed | `status`, `checks_passed`, `checks_failed` |
| `system.config_reloaded` | INFO | Configuration reloaded | `config_source` |
| `cache.hit` | DEBUG | Cache hit | `cache_key`, `layer` |
| `cache.miss` | DEBUG | Cache miss | `cache_key`, `layer` |
| `cache.evicted` | WARNING | Cache entry evicted | `cache_key`, `reason` |

---

## Tenant ID Hashing

### Why Hash?

Tenant IDs are hashed to:
1. **Prevent log-based tenant enumeration** (privacy)
2. **Reduce PII exposure** in log aggregation systems
3. **Enable tenant-specific queries** without revealing raw IDs

### Hashing Method

```python
import hashlib

def hash_tenant_id(raw_tenant_id: str) -> str:
    """
    Hash tenant ID using SHA-256, return first 16 hex characters.
    This provides ~64 bits of entropy — enough for correlation
    without being reversible.
    """
    if not raw_tenant_id or raw_tenant_id == "anonymous":
        return "anonymous"
    return hashlib.sha256(raw_tenant_id.encode("utf-8")).hexdigest()[:16]

# Example:
# Input:  "tenant-acme-corp-12345"
# Output: "a3f7b2e1d8c90456"
```

### Correlation

To find logs for a specific tenant, hash the tenant ID locally and query:

```logql
# Loki query for a specific tenant
{service="fabric4l.layer1.ingestion"} | json | tenant_id="a3f7b2e1d8c90456"
```

---

## Trace Context Correlation

All logs must include `trace_id` and `span_id` from the active OpenTelemetry span. This enables:

1. **Trace-to-log correlation:** Click a trace in Jaeger, find related logs in Loki
2. **Log-to-trace correlation:** See a log line, click to view the full trace
3. **Cross-service debugging:** Follow a request through all 6 layers via trace ID

### Integration with structlog

The `add_otel_trace_info` processor (shown in Configuration above) automatically populates these fields.

---

## Validation & Testing

### Log Schema Validation Test

```python
# tests/test_logging.py
import json
import pytest
from fabric4l.observability.logging_config import configure_logging, get_logger

MANDATORY_FIELDS = {
    "timestamp", "level", "service_name", "trace_id", "span_id",
    "tenant_id", "event", "message", "environment", "host", "version",
}

@pytest.fixture(autouse=True)
def setup_logging():
    configure_logging(
        service_name="fabric4l.test",
        version="1.2.0",
        log_level="DEBUG",
    )

class TestStructuredLogging:
    def test_mandatory_fields_present(self, capsys):
        """Every log entry must contain all mandatory fields."""
        logger = get_logger()
        logger.info("Test message", event="test.event", tenant_id_raw="tenant-123")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip().split("\n")[-1])

        missing = MANDATORY_FIELDS - set(log_entry.keys())
        assert not missing, f"Missing mandatory fields: {missing}"

    def test_tenant_id_is_hashed(self, capsys):
        """tenant_id must be hashed, not raw."""
        logger = get_logger()
        logger.info("Test", event="test.event", tenant_id_raw="sensitive-tenant-id")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip().split("\n")[-1])

        assert log_entry["tenant_id"] != "sensitive-tenant-id"
        assert len(log_entry["tenant_id"]) == 16
        assert all(c in "0123456789abcdef" for c in log_entry["tenant_id"])

    def test_sensitive_keys_redacted(self, capsys):
        """Sensitive keys must be redacted."""
        logger = get_logger()
        logger.info("Test", event="test.event", password="secret123", api_key="abc")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip().split("\n")[-1])

        assert log_entry["password"] == "[REDACTED]"
        assert log_entry["api_key"] == "[REDACTED]"

    def test_invalid_level_rejected(self):
        """Only valid log levels are permitted."""
        with pytest.raises((ValueError, KeyError)):
            configure_logging(log_level="INVALID")

    def test_timestamp_format(self, capsys):
        """Timestamp must be ISO 8601 UTC."""
        logger = get_logger()
        logger.info("Test", event="test.event")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip().split("\n")[-1])

        import re
        iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"
        assert re.match(iso_pattern, log_entry["timestamp"])

    def test_event_name_format(self, capsys):
        """Event names must follow dot-notation convention."""
        logger = get_logger()
        logger.info("Test", event="domain.subdomain.action")

        captured = capsys.readouterr()
        log_entry = json.loads(captured.out.strip().split("\n")[-1])

        assert "." in log_entry["event"]
        assert log_entry["event"] == log_entry["event"].lower()
```

---

## Example Log Output

### Successful API request

```json
{
  "timestamp": "2024-06-15T14:30:00.123Z",
  "level": "INFO",
  "service_name": "fabric4l.layer1.ingestion",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "tenant_id": "a3f7b2e1d8c90456",
  "event": "api.request_completed",
  "message": "POST /api/v1/documents/ingest completed",
  "duration_ms": 142.5,
  "request_path": "/api/v1/documents/ingest",
  "response_status": 200,
  "http_method": "POST",
  "response_size": 256,
  "environment": "production",
  "host": "l1-ingestion-7d9f4b8c5-x2k9m",
  "version": "1.2.0"
}
```

### Failed database connection

```json
{
  "timestamp": "2024-06-15T14:31:15.456Z",
  "level": "ERROR",
  "service_name": "fabric4l.layer3.knowledge",
  "trace_id": "7a1b3c5d9e2f4a6b8c0d2e4f6a8b0c2d",
  "span_id": "1a2b3c4d5e6f7890",
  "tenant_id": "anonymous",
  "event": "db.connection_pool_exhausted",
  "message": "PostgreSQL connection pool exhausted",
  "pool_size": 20,
  "waiters": 15,
  "environment": "production",
  "host": "l3-knowledge-3a8f1e7b-x4m2p",
  "version": "1.2.0",
  "exc_info": "Traceback (most recent call last):..."
}
```

### Agent workflow with LLM call

```json
{
  "timestamp": "2024-06-15T14:32:30.789Z",
  "level": "INFO",
  "service_name": "fabric4l.layer4.agents",
  "trace_id": "9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b",
  "span_id": "2b3c4d5e6f7a8901",
  "tenant_id": "b4e8c1f2a5d90367",
  "event": "agent.llm_call_completed",
  "message": "LLM call to openai/gpt-4 completed",
  "provider": "openai",
  "model": "gpt-4",
  "prompt_tokens": 2048,
  "completion_tokens": 512,
  "cost_usd": 0.078,
  "duration_ms": 3200,
  "environment": "production",
  "host": "l4-agents-5c2e8f1a-x7k3m",
  "version": "1.2.0"
}
```

---

## Loki Query Patterns

### Find all errors for a tenant

```logql
{service="fabric4l.layer1.ingestion"}
  | json
  | tenant_id="a3f7b2e1d8c90456"
  | level="ERROR"
```

### Trace a request across all services

```logql
{environment="production"}
  | json
  | trace_id="4bf92f3577b34da6a3ce929d0e0e4736"
```

### Find slow API requests

```logql
{service=~"fabric4l.layer[1-6].*"}
  | json
  | event="api.request_completed"
  | duration_ms > 1000
```

### Count errors by service (last hour)

```logql
sum by (service_name) (
  rate(
    {environment="production"}
      | json
      | level="ERROR"
      [1h]
  )
)
```

### Find tenant isolation events

```logql
{service=~"fabric4l.*"}
  | json
  | event="auth.permission_denied" or event="security.cross_tenant_access"
```

### LLM cost by tenant

```logql
sum by (tenant_id) (
  {service="fabric4l.layer4.agents"}
    | json
    | event="agent.llm_call_completed"
    | unwrap cost_usd [1h]
)
```

---
skill_id: observability-setup
name: observability-setup
version: 1.0.0
description: OpenTelemetry tracing, structured logging, circuit breakers, and monitoring configuration
side_effects: write
timeout_ms: 300000
required_context: [service_configs, monitoring_stack, slos]
allowed_agents: ["infrastructure-operator", "drift-assessor"]
---

# Observability Setup Skill

OpenTelemetry tracing, structured logging, circuit breakers, and monitoring configuration for production observability.

## Features

- **OTel Tracing** - Migrate services to OpenTelemetry SDK
- **Structured Logging** - Standardize on structlog + JSONRenderer
- **Circuit Breakers** - Implement circuit breaker pattern on inter-service calls
- **Connection Pool Monitoring** - Track pool metrics and alert on saturation
- **Jaeger Persistence** - Configure persistent storage for traces
- **SLO Tracking** - Define and track service level objectives with alerts

## Usage Examples

- "Migrate L3 tracer to OpenTelemetry SDK"
- "Configure structured JSON logging for all layers"
- "Implement circuit breaker on HTTP calls"
- "Set up connection pool monitoring"
- "Configure Jaeger with persistent storage"
- "Define SLOs and configure alerts"

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["otel-migrate", "structured-logs", "circuit-breaker", "pool-monitoring", "jaeger-persistence", "slo-setup"]
    },
    "target_services": { "type": "array", "items": { "type": "string" } },
    "config": { "type": "object" }
  },
  "required": ["action"]
}
```

## Output Schema

```json
{
  "type": "object",
  "properties": {
    "services_configured": { "type": "array" },
    "tracing_config": { "type": "object" },
    "logging_config": { "type": "object" },
    "circuit_breaker_rules": { "type": "array" },
    "monitoring_dashboards": { "type": "array" },
    "slo_definitions": { "type": "array" },
    "success": { "type": "boolean" }
  }
}
```

## Observability Gates Supported

- OBS-G-001: All layers emit structured JSON logs
- OBS-G-002: Distributed traces survive restart
- OBS-G-003: All SLOs tracked with alerts
- OBS-G-004: Security alerts fire on attack
- INFRA-G-003: Jaeger persistent storage
- INFRA-G-004: Circuit breaker active

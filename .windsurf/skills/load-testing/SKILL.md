---
skill_id: load-testing
name: load-testing
version: 1.0.0
description: Load testing and performance validation for production launch readiness
side_effects: exec
timeout_ms: 600000
required_context: [deployment_config, performance_targets, infrastructure_capacity]
allowed_agents: ["infrastructure-operator"]
---

# Load Testing Skill

Load testing and performance validation for production launch readiness including traffic simulation, latency validation, and HPA scaling verification.

## Features

- **Traffic Simulation** - Generate load at 2x projected traffic
- **Latency Validation** - Verify p95 latencies <500ms under load
- **Error Rate Monitoring** - Ensure error rate <0.1%
- **HPA Scaling** - Verify horizontal pod autoscaler scales appropriately
- **SLO Validation** - Confirm all service level objectives under load
- **War Room Support** - 72-hour monitoring during production rollout

## Usage Examples

- "Run load test at 2x projected traffic"
- "Validate p95 latency under load"
- "Verify HPA scaling behavior"
- "Monitor error rates during load test"
- "Validate SLOs under production-like load"
- "Set up 72-hour war room monitoring"

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["run-load-test", "validate-latency", "verify-hpa", "monitor-errors", "validate-slos", "war-room-setup"]
    },
    "traffic_multiplier": { "type": "number", "default": 2.0 },
    "duration_minutes": { "type": "number", "default": 30 },
    "target_endpoints": { "type": "array", "items": { "type": "string" } }
  },
  "required": ["action"]
}
```

## Output Schema

```json
{
  "type": "object",
  "properties": {
    "test_report": { "type": "object" },
    "latency_percentiles": { "type": "object" },
    "error_rate": { "type": "number" },
    "hpa_events": { "type": "array" },
    "slo_status": { "type": "object" },
    "recommendations": { "type": "array" },
    "success": { "type": "boolean" }
  }
}
```

## Launch Gates Supported

- LAUNCH-001: Final load testing (2x projected traffic)
- INFRA-G-005: HPA scales under load

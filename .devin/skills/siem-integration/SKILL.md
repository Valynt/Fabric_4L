---
skill_id: siem-integration
name: siem-integration
version: 1.0.0
description: SIEM integration for audit log streaming, security alerting, and compliance monitoring
side_effects: write
timeout_ms: 300000
required_context: [audit_log_schema, siem_config, security_policies]
allowed_agents: ["infrastructure-operator", "security-auditor"]
---

# SIEM Integration Skill

SIEM integration for audit log streaming, security alerting, and compliance monitoring including webhook configuration, schema mapping, and alert validation.

## Features

- **Audit Log Streaming** - Stream audit events to SIEM via webhook
- **Schema Mapping** - Map audit events to SIEM ingestion format
- **Security Alerting** - Configure alerts for attack patterns
- **Compliance Monitoring** - Track compliance events for SOC 2
- **Latency Validation** - Ensure streaming latency <5 minutes
- **Impersonation Auditing** - Track admin impersonation with full audit trail

## Usage Examples

- "Configure audit log streaming to SIEM"
- "Map audit events to SIEM schema"
- "Set up security alerts for BOLA attacks"
- "Validate streaming latency requirements"
- "Configure compliance monitoring for SOC 2"
- "Set up impersonation audit logging"

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["configure-streaming", "map-schema", "setup-alerts", "validate-latency", "compliance-monitoring", "impersonation-audit"]
    },
    "siem_provider": { "type": "string" },
    "webhook_url": { "type": "string" },
    "event_types": { "type": "array", "items": { "type": "string" } },
    "alert_rules": { "type": "array" }
  },
  "required": ["action"]
}
```

## Output Schema

```json
{
  "type": "object",
  "properties": {
    "streaming_config": { "type": "object" },
    "schema_mapping": { "type": "object" },
    "alert_configuration": { "type": "array" },
    "latency_test_results": { "type": "object" },
    "compliance_status": { "type": "object" },
    "audit_trail_config": { "type": "object" },
    "success": { "type": "boolean" }
  }
}
```

## SaaS Gates Supported

- SAAS-G-005: Audit log streaming to SIEM
- OBS-G-004: Security alerts fire on attack

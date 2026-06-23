---
skill_id: security-auditor
name: security-auditor
version: 1.0.0
description: Security auditing for CORS, API key leaks, penetration testing support, and vulnerability scanning
side_effects: none
timeout_ms: 300000
required_context: [security_policies, api_routes, infrastructure_manifests]
allowed_agents: ["code-reviewer", "drift-assessor"]
---

# Security Auditor Skill

Security auditing for production readiness including CORS configuration, API key leakage detection, penetration testing support, and vulnerability scanning.

## Features

- **CORS Configuration Audit** - Verify no wildcard origins with credentials
- **API Key Header Leakage Detection** - Scan responses for X-API-Key-* headers
- **Secret Scanning** - Check for hardcoded secrets in manifests and code
- **WebSocket Auth Validation** - Ensure header-only authentication
- **Penetration Test Support** - Generate test cases for security gates
- **Vault Configuration Audit** - Verify HA mode and auto-unseal

## Usage Examples

- "Audit CORS configuration across all services"
- "Scan for API key header leaks in responses"
- "Check for hardcoded secrets in K8s manifests"
- "Validate WebSocket authentication is header-only"
- "Generate penetration test cases for auth endpoints"

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "audit_type": {
      "type": "string",
      "enum": ["cors", "api-key-leak", "secrets", "websocket-auth", "vault-config", "all"]
    },
    "target_services": { "type": "array", "items": { "type": "string" } },
    "generate_tests": { "type": "boolean", "default": true }
  },
  "required": ["audit_type"]
}
```

## Output Schema

```json
{
  "type": "object",
  "properties": {
    "findings": { "type": "array" },
    "severity_counts": { "type": "object" },
    "test_cases": { "type": "array" },
    "remediation_steps": { "type": "array" },
    "compliance_status": { "type": "string" }
  }
}
```

## Security Gates Supported

- SEC-G-001: CORS wildcard removed
- SEC-G-002: No API key metadata in responses
- SEC-G-004: Zero hardcoded secrets
- SEC-G-006: API keys header-only
- SEC-G-008: WebSocket auth header-only
- SEC-G-009: Security penetration test

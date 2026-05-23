---
skill_id: stripe-integration
name: stripe-integration
version: 1.0.0
description: Stripe billing integration for subscriptions, invoicing, usage metering, and customer portal
side_effects: write
timeout_ms: 300000
required_context: [stripe_config, billing_models, webhooks]
allowed_agents: ["*"]
---

# Stripe Integration Skill

Stripe billing integration for SaaS functionality including subscription lifecycle, usage metering, invoicing, and customer portal management.

## Features

- **Subscription Lifecycle** - Create, cancel, update subscriptions
- **Usage Metering** - Ingest usage events and generate invoices
- **Customer Portal** - Self-service upgrade/downgrade/cancel
- **Webhook Handling** - Process Stripe events with idempotency
- **Impersonation Support** - Admin impersonation with audit trail
- **DSAR Compliance** - Data export for privacy requests

## Usage Examples

- "Create a Stripe subscription for a tenant"
- "Process Stripe webhook events"
- "Set up usage metering for API calls"
- "Configure customer portal for self-service billing"
- "Implement admin impersonation with audit logging"

## Input Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["create-subscription", "cancel-subscription", "update-subscription", "process-webhook", "meter-usage", "configure-portal", "impersonate-user", "export-dsar"]
    },
    "tenant_id": { "type": "string" },
    "subscription_data": { "type": "object" },
    "webhook_event": { "type": "object" },
    "usage_record": { "type": "object" }
  },
  "required": ["action"]
}
```

## Output Schema

```json
{
  "type": "object",
  "properties": {
    "subscription_id": { "type": "string" },
    "invoice_id": { "type": "string" },
    "customer_portal_url": { "type": "string" },
    "usage_report": { "type": "object" },
    "audit_log": { "type": "array" },
    "dsar_package_url": { "type": "string" },
    "success": { "type": "boolean" },
    "error": { "type": "string" }
  }
}
```

## SaaS Gates Supported

- SAAS-G-001: Stripe billing end-to-end
- SAAS-G-002: Customer portal functional
- SAAS-G-003: Usage metering accurate
- SAAS-G-004: Super admin console
- SAAS-G-005: DSAR request completion

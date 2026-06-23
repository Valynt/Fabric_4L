---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# API Documentation

Complete reference for the ValuePact REST API. Use these guides to authenticate, handle errors, paginate results, and integrate programmatically.

## Who this is for

<span class="vp-badge vp-badge--role">Developer</span>
<span class="vp-badge vp-badge--role">Admin</span>

## API guides

| Guide | What you'll learn |
|-------|-----------------|
| [API Overview](overview.md) | Base URL, request format, status codes, idempotency |
| [Authentication](authentication.md) | JWT tokens, SSO, MFA, API keys, permission claims |
| [Rate Limits](rate-limits.md) | Tiered limits, burst behavior, backoff strategies |
| [Errors](errors.md) | Error codes, retry behavior, request IDs |
| [Pagination](pagination.md) | Offset and cursor pagination, sorting, filtering |

## Endpoint reference

| Domain | Description |
|--------|-------------|
| [Initiatives](endpoints/initiatives.md) | Strategic programs |
| [Business Cases](endpoints/business-cases.md) | Value arguments and deliverables |
| [Benefits](endpoints/benefits.md) | Benefit tracking |
| [Stakeholders](endpoints/stakeholders.md) | Stakeholder management |
| [Dashboards](endpoints/dashboards.md) | Dashboard data |
| [Analytics](endpoints/analytics.md) | Analytics and insights |
| [Users](endpoints/users.md) | User profiles |
| [Roles](endpoints/roles.md) | Role and permission management |
| [Integrations](endpoints/integrations.md) | Connector configuration |
| [Webhooks](endpoints/webhooks.md) | Webhook subscriptions |

## Interactive documentation

The [Generated API Docs](generated.md) renders the canonical OpenAPI specification with interactive Swagger UI. You can execute requests directly from the browser.

## SDKs and tools

- **OpenAPI spec**: `/openapi.json` on any service
- **Postman**: Import the OpenAPI spec
- **Swagger UI**: `/docs` on each service

## Getting help

- Check [Errors](errors.md) for error code explanations
- Review [Troubleshooting → Login Issues](../troubleshooting/login-issues.md) for auth problems
- Contact support@valuepact.ai with your `request_id`

## Related pages

- [Integrations → APIs](../integrations/apis.md)
- [Administration → Security → Authentication](../administration/security/authentication.md)

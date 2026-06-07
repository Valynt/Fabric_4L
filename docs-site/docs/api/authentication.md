---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Authentication

ValuePact uses JSON Web Tokens (JWT) for API authentication. Tokens are issued by Clerk and validated by the API gateway on every request.

## Who this is for

<span class="vp-badge vp-badge--role">Developer</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Support</span>

## How authentication works

1. User signs in via Clerk (email/password, SSO, or MFA).
2. Clerk issues a short-lived JWT access token (default 1 hour) and a longer-lived refresh token.
3. Your application includes the access token in the `Authorization: Bearer <token>` header.
4. The API gateway validates the token signature, expiry, and tenant claims.
5. The request proceeds only if all checks pass.

## Token types

| Type | Lifetime | Use |
|------|----------|-----|
| Access token | 1 hour | API requests |
| Refresh token | 7 days | Obtain a new access token |
| Session token | Browser session | Frontend session management |

## Obtaining a token

### Browser applications

Use the Clerk SDK to handle sign-in and token retrieval:

```javascript
import { useAuth } from '@clerk/clerk-react';

const { getToken } = useAuth();
const token = await getToken();
```

### Backend services

Backend services use machine-to-machine authentication with service tokens:

```http
POST /v1/auth/token
Content-Type: application/json

{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "grant_type": "client_credentials"
}
```

Response:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

## Using tokens in requests

Include the token in every API request:

```http
GET /v1/initiatives
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
X-Tenant-ID: your-tenant-id
```

!!! warning "Tenant ID in header"
    The `X-Tenant-ID` header is required for multi-tenant API requests. The API validates that the authenticated user is a member of the specified tenant.

## Token refresh

When an access token expires, use the refresh token to obtain a new one:

```http
POST /v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "your-refresh-token"
}
```

Response:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "new-refresh-token",
  "expires_in": 3600
}
```

!!! tip "Automatic refresh"
    The Clerk JavaScript SDK handles token refresh automatically. For custom implementations, refresh the token when you receive a 401 response.

## Token claims

A valid JWT contains these claims:

| Claim | Description |
|-------|-------------|
| `sub` | User ID |
| `org_id` | Organization (tenant) ID |
| `roles` | Array of role names |
| `permissions` | Array of permission strings |
| `iat` | Issued at timestamp |
| `exp` | Expiration timestamp |

## Permissions

Permissions are granular capabilities assigned to roles:

| Permission | Description |
|------------|-------------|
| `initiatives:read` | View initiatives |
| `initiatives:write` | Create and edit initiatives |
| `initiatives:delete` | Delete initiatives |
| `business_cases:read` | View business cases |
| `business_cases:write` | Create and edit business cases |
| `business_cases:approve` | Approve business cases |
| `analytics:read` | View analytics and reports |
| `admin:users` | Manage users |
| `admin:roles` | Manage roles and permissions |
| `admin:config` | Manage organization settings |

See [Administration → Permissions](../administration/user-management/permissions.md) for the full permission matrix.

## API keys (legacy)

API keys are deprecated in favor of JWT tokens. Existing API keys continue to work but new integrations should use JWT authentication.

```http
GET /v1/initiatives
X-API-Key: vp_live_xxxxxxxxxxxxxxxx
```

## SSO and SAML

For organizations using SSO:

1. Configure SAML or OIDC in [Administration → SSO](../administration/security/sso.md).
2. Users authenticate via your identity provider.
3. Tokens are issued automatically after successful SSO authentication.

## Multi-factor authentication

When MFA is enforced:

1. User provides primary credentials.
2. System prompts for MFA code (TOTP or SMS).
3. After MFA verification, the token is issued.

See [Administration → MFA](../administration/security/mfa.md) for configuration.

## Troubleshooting

??? question "Token rejected with 401"
    **Cause**: Token expired, malformed, or signature invalid.
    **Resolution**: Check token expiry. Refresh the token if expired. Verify the `Authorization` header format is exactly `Bearer <token>`.

??? question "Token valid but 403 returned"
    **Cause**: User lacks permission for the requested operation or tenant.
    **Resolution**: Verify the user's role includes the required permission. Confirm `X-Tenant-ID` matches an organization the user belongs to.

??? question "Refresh token rejected"
    **Cause**: Refresh token expired or was revoked.
    **Resolution**: Re-authenticate the user to obtain a new token pair. Check if the user's session was terminated by an admin.

??? question "CORS errors in browser"
    **Cause**: API requests from browser without proper CORS configuration.
    **Resolution**: Use the Clerk SDK which handles CORS automatically. For custom implementations, ensure your domain is allowlisted in the API gateway CORS policy.

## Limits

<span class="vp-badge vp-badge--limit">Limit</span> Token rate limit: 100 token requests per minute per IP.

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 5 concurrent sessions per user.

## Related pages

- [API Overview](overview.md)
- [Errors](errors.md)
- [Rate Limits](rate-limits.md)
- [Administration → SSO](../administration/security/sso.md)
- [Administration → MFA](../administration/security/mfa.md)
- [Administration → Permissions](../administration/user-management/permissions.md)

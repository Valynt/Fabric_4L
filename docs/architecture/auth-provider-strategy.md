# Auth Provider Strategy

## Overview

Fabric_4L uses an external managed IdP for production and Keycloak for local/dev/integration testing.

## Production: Auth0

### Configuration

**Environment Variables:**
- `AUTH0_DOMAIN`: Auth0 tenant domain (e.g., `your-tenant.auth0.com`)
- `AUTH0_CLIENT_ID`: Auth0 application client ID
- `AUTH0_CLIENT_SECRET`: Auth0 application client secret
- `AUTH0_AUDIENCE`: Auth0 API audience identifier
- `JWT_ALGORITHM`: `RS256` (required for Auth0)

### OIDC Discovery

Auth0 provides standard OIDC discovery endpoints:
- Issuer: `https://{AUTH0_DOMAIN}`
- JWKS URL: `https://{AUTH0_DOMAIN}/.well-known/jwks.json`
- Authorization Endpoint: `https://{AUTH0_DOMAIN}/authorize`
- Token Endpoint: `https://{AUTH0_DOMAIN}/oauth/token`

### Claim Mapping

**Standard Claims:**
- `sub`: User identifier
- `email`: User email
- `name`: User name
- `picture`: User avatar URL

**Custom Claims (configure in Auth0):**
- `tenant_id`: Tenant identifier for multi-tenancy
- `roles`: User roles (admin, user, etc.)
- `permissions`: Granular permissions

### JWT Validation

The JWT validation middleware in `packages/shared/src/value_fabric/shared/identity/middleware.py`:
1. Fetches JWKS from Auth0 discovery endpoint
2. Validates RS256 signature using Auth0 public keys
3. Verifies issuer matches `AUTH0_DOMAIN`
4. Verifies audience matches `AUTH0_AUDIENCE`
5. Extracts tenant_id, roles, and permissions claims

### Auth0 Application Setup

1. **Create Auth0 Application:**
   - Go to Auth0 Dashboard > Applications > Applications > Create Application
   - Choose "Regular Web Application" or "Single Page Application"
   - Set callback URLs for your environment

2. **Configure API:**
   - Go to Auth0 Dashboard > Applications > APIs > Create API
   - Set identifier (this is your `AUTH0_AUDIENCE`)
   - Enable RBAC if using roles/permissions

3. **Add Custom Claims:**
   - Go to Auth0 Dashboard > Rules > Create Rule
   - Add tenant_id, roles, permissions to ID token

4. **Get Credentials:**
   - Copy Domain, Client ID, Client Secret
   - Add to environment variables

## Development: Keycloak

Keycloak remains for local/dev/integration testing only.

### Configuration

**Environment Variables:**
- `KEYCLOAK_URL`: `http://localhost:8080` (default)
- `KEYCLOAK_REALM`: `fabric` (default)
- `KEYCLOAK_ADMIN_USER`: `admin` (default)
- `KEYCLOAK_ADMIN_PASSWORD`: Set in .env for dev

### Dev-Only Warning

The Keycloak deployment in `k8s/dev-only/keycloak-deployment.yaml` is marked as dev-only and should not be used in production.

## Cloud Portability

The JWT validation middleware is OIDC-compliant and can be switched to other IdP providers:

### Okta

**Environment Variables:**
- `OIDC_ISSUER`: `https://{your-okta-domain}.okta.com/oauth2/default`
- `OIDC_AUDIENCE`: `api://{your-audience}`
- `OIDC_JWKS_URL`: `https://{your-okta-domain}.okta.com/oauth2/default/v1/keys`

### Azure AD

**Environment Variables:**
- `OIDC_ISSUER`: `https://login.microsoftonline.com/{tenant-id}/v2.0`
- `OIDC_AUDIENCE`: Azure AD application ID
- `OIDC_JWKS_URL`: `https://login.microsoftonline.com/{tenant-id}/discovery/v2.0/keys`

### Google Identity

**Environment Variables:**
- `OIDC_ISSUER`: `https://accounts.google.com`
- `OIDC_AUDIENCE`: Google OAuth2 client ID
- `OIDC_JWKS_URL`: `https://www.googleapis.com/oauth2/v3/certs`

## Security Requirements

1. **TLS Required**: All IdP communication must use HTTPS
2. **RS256 Algorithm**: Production must use RS256, not HS256
3. **Claim Validation**: Always validate issuer and audience
4. **Token Expiration**: Validate token expiration time
5. **Key Rotation**: JWKS keys rotate automatically via discovery

## IdP Health Monitoring

Add IdP health checks to monitor:
- JWKS endpoint availability
- Token endpoint response time
- Certificate validity

## Migration Path

To switch from Keycloak to Auth0 (or another IdP):

1. Update environment variables
2. No code changes required (OIDC-compliant middleware)
3. Test token validation with new IdP
4. Update user provisioning if needed

## References

- Auth0 Documentation: https://auth0.com/docs
- OIDC Specification: https://openid.net/connect/
- JWT Validation: https://tools.ietf.org/html/rfc7519

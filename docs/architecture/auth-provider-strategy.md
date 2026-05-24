# Auth Provider Strategy

## Overview

Fabric_4L uses an external managed IdP for production and Keycloak for local/dev/integration testing.

## Production: Clerk

### Configuration

**Environment Variables:**
- `CLERK_PUBLISHABLE_KEY`: Clerk publishable key (starts with `pk_test_` or `pk_live_`)
- `CLERK_SECRET_KEY`: Clerk secret key (starts with `sk_test_` or `sk_live_`)
- `CLERK_JWT_ISSUER`: Clerk JWT issuer URL (e.g., `https://clerk.your-domain.com`)
- `CLERK_JWT_AUDIENCE`: Clerk application ID (found in Clerk Dashboard)
- `CLERK_JWKS_URL`: Clerk JWKS endpoint (e.g., `https://clerk.your-domain.com/.well-known/jwks.json`)
- `JWT_ALGORITHM`: `RS256` (required for Clerk)

### OIDC Discovery

Clerk provides standard OIDC-compliant discovery endpoints:
- Issuer: `https://clerk.{your-domain}.com`
- JWKS URL: `https://clerk.{your-domain}.com/.well-known/jwks.json`
- Authorization Endpoint: `https://clerk.{your-domain}/oauth/authorize`
- Token Endpoint: `https://clerk.{your-domain}/oauth/token`

### Claim Mapping

**Standard Claims:**
- `sub`: Clerk user ID
- `email`: User email
- `name`: User first and last name

**Custom Claims (configure in Clerk JWT Template):**
- `tenant_id`: Clerk Organization ID (multi-tenancy)
- `roles`: Clerk Organization role (e.g., `org:admin`, `org:member`)
- `permissions`: Derived from role or custom permissions

### JWT Validation

The JWT validation middleware in `packages/shared/src/value_fabric/shared/identity/middleware.py`:
1. Fetches JWKS from Clerk discovery endpoint
2. Validates RS256 signature using Clerk public keys
3. Verifies issuer matches `CLERK_JWT_ISSUER`
4. Verifies audience matches `CLERK_JWT_AUDIENCE`
5. Extracts tenant_id, roles, and permissions claims

### Clerk Application Setup

1. **Create Clerk Application:**
   - Go to Clerk Dashboard > Create Application
   - Choose application type (Next.js, React, or Generic)
   - Configure organization settings

2. **Configure Organizations (for multi-tenancy):**
   - Go to Clerk Dashboard > Organizations
   - Enable Organizations feature
   - Create organizations for each tenant

3. **Add Custom Claims (JWT Template):**
   - Go to Clerk Dashboard > JWT Templates
   - Create custom template with claims:
     ```json
     {
       "tenant_id": "{{ org.id }}",
       "roles": "{{ org.role }}",
       "permissions": "{{ org.permissions }}"
     }
     ```

4. **Get Credentials:**
   - Copy Publishable Key and Secret Key from API Keys section
   - Copy Application ID for audience
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

### Clerk

**Environment Variables:**
- `CLERK_PUBLISHABLE_KEY`: `pk_live_...` or `pk_test_...`
- `CLERK_SECRET_KEY`: `sk_live_...` or `sk_test_...`
- `CLERK_JWT_ISSUER`: `https://clerk.{your-domain}.com`
- `CLERK_JWT_AUDIENCE`: `{clerk-application-id}`
- `CLERK_JWKS_URL`: `https://clerk.{your-domain}.com/.well-known/jwks.json`

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

### Auth0 to Clerk Migration

To migrate from Auth0 to Clerk:

1. **Update environment variables** (replace Auth0 with Clerk)
2. **Configure Clerk JWT template** to match Auth0 claim structure
3. **Map Clerk Organizations to Value Fabric tenants**
4. **No code changes required** (OIDC-compliant middleware)
5. **Test token validation** with Clerk tokens
6. **Migrate users** from Auth0 to Clerk (export/import)
7. **Update documentation** and runbooks

### Keycloak to Clerk (or another IdP)

1. Update environment variables
2. No code changes required (OIDC-compliant middleware)
3. Test token validation with new IdP
4. Update user provisioning if needed

## References

- Clerk Documentation: https://clerk.com/docs
- Clerk OIDC Integration: https://clerk.com/docs/backend-requests/handling/oidc
- OIDC Specification: https://openid.net/connect/
- JWT Validation: https://tools.ietf.org/html/rfc7519

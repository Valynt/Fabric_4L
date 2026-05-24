---
skill_id: clerk-auth
name: clerk-auth
version: 1.0.0
description: Clerk authentication setup, configuration, and integration for React/Vite and Next.js projects
side_effects: write
timeout_ms: 300000
required_context: [project_graph, frontend/framework, env_config]
allowed_agents: ["*"]
---

# Clerk Authentication Skill

Set up and configure Clerk authentication for Value Fabric projects. Supports React/Vite (current stack) and Next.js.

## When to Use

- Setting up Clerk authentication in a new or existing project
- Configuring Clerk OIDC integration for backend JWT validation
- Migrating from Auth0 or another IdP to Clerk
- Adding sign-in, sign-up, and user management UI components
- Configuring Clerk Organizations for multi-tenancy

## Features

- **CLI Setup** - Install Clerk CLI, authenticate, and initialize
- **SDK Integration** - Install `@clerk/clerk-react` or `@clerk/nextjs`
- **OIDC Configuration** - Configure JWT templates, JWKS endpoints, claim mapping
- **Multi-Tenancy** - Clerk Organizations with role-based access
- **UI Components** - SignInButton, SignUpButton, UserButton, OrganizationSwitcher
- **Environment Config** - Publishable key, secret key, issuer, audience, JWKS URL
- **Backend Validation** - RS256 JWT verification with Clerk public keys

## Input Parameters

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["init", "configure-oidc", "add-components", "migrate-from-auth0", "verify-setup"]
    },
    "framework": {
      "type": "string",
      "enum": ["react", "nextjs", "vite"],
      "default": "react"
    },
    "app_id": {
      "type": "string",
      "description": "Clerk application ID (e.g., app_3E926w2ryugNxxSpjjHbV0UcdTU)"
    },
    "environment": {
      "type": "string",
      "enum": ["development", "staging", "production"],
      "default": "development"
    }
  },
  "required": ["action"]
}
```

## Output

```json
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean" },
    "clerk_config": {
      "type": "object",
      "properties": {
        "publishable_key": { "type": "string" },
        "issuer": { "type": "string" },
        "jwks_url": { "type": "string" },
        "audience": { "type": "string" }
      }
    },
    "files_modified": { "type": "array", "items": { "type": "string" } },
    "next_steps": { "type": "array", "items": { "type": "string" } },
    "error": { "type": "string" }
  }
}
```

## Steps

### 1. Install Clerk CLI

```bash
npm install -g clerk
clerk --version
```

### 2. Authenticate

```bash
clerk auth login
```

### 3. Initialize Project

For existing React/Vite projects:
```bash
clerk init --app <app_id>
```

For new projects or specific framework:
```bash
clerk init --framework <framework> --pm <package_manager> --app <app_id>
```

### 4. Configure Environment Variables

Add to `.env`:
```
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
CLERK_JWT_ISSUER=https://clerk.<your-domain>.com
CLERK_JWT_AUDIENCE=<app_id>
CLERK_JWKS_URL=https://clerk.<your-domain>.com/.well-known/jwks.json
JWT_ALGORITHM=RS256
```

### 5. Configure JWT Template (Dashboard)

In Clerk Dashboard → JWT Templates:
```json
{
  "tenant_id": "{{ org.id }}",
  "roles": "{{ org.role }}",
  "permissions": "{{ org.permissions }}"
}
```

### 6. Add Auth Components

Wrap app with `ClerkProvider`:
```tsx
import { ClerkProvider } from '@clerk/clerk-react'

<ClerkProvider publishableKey={import.meta.env.VITE_CLERK_PUBLISHABLE_KEY}>
  <App />
</ClerkProvider>
```

Add UI controls:
```tsx
import { SignInButton, SignUpButton, UserButton, useAuth } from '@clerk/clerk-react'
```

### 7. Verify Setup

```bash
clerk doctor
```

## Edge Cases

- **No Organizations enabled** - JWT template will not include `org.id`. Enable Organizations in Clerk Dashboard.
- **Missing publishable key** - App will crash on load. Ensure `CLERK_PUBLISHABLE_KEY` is set.
- **CORS issues** - Clerk frontend API must be accessible from your domain. Add allowed origins in Dashboard.
- **Backend validation fails** - Verify `CLERK_JWKS_URL` and `CLERK_JWT_ISSUER` match your Clerk instance.

## Anti-Patterns

- Do NOT expose `CLERK_SECRET_KEY` in client code
- Do NOT use `@clerk/clerk-react` in server-side code (use `@clerk/nextjs` server helpers for Next.js)
- Do NOT skip JWT validation on backend - always verify signatures via JWKS
- Do NOT hardcode Clerk keys in source code - use environment variables

## Related

- [Clerk Docs](https://clerk.com/docs)
- [Clerk React SDK](https://clerk.com/docs/react/overview)
- [Clerk Organizations](https://clerk.com/docs/organizations/overview)
- Auth Provider Strategy: `docs/architecture/auth-provider-strategy.md`

# Clerk Setup for Fabric_4L

This app uses Clerk as the frontend identity provider when `VITE_AUTH_PROVIDER=clerk`.
The frontend app is `apps/web`, built with Vite, React Router, Tailwind, shadcn/ui,
and `@clerk/react`.

## Local Environment

Use local env files only for real keys. They are gitignored.

Frontend:

```env
VITE_AUTH_PROVIDER=clerk
VITE_CLERK_PUBLISHABLE_KEY=pk_test_REPLACE_ME
VITE_CLERK_SIGN_IN_URL=/sign-in
VITE_CLERK_SIGN_UP_URL=/sign-up
VITE_CLERK_AFTER_SIGN_IN_URL=/home
VITE_CLERK_AFTER_SIGN_UP_URL=/onboarding
VITE_CLERK_JWT_TEMPLATE=fabric4l-api
```

Backend/API verification, when enabled:

```env
CLERK_SECRET_KEY=sk_test_REPLACE_ME
CLERK_JWT_AUDIENCE=fabric4l-api
CLERK_AUTHORIZED_PARTIES=http://localhost:3011,http://localhost:3001
```

Do not put `CLERK_SECRET_KEY`, webhook secrets, or JWT private keys in frontend
env files.

## Dashboard Checklist

In the Clerk Dashboard for the Fabric_4L application:

1. Enable email sign-in. The current custom sign-in screen uses Clerk
   email/password via `client.signIn.create({ identifier, password })`.
2. Enable social connections:
   - Google
   - Apple
   - Microsoft
3. Configure development URLs:
   - Application URL: `http://localhost:3011` for the Docker frontend, or
     `http://localhost:3001` for direct Vite dev.
   - Sign-in URL: `/sign-in`
   - Sign-up URL: `/sign-up`
   - OAuth callback URL: `/sso-callback`
   - After sign-in URL: `/home`
   - After sign-up URL: `/onboarding`
4. Enable Organizations for tenant-scoped Fabric workspaces.
5. Confirm users can create or join an organization before entering
   tenant-scoped routes. Existing `RequireClerkAuth`, `AuthContext`, and
   `SelectOrganization` behavior remains authoritative.
6. Configure a JWT template named `fabric4l-api` with audience
   `fabric4l-api` so backend services can verify browser API tokens.

## Runtime Flow

- `/sign-in` renders the custom shadcn-style Clerk login screen.
- Google, Apple, and Microsoft buttons call Clerk OAuth redirect flows with
  `redirectUrl: "/sso-callback"`.
- Email/password submits to Clerk directly and activates the returned session.
- Protected routes still redirect unauthenticated users to `/sign-in` with a
  safe `redirect_url`.
- Signed-in users with no active organization continue through the existing
  organization selection flow.

## Local Verification

```bash
corepack pnpm --dir apps/web exec vitest run src/pages/ClerkSignIn.test.tsx
corepack pnpm --dir apps/web run typecheck
corepack pnpm --dir apps/web run lint
```

For the Docker-backed frontend:

```bash
docker compose -f docker-compose.live.yml up -d --no-deps --force-recreate frontend
```

Then open `http://localhost:3011/sign-in`.

# Backend Connection Audit Checklist

Read this file during Phase 2 (backend connection audit) to ensure all connection surfaces are covered.

## Table of Contents
1. [API Client Layer](#1-api-client-layer)
2. [URL Prefix Mapping](#2-url-prefix-mapping)
3. [Authentication Flow](#3-authentication-flow)
4. [SSE / Streaming Connections](#4-sse--streaming-connections)
5. [OpenAPI Contract Alignment](#5-openapi-contract-alignment)
6. [Environment Variable Coverage](#6-environment-variable-coverage)
7. [Security Checks](#7-security-checks)

---

## 1. API Client Layer

Locate the central HTTP client (e.g., `api/client.ts`). Verify:
- All backend layers (L1–LN) are registered with correct base URLs.
- Auth headers (Bearer token) are injected via a request interceptor, not per-call.
- Error responses (401, 403, 5xx) are handled centrally with appropriate redirects.
- No page or hook calls `fetch()` or `axios` directly — all calls go through the client.

```bash
grep -rn "fetch(\|axios\." src/ --include="*.ts" --include="*.tsx" | grep -v "api/client"
```

---

## 2. URL Prefix Mapping

For each backend layer, verify the frontend prefix matches the backend router's `prefix=` value.

| Layer | Frontend default | Backend `prefix=` | Match? |
|-------|-----------------|-------------------|--------|
| L1    | `/ingest`       | `/v1/ingest`      | ❌ example mismatch |
| L2    | `/extract`      | `/v1/extract`     | check  |
| L3    | `/graph`        | `/v1/graph`       | check  |
| L4    | `/agents`       | `/v1/agents`      | check  |

**How to check backend prefix:**
```bash
grep -rn "prefix=" services/ --include="*.py" | grep "APIRouter\|include_router"
```

A `/v1` discrepancy means every API call from that layer will 404 in production.

---

## 3. Authentication Flow

Trace the full OIDC/OAuth flow:

1. **Login initiation:** Does the frontend construct the authorization URL correctly? Check `redirect_uri` matches what the backend OIDC router expects.
2. **Callback handling:** Does the frontend callback route (`/login/callback`) match the backend's registered redirect URI?
3. **Token storage:** Are tokens stored in `httpOnly` cookies (secure) or `localStorage` (XSS risk)?
4. **Token refresh:** Is there a refresh token flow? What happens on 401?
5. **Logout:** Does logout clear both frontend state and invalidate the server-side session?

```bash
grep -rn "redirect_uri\|callback\|token\|logout" src/contexts/AuthContext.tsx
```

---

## 4. SSE / Streaming Connections

For each SSE hook, verify:
- The SSE endpoint URL matches the backend's `@router.get(...)` path.
- There is a polling fallback when `EventSource` is unavailable.
- The `EventSource` is closed in the `useEffect` cleanup function.
- Timeout handling closes the connection and falls back gracefully.
- Auth credentials are passed (SSE cannot use Authorization headers — use cookies or query params).

```bash
grep -rn "new EventSource\|SSEBuilders\|buildSSEUrl" src/ --include="*.ts"
```

---

## 5. OpenAPI Contract Alignment

If the project has OpenAPI specs, compare frontend calls against the spec:

```bash
# Extract all paths from OpenAPI spec
python3 -c "
import yaml, sys
spec = yaml.safe_load(open(sys.argv[1]))
for path in spec.get('paths', {}):
    for method in spec['paths'][path]:
        print(f'{method.upper()} {path}')
" contracts/openapi/layer1.yaml
```

Check for:
- Paths the frontend calls that are not in the spec (will 404).
- Paths in the spec that the frontend never calls (dead backend endpoints).
- Request/response shape mismatches (field names, required vs optional).

---

## 6. Environment Variable Coverage

List all `VITE_` env vars referenced in source and verify each is documented in `.env.example` or `.env.development`:

```bash
grep -rh "import\.meta\.env\.VITE_" src/ --include="*.ts" --include="*.tsx" \
  | grep -oP 'VITE_\w+' | sort -u
```

Missing env vars silently fall back to hardcoded defaults, which may point to wrong hosts in production.

---

## 7. Security Checks

| Check | Command |
|-------|---------|
| Hardcoded secrets / API keys | `grep -rn "sk-\|Bearer \|api_key\s*=" src/` |
| `localStorage` token storage (XSS risk) | `grep -rn "localStorage\.set\|localStorage\.get" src/` |
| `dangerouslySetInnerHTML` usage | `grep -rn "dangerouslySetInnerHTML" src/` |
| Missing CSRF protection on mutations | Check if POST/PUT/DELETE calls include CSRF token header |
| Open redirect in auth callback | Verify `redirect_uri` is validated against an allowlist |
| RouteGuard fail-open | See `refactor-patterns.md` Pattern 8 |

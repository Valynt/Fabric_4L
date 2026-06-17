# Settings Area Robustness — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the settings area tenant-context aware, fix navigation drift, add API-key creation, and wire the personal profile form to a new `/me` backend endpoint.

**Architecture:** A small path-builder layer transforms canonical global route templates into tenant-aware paths. `SettingsLayout` consumes the transformed paths. `PermissionsAdmin` gains a real create-key dialog. A new backend `/v1/users/me` surface lets users update their own display name, and the profile page is rewritten with RHF/Zod.

**Tech Stack:** React Router v6, TypeScript, TanStack Query, React Hook Form, Zod, shadcn/ui, FastAPI, SQLAlchemy async.

---

## File map

| File | Responsibility |
|---|---|
| `apps/web/src/app/settings/useSettingsTenantSlug.ts` | Derive active tenant slug. |
| `apps/web/src/app/settings/pathBuilder.ts` | Transform global templates to tenant-aware paths. |
| `apps/web/src/app/settings/SettingsLayout.tsx` | Use tenant-aware paths. |
| `apps/web/src/app/settings/pages/PersonalProfile.tsx` | RHF/Zod profile form. |
| `apps/web/src/hooks/useCurrentUser.ts` | Fetch/update current user. |
| `apps/web/src/hooks/useGovernance.ts` | Add `useCreateApiKey`. |
| `apps/web/src/pages/admin/PermissionsAdmin.tsx` | Add create-key dialog, fix tab detection. |
| `services/layer4-agents/src/layer4_agents/tenants/api/routes/users.py` | Add `/me` routes. |
| `services/layer4-agents/src/layer4_agents/tenants/service.py` | Add `get_current_user`, `update_current_user`. |
| `services/layer4-agents/tests/test_tenants/test_users.py` | Tests for `/me` endpoints. |
| `apps/web/src/app/settings/pathBuilder.test.ts` | Tests for path builder. |

---

## Task 1: Backend — add `/v1/users/me` endpoints

**Files:**
- Modify: `services/layer4-agents/src/layer4_agents/tenants/service.py`
- Modify: `services/layer4-agents/src/layer4_agents/tenants/api/routes/users.py`
- Test: `services/layer4-agents/tests/test_tenants/test_users.py`

- [ ] **Step 1: Add service helpers**

Add to `service.py`:

```python
async def get_current_user(db: AsyncSession, tenant_id: UUID, user_id: UUID) -> UserModel | None:
    return await get_user(db, tenant_id, user_id)

async def update_current_user(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    request: UserUpdateRequest,
) -> UserModel | None:
    user = await get_user(db, tenant_id, user_id)
    if not user:
        return None
    if request.display_name is not None:
        user.display_name = request.display_name
    user.updated_at = datetime.now(UTC)
    await db.flush()
    return _user_to_model(user)
```

- [ ] **Step 2: Add routes**

In `users.py`, after imports, add dependency and routes:

```python
from value_fabric.shared.identity.dependencies import require_authenticated

@router.get("/me", response_model=UserModel)
async def api_get_current_user(
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> UserModel:
    if not ctx.user_id:
        raise AuthorizationError(message="Authenticated user ID is required")
    user = await get_current_user(db, UUID(ctx.tenant_id), UUID(ctx.user_id))
    if not user:
        raise NotFoundError(message="Current user not found")
    return user

@router.patch("/me", response_model=UserModel)
async def api_update_current_user(
    request: UserUpdateRequest,
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> UserModel:
    if not ctx.user_id:
        raise AuthorizationError(message="Authenticated user ID is required")
    if request.role is not None or request.status is not None:
        raise AuthorizationError(message="Role and status can only be changed by tenant admins")
    user = await update_current_user(db, UUID(ctx.tenant_id), UUID(ctx.user_id), request)
    if not user:
        raise NotFoundError(message="Current user not found")
    return user
```

- [ ] **Step 3: Write backend tests**

Add tests that assert:
- `GET /v1/users/me` returns the authenticated user.
- `PATCH /v1/users/me` updates `display_name`.
- `PATCH /v1/users/me` with `role` is rejected.

Run: `pytest services/layer4-agents/tests/test_tenants/test_users.py -v`

---

## Task 2: Frontend — tenant-aware path builder

**Files:**
- Create: `apps/web/src/app/settings/useSettingsTenantSlug.ts`
- Create: `apps/web/src/app/settings/pathBuilder.ts`
- Test: `apps/web/src/app/settings/pathBuilder.test.ts`

- [ ] **Step 1: Create `useSettingsTenantSlug.ts`**

```ts
import { useParams } from "react-router-dom";
import { useAuthContext } from "@/contexts/AuthContext";

export function useSettingsTenantSlug(): string | null {
  const params = useParams<{ tenantSlug?: string }>();
  const { currentTenantSlug } = useAuthContext();
  return params.tenantSlug ?? currentTenantSlug ?? null;
}
```

- [ ] **Step 2: Create `pathBuilder.ts`**

```ts
const TENANT_SCOPED_PREFIXES = [
  "/settings",
  "/personal", // personal remains global; keep for completeness
];

export function withTenantPrefix(path: string, tenantSlug: string | null): string {
  if (!tenantSlug) return path;
  if (path.startsWith("/t/")) return path;
  if (path.startsWith("/settings/")) return `/t/${tenantSlug}${path}`;
  if (path === "/settings") return `/t/${tenantSlug}/settings`;
  return path;
}
```

- [ ] **Step 3: Add unit tests**

Assert global paths pass through and tenant paths are prefixed.

Run: `pnpm --dir apps/web test --run src/app/settings/pathBuilder.test.ts`

---

## Task 3: Update `SettingsLayout` to use tenant-aware paths

**Files:**
- Modify: `apps/web/src/app/settings/SettingsLayout.tsx`

- [ ] **Step 1: Use `useSettingsTenantSlug` and `withTenantPrefix`**

Replace hard-coded `cat.basePath` and `item.path` usage with tenant-aware versions.

- [ ] **Step 2: Fix active category detection**

Active detection should compare against tenant-aware paths and also match the current tenant pathname.

- [ ] **Step 3: Fix audit trail link**

Build audit link with tenant prefix: tenant-aware path is `/t/:tenantSlug/settings/governance/audit`, global fallback is `/settings/governance/audit-trail`.

---

## Task 4: Add API key creation

**Files:**
- Modify: `apps/web/src/hooks/useGovernance.ts`
- Modify: `apps/web/src/pages/admin/PermissionsAdmin.tsx`

- [ ] **Step 1: Add `useCreateApiKey`**

```ts
export interface CreateApiKeyPayload {
  name: string;
  role: string;
  expires_at?: string;
}

export interface CreatedApiKey {
  key_id: string;
  name: string;
  api_key: string;
  prefix: string;
  role: string;
  expires_at?: string;
  created_at: string;
}

export function useCreateApiKey() {
  const queryClient = useQueryClient();
  return useMutation<CreatedApiKey, GovernanceApiError, CreateApiKeyPayload>({
    mutationFn: async (payload) => {
      const response = await apiPost<CreatedApiKey>("l4", "/api-keys", payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.governance.apiKeys() });
    },
  });
}
```

- [ ] **Step 2: Add `CreateApiKeyDialog`**

Inline in `PermissionsAdmin.tsx`. Fields: name input, role select, optional expiration date input. Submit calls `useCreateApiKey`. On success, show a read-only textarea with the raw key and a copy button.

- [ ] **Step 3: Enable the "New API Key" button**

Change the primary action button to open the create-key dialog when `activeTab === "api-keys"`.

- [ ] **Step 4: Fix tab detection for tenant paths**

Update `getTabFromPath` to also detect `/t/:tenantSlug/settings/api-keys` and `/t/:tenantSlug/settings/users`.

---

## Task 5: Wire personal profile form

**Files:**
- Create: `apps/web/src/hooks/useCurrentUser.ts`
- Modify: `apps/web/src/app/settings/pages/PersonalProfile.tsx`

- [ ] **Step 1: Create `useCurrentUser.ts`**

```ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPatch } from "@/api/typedClient";
import { QK } from "./queryKeys";
import { withApiError, BaseApiError, STALE_TIME, RETRY_CONFIG } from "./useApiShared";

export interface CurrentUser {
  id: string;
  email: string;
  display_name?: string;
  role: string;
}

export class CurrentUserApiError extends BaseApiError { ... }

export function useCurrentUser() { ... }
export function useUpdateCurrentUser() { ... }
```

- [ ] **Step 2: Refactor `PersonalProfile.tsx` to RHF/Zod**

Use `Form`, `FormField`, `FormItem`, `FormLabel`, `FormControl`, `FormMessage`, `Input`, and `Btn`. Schema validates display name length and email format (read-only email can be displayed separately).

- [ ] **Step 3: Submit to `/v1/users/me`**

On submit, call `updateCurrentUser.mutateAsync({ display_name: values.fullName })`.

---

## Task 6: Validation

- [ ] Run backend tests: `pytest services/layer4-agents/tests/test_tenants/test_users.py -v`
- [ ] Run frontend unit tests: `pnpm --dir apps/web test --run`
- [ ] Run typecheck: `pnpm --dir apps/web typecheck`
- [ ] Run lint: `pnpm --dir apps/web lint`

## Follow-up work
- Persist user notification preferences in a new `user_settings` table/column.
- Add domain/DNS verification UI for custom domains.
- Add custom role creation and SCIM provisioning.

# Settings Area Robustness — Design

## Goal
Make the Value Fabric settings area tenant-context aware, eliminate navigation drift between global and tenant-scoped routes, and add the missing API-key creation flow so the settings surface behaves like a B2B enterprise SaaS control plane.

## Scope

### In scope
1. **Tenant-aware settings navigation**
   - `SettingsLayout` must render correct category tabs, subnav links, and active states for both global (`/personal/*`, `/settings/*`) and tenant-scoped (`/t/:tenantSlug/settings/*`) routes.
   - Right-rail "View audit trail" link must point to the correct audit route for the current context.
2. **API key creation**
   - The existing `PermissionsAdmin` page already lists keys but disables the "New API Key" action.
   - Add a creation dialog (name, role, optional expiration), wire it to `POST /v1/api-keys`, and display the one-time raw key with copy/reveal.
3. **Form hygiene on the Personal Profile page**
   - Replace raw `<input>`/`<select>` elements with the project’s React Hook Form + Zod pattern.
   - Load current user identity from `AuthContext` and submit the profile update to a new backend `/v1/users/me` endpoint that lets a user update their own `display_name`.

### Out of scope (follow-up work)
- Full user notification preferences backend (no persisted user-level settings column yet).
- Billing contact/tax settings and plan upgrades.
- Custom role creation and SCIM.
- Domain/DNS verification UI.

## Architecture

### Navigation model
- Keep `settingsRoutes`, `settingsNavigation`, and `settingsCategories` in `schemas.ts` as the canonical **global path templates**.
- Introduce `useSettingsTenantSlug()` to derive the active tenant slug from the route (`useParams`) or `AuthContext`.
- Introduce `makeTenantAwarePaths(tenantSlug)` to transform global templates into tenant-scoped paths when `tenantSlug` is present.
- `SettingsLayout` consumes the transformed paths for category tabs, subnav, and active-state logic.

### API key creation
- Add `useCreateApiKey()` to `apps/web/src/hooks/useGovernance.ts`.
- Add a small `CreateApiKeyDialog` component inside `PermissionsAdmin` for the creation form and one-time reveal.
- Reuse existing shadcn/ui Dialog, Input, Select, and Btn primitives.

### Personal profile update
- Add backend route `GET /v1/users/me` and `PATCH /v1/users/me` in `services/layer4-agents/src/layer4_agents/tenants/api/routes/users.py`.
- The PATCH endpoint updates the calling user’s `display_name` (and later can be extended for notification preferences).
- Add `useCurrentUser()` / `useUpdateCurrentUser()` hooks in the frontend.
- Refactor `PersonalProfile.tsx` to use `react-hook-form` + `zod` and submit to the new endpoint.

## Components & Files

| File | Responsibility |
|---|---|
| `apps/web/src/app/settings/schemas.ts` | Canonical global path templates (unchanged). |
| `apps/web/src/app/settings/useSettingsTenantSlug.ts` | Derive active tenant slug from route or auth context. |
| `apps/web/src/app/settings/pathBuilder.ts` | Transform global templates to tenant-aware paths. |
| `apps/web/src/app/settings/SettingsLayout.tsx` | Use tenant-aware paths; fix active states; fix audit link. |
| `apps/web/src/hooks/useGovernance.ts` | Add `useCreateApiKey()` mutation. |
| `apps/web/src/pages/admin/PermissionsAdmin.tsx` | Add `CreateApiKeyDialog`, enable "New API Key" action, fix tab detection for tenant paths. |
| `services/layer4-agents/src/layer4_agents/tenants/api/routes/users.py` | Add `/me` GET/PATCH routes. |
| `services/layer4-agents/src/layer4_agents/tenants/service.py` | Add `get_current_user`, `update_current_user`. |
| `apps/web/src/hooks/useCurrentUser.ts` | Fetch and update current user profile. |
| `apps/web/src/app/settings/pages/PersonalProfile.tsx` | RHF/Zod form wired to current user hook. |

## Data Flow

### Navigation
```
URL: /t/acme/settings/api-keys
useSettingsTenantSlug() -> "acme"
makeTenantAwarePaths("acme") -> category billing: "/t/acme/settings/billing"
SettingsLayout renders category tabs with tenant-aware base paths.
Subnav links point to tenant-aware child paths.
Active detection matches current pathname.
```

### API key creation
```
User clicks "New API Key" -> Dialog opens
User enters name, role, optional expiry -> Submit
useCreateApiKey POSTs /v1/api-keys
On success: display one-time key, invalidate keys query
On error: show form-level error
```

### Profile update
```
PersonalProfile mounts -> loads user from AuthContext / useCurrentUser
User edits display name -> RHF validation
Submit -> PATCH /v1/users/me
On success -> toast + invalidate user query
```

## Error Handling
- Navigation helpers fail closed: if tenant slug cannot be resolved, fall back to global paths.
- API key creation errors are surfaced in the dialog with retry.
- Profile update displays field-level validation and form-level backend errors.

## Testing
- Frontend unit tests for `pathBuilder.ts` (global and tenant path generation).
- Component test for `CreateApiKeyDialog` copy/reveal behavior.
- Update existing `TeamAccessPages.test.tsx` to assert creation flow.
- Backend tests for `/v1/users/me` GET/PATCH in Layer 4 tenant tests.
- Run `pnpm --dir apps/web typecheck`, `pnpm --dir apps/web lint`, and `pnpm --dir apps/web test`.

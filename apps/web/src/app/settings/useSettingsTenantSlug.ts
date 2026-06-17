import { useParams } from "react-router-dom";
import { useAuthContext } from "@/contexts/AuthContext";

/**
 * Resolve the active tenant slug for the settings shell.
 *
 * When the user is on a tenant-scoped route (e.g. `/t/acme/settings/api-keys`)
 * the slug comes from the URL. Otherwise fall back to the authenticated user's
 * current tenant so that global `/settings/*` links can still redirect into the
 * active workspace context.
 */
export function useSettingsTenantSlug(): string | null {
  const params = useParams<{ tenantSlug?: string }>();
  const { currentTenantSlug } = useAuthContext();
  return params.tenantSlug ?? currentTenantSlug ?? null;
}

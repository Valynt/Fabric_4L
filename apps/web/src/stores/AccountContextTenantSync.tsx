/**
 * AccountContextTenantSync — keeps accountContextStore scoped to the current tenant.
 *
 * Responsibilities:
 *   1. On tenant mount/change: load the previous account selection from
 *      tenant-prefixed localStorage (or clear if no prior selection).
 *   2. On account selection change: persist to tenant-prefixed localStorage.
 *   3. On tenant switch: clear the in-memory store so the previous tenant's
 *      selected account is not leaked into the new tenant's UI.
 *
 * This component renders nothing. Mount it once inside AuthProvider.
 */
import { useEffect, useRef } from "react";
import { useAuthContext } from "@/contexts/AuthContext";
import {
  useAccountContextStore,
  loadAccountContextForTenant,
  saveAccountContextForTenant,
} from "./accountContextStore";

export function AccountContextTenantSync(): null {
  const { user } = useAuthContext();
  const tenantId = user?.tenantId ?? null;

  // Track previous tenant to detect switches
  const prevTenantRef = useRef<string | null>(null);

  // Load persisted selection when tenant becomes known or changes
  useEffect(() => {
    if (!tenantId) {
      // No tenant context — clear selection to fail closed
      useAccountContextStore.setState({ selectedAccountId: null });
      prevTenantRef.current = null;
      return;
    }

    const prevTenant = prevTenantRef.current;
    if (prevTenant !== tenantId) {
      // Tenant switch detected — load new tenant's persisted context
      loadAccountContextForTenant(tenantId);
      prevTenantRef.current = tenantId;
    }
  }, [tenantId]);

  // Persist selection changes to localStorage (scoped by tenant)
  useEffect(() => {
    if (!tenantId) return;

    const unsubscribe = useAccountContextStore.subscribe((state) => {
      saveAccountContextForTenant(tenantId);
    });

    return unsubscribe;
  }, [tenantId]);

  return null;
}

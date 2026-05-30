import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { getActiveClerkOrgId } from "@/auth/clerkSession";

interface AccountContextState {
  selectedAccountId: string | null;
  /** Tenant ID captured at last write — used to detect cross-tenant stale data. */
  _persistedTenantId: string | null;
  setSelectedAccountId: (accountId: string | null) => void;
  clearSelectedAccountId: () => void;
  /**
   * Call this whenever the active tenant may have changed (e.g. in ClerkAuthBridge
   * after `setActiveClerkOrgId`).  Clears persisted account selection if the
   * tenant has switched so stale data from a previous tenant is never exposed.
   */
  syncTenant: () => void;
}

export const useAccountContextStore = create<AccountContextState>()(
  persist(
    (set, get) => ({
      selectedAccountId: null,
      _persistedTenantId: null,
      setSelectedAccountId: accountId =>
        set({ selectedAccountId: accountId, _persistedTenantId: getActiveClerkOrgId() }),
      clearSelectedAccountId: () => set({ selectedAccountId: null, _persistedTenantId: null }),
      syncTenant: () => {
        const currentTenantId = getActiveClerkOrgId();
        if (get()._persistedTenantId !== currentTenantId) {
          // Tenant changed — clear any persisted account selection to prevent
          // cross-tenant data leakage.
          set({ selectedAccountId: null, _persistedTenantId: currentTenantId });
        }
      },
    }),
    {
      name: "fabric-account-context",
      // Use sessionStorage so data is automatically cleared when the tab closes.
      // This limits the blast radius of any residual cross-tenant leakage to the
      // current browser tab / session.
      storage: createJSONStorage(() => sessionStorage),
      partialize: state => ({
        selectedAccountId: state.selectedAccountId,
        _persistedTenantId: state._persistedTenantId,
      }),
    }
  )
);

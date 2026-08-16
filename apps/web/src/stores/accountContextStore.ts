import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";
import {
  ACCOUNT_CONTEXT_STORAGE_KEY,
  ACCOUNT_CONTEXT_STORAGE_VERSION,
  type AccountContextState,
  type PersistedAccountContext,
} from "@fabric/platform-contract/stores";

function removePersistedContext(): void {
  try {
    sessionStorage.removeItem(ACCOUNT_CONTEXT_STORAGE_KEY);
  } catch {
    // Browser storage is untrusted and may be unavailable; memory still clears.
  }
}

function readPersistedContext(): PersistedAccountContext | null {
  try {
    const raw: unknown = JSON.parse(sessionStorage.getItem(ACCOUNT_CONTEXT_STORAGE_KEY) ?? "null");
    if (!raw || typeof raw !== "object") return null;
    const envelope = raw as { state?: unknown; version?: unknown };
    if (envelope.version !== ACCOUNT_CONTEXT_STORAGE_VERSION) return null;
    if (!envelope.state || typeof envelope.state !== "object") return null;
    const state = envelope.state as Record<string, unknown>;
    if (
      Object.keys(state).some(key => key !== "fabricTenantId" && key !== "selectedAccountId") ||
      typeof state.fabricTenantId !== "string" ||
      (state.selectedAccountId !== null && typeof state.selectedAccountId !== "string")
    ) return null;
    return {
      fabricTenantId: state.fabricTenantId,
      selectedAccountId: state.selectedAccountId as string | null,
    };
  } catch {
    return null;
  }
}

function clearedState(): Pick<AccountContextState, "fabricTenantId" | "selectedAccountId" | "authorizationStatus"> {
  return { fabricTenantId: null, selectedAccountId: null, authorizationStatus: "unverified" };
}

export const useAccountContextStore = create<AccountContextState>()(
  persist(
    (set, get) => ({
      ...clearedState(),
      setSelectedAccountId: accountId => {
        const state = get();
        if (!isClerkAuthEnabled()) {
          set({ selectedAccountId: accountId });
          return;
        }
        if (state.authorizationStatus !== "verified" || !state.fabricTenantId) return;
        set({ selectedAccountId: accountId });
      },
      clearSelectedAccountId: () => {
        if (!isClerkAuthEnabled()) {
          set({ selectedAccountId: null });
          return;
        }
        if (get().authorizationStatus !== "verified") {
          set(clearedState());
          removePersistedContext();
          return;
        }
        set({ selectedAccountId: null });
      },
      authorizationIdentityChanged: () => {
        set(clearedState());
        removePersistedContext();
      },
      authorizationVerified: fabricTenantId => {
        const persisted = readPersistedContext();
        if (persisted?.fabricTenantId !== fabricTenantId) removePersistedContext();
        set({
          fabricTenantId,
          selectedAccountId:
            persisted?.fabricTenantId === fabricTenantId ? persisted.selectedAccountId : null,
          authorizationStatus: "verified",
        });
      },
      authorizationUnavailable: () => {
        set(clearedState());
        removePersistedContext();
      },
    }),
    {
      name: ACCOUNT_CONTEXT_STORAGE_KEY,
      version: ACCOUNT_CONTEXT_STORAGE_VERSION,
      storage: createJSONStorage(() => sessionStorage),
      partialize: state => ({
        fabricTenantId: state.fabricTenantId,
        selectedAccountId: state.selectedAccountId,
      }),
      skipHydration: isClerkAuthEnabled(),
    }
  )
);

export type { AccountContextState } from "@fabric/platform-contract/stores";

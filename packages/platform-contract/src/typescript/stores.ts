/** Canonical client-side presentation-store contracts. */

export const ACCOUNT_CONTEXT_STORAGE_KEY = "fabric-account-context-v1" as const;
export const ACCOUNT_CONTEXT_STORAGE_VERSION = 1 as const;

/** Untrusted session payload. It never represents an authorization grant. */
export interface PersistedAccountContext {
  fabricTenantId: string | null;
  selectedAccountId: string | null;
}

export type AccountAuthorizationStatus = "unverified" | "verified";

export interface AccountContextState extends PersistedAccountContext {
  authorizationStatus: AccountAuthorizationStatus;
  setSelectedAccountId: (id: string | null) => void;
  clearSelectedAccountId: () => void;
  authorizationIdentityChanged: () => void;
  authorizationVerified: (fabricTenantId: string) => void;
  authorizationUnavailable: () => void;
}

export type StoreSelector<T, R> = (state: T) => R;

import {
  ACCOUNT_CONTEXT_STORAGE_KEY,
  ACCOUNT_CONTEXT_STORAGE_VERSION,
  type AccountContextState,
  type PersistedAccountContext,
  type StoreSelector,
} from "@fabric/platform-contract/stores";

const persisted: PersistedAccountContext = {
  fabricTenantId: "tenant-1",
  selectedAccountId: "acc-1",
};

const exactKey: "fabric-account-context-v1" = ACCOUNT_CONTEXT_STORAGE_KEY;
const exactVersion: 1 = ACCOUNT_CONTEXT_STORAGE_VERSION;

const selector: StoreSelector<AccountContextState, string | null> = (state) =>
  state.selectedAccountId;

const accountState = null as unknown as AccountContextState;
accountState.authorizationVerified("tenant-1");
accountState.setSelectedAccountId("acc-1");
accountState.clearSelectedAccountId();
accountState.authorizationIdentityChanged();
accountState.authorizationUnavailable();

void selector;
void persisted;
void exactKey;
void exactVersion;

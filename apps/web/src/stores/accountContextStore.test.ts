import { beforeEach, describe, expect, it } from "vitest";
import {
  ACCOUNT_CONTEXT_STORAGE_KEY,
  ACCOUNT_CONTEXT_STORAGE_VERSION,
} from "@fabric/platform-contract/stores";
import { useAccountContextStore } from "./accountContextStore";

function seed(state: unknown, version = ACCOUNT_CONTEXT_STORAGE_VERSION): void {
  sessionStorage.setItem(
    ACCOUNT_CONTEXT_STORAGE_KEY,
    JSON.stringify({ state, version })
  );
}

describe("accountContextStore authorization lifecycle", () => {
  beforeEach(() => {
    sessionStorage.clear();
    useAccountContextStore.getState().authorizationUnavailable();
  });

  it("does not expose or persist a selected account before verification", () => {
    useAccountContextStore.getState().setSelectedAccountId("acct_untrusted");
    expect(useAccountContextStore.getState().selectedAccountId).toBeNull();
    expect(sessionStorage.getItem(ACCOUNT_CONTEXT_STORAGE_KEY)).toBeNull();
  });

  it("persists only the verified Fabric tenant and selected account", () => {
    useAccountContextStore.getState().authorizationVerified("fabric-tenant-a");
    useAccountContextStore.getState().setSelectedAccountId("acct_a");

    expect(
      JSON.parse(sessionStorage.getItem(ACCOUNT_CONTEXT_STORAGE_KEY)!)
    ).toEqual({
      state: { fabricTenantId: "fabric-tenant-a", selectedAccountId: "acct_a" },
      version: ACCOUNT_CONTEXT_STORAGE_VERSION,
  });
  });

  it("restores only after an exact verified Fabric tenant match", () => {
    seed({ fabricTenantId: "fabric-tenant-a", selectedAccountId: "acct_a" });
    expect(useAccountContextStore.getState().selectedAccountId).toBeNull();

    useAccountContextStore.getState().authorizationVerified("fabric-tenant-a");
    expect(useAccountContextStore.getState().selectedAccountId).toBe("acct_a");
  });

  it("rejects tenant-switched and tampered storage", () => {
    seed({
      fabricTenantId: "fabric-tenant-a",
      selectedAccountId: "acct_a",
      clerkOrgId: "org-b",
  });
    useAccountContextStore.getState().authorizationVerified("fabric-tenant-b");

    expect(useAccountContextStore.getState().selectedAccountId).toBeNull();
    expect(
      JSON.parse(sessionStorage.getItem(ACCOUNT_CONTEXT_STORAGE_KEY)!)
    ).toEqual({
      state: { fabricTenantId: "fabric-tenant-b", selectedAccountId: null },
      version: ACCOUNT_CONTEXT_STORAGE_VERSION,
    });
  });

  it.each([
    ["malformed JSON", "{bad-json"],
    [
      "wrong version",
      JSON.stringify({
        state: {
          fabricTenantId: "fabric-tenant-a",
          selectedAccountId: "acct_a",
        },
        version: 999,
      }),
    ],
    [
      "invalid fields",
      JSON.stringify({
        state: { fabricTenantId: 7, selectedAccountId: { id: "acct_a" } },
        version: ACCOUNT_CONTEXT_STORAGE_VERSION,
      }),
    ],
  ])("fails closed for %s", (_label, raw) => {
    sessionStorage.setItem(ACCOUNT_CONTEXT_STORAGE_KEY, raw);
    useAccountContextStore.getState().authorizationVerified("fabric-tenant-a");
    expect(useAccountContextStore.getState().selectedAccountId).toBeNull();
    expect(
      JSON.parse(sessionStorage.getItem(ACCOUNT_CONTEXT_STORAGE_KEY)!)
    ).toEqual({
      state: { fabricTenantId: "fabric-tenant-a", selectedAccountId: null },
      version: ACCOUNT_CONTEXT_STORAGE_VERSION,
    });
  });

  it("clears memory and storage synchronously on session or organization change", () => {
    useAccountContextStore.getState().authorizationVerified("fabric-tenant-a");
    useAccountContextStore.getState().setSelectedAccountId("acct_a");

    useAccountContextStore.getState().authorizationIdentityChanged();

    expect(useAccountContextStore.getState()).toMatchObject({
      fabricTenantId: null,
      selectedAccountId: null,
      authorizationStatus: "unverified",
    });
    expect(sessionStorage.getItem(ACCOUNT_CONTEXT_STORAGE_KEY)).toBeNull();
  });

  it.each(["denied", "expired", "unauthenticated"])(
    "clears memory and storage when authorization is %s",
    () => {
      useAccountContextStore
        .getState()
        .authorizationVerified("fabric-tenant-a");
      useAccountContextStore.getState().setSelectedAccountId("acct_a");
      useAccountContextStore.getState().authorizationUnavailable();
      expect(useAccountContextStore.getState().selectedAccountId).toBeNull();
      expect(sessionStorage.getItem(ACCOUNT_CONTEXT_STORAGE_KEY)).toBeNull();
    }
  );

  it("cannot restore through delayed Zustand hydration after an identity reset", async () => {
    seed({ fabricTenantId: "fabric-tenant-a", selectedAccountId: "acct_a" });
    useAccountContextStore.getState().authorizationIdentityChanged();
    await useAccountContextStore.persist.rehydrate();
    expect(useAccountContextStore.getState().selectedAccountId).toBeNull();
    expect(sessionStorage.getItem(ACCOUNT_CONTEXT_STORAGE_KEY)).toBeNull();
  });
});

import { describe, expect, it, vi } from "vitest";
import {
  authorizationSnapshotQueryKey,
  resolveRouteAccountId,
  shouldHoldAuthorizationLoading,
  synchronizeAccountAuthorization,
} from "./AuthorizationProvider";

describe("authorizationSnapshotQueryKey", () => {
  it("binds tenant authorization to the exact Clerk session and organization", () => {
    expect(authorizationSnapshotQueryKey("sess_1", "org_1", null)).toEqual([
      "authorization-snapshot",
      "1",
      "sess_1",
      "org_1",
      "tenant",
    ]);
  });

  it("includes the normalized exact account scope", () => {
    expect(
      authorizationSnapshotQueryKey("sess_1", "org_1", " acc_1 ")
    ).toEqual([
      "authorization-snapshot",
      "1",
      "sess_1",
      "org_1",
      "account:acc_1",
    ]);
  });
});

describe("resolveRouteAccountId", () => {
  it("uses the deepest matched child account parameter", () => {
    expect(
      resolveRouteAccountId(
        [
          { params: {} },
          { params: { tenantSlug: "acme", accountId: " child-account " } },
        ],
        "persisted-account"
      )
    ).toBe("child-account");
  });

  it("falls back to the verified persisted selection outside account routes", () => {
    expect(
      resolveRouteAccountId([{ params: { tenantSlug: "acme" } }], " saved ")
    ).toBe("saved");
  });
});

describe("shouldHoldAuthorizationLoading", () => {
  it("keeps authorization pending while an expired snapshot is refetched", () => {
    expect(
      shouldHoldAuthorizationLoading({
        ready: true,
        identityReady: true,
        isPending: false,
        isFetching: true,
      })
    ).toBe(true);
  });
});

describe("synchronizeAccountAuthorization", () => {
  it("publishes verified tenant identity to the account context", () => {
    const authorizationVerified = vi.fn();
    const authorizationUnavailable = vi.fn();

    synchronizeAccountAuthorization(
      {
        status: "verified",
        snapshot: {
          tenant: { fabricTenantId: "tenant_1" },
        },
      },
      { authorizationVerified, authorizationUnavailable }
    );

    expect(authorizationVerified).toHaveBeenCalledWith("tenant_1");
    expect(authorizationUnavailable).not.toHaveBeenCalled();
  });

  it.each(["denied", "expired"] as const)(
    "clears account context for a %s resolution",
    status => {
      const authorizationVerified = vi.fn();
      const authorizationUnavailable = vi.fn();

      synchronizeAccountAuthorization(
        { status, snapshot: null },
        { authorizationVerified, authorizationUnavailable }
      );

      expect(authorizationUnavailable).toHaveBeenCalledOnce();
      expect(authorizationVerified).not.toHaveBeenCalled();
    }
  );
});

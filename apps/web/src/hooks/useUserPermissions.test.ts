import { describe, expect, it } from "vitest";
import { decideUserPermissions } from "./useUserPermissions";
import type { AuthorizationSnapshotState } from "./useAuthorizationSnapshot";

const verified: AuthorizationSnapshotState = {
  status: "verified",
  snapshot: {
    tenantId: "id",
    tenantSlug: "tenant-a",
    role: "org:member",
    expiresAt: "2099-01-01T00:00:00.000Z",
    permissions: ["account:read"],
    entitlements: [],
    tenantMember: true,
    accountIds: ["acc-1"],
  },
  permissions: ["account:read"],
  entitlements: [],
};

describe("decideUserPermissions", () => {
  it("keeps a verified snapshot distinct from a denied permission decision", () => {
    expect(decideUserPermissions(verified, ["admin:manage"])).toEqual({
      status: "denied",
      reason: "missing_permission",
    });
    expect(verified.status).toBe("verified");
  });

  it("allows only grants present in the verified snapshot", () => {
    expect(decideUserPermissions(verified, ["account:read"])).toEqual({
      status: "allowed",
    });
  });

  it("propagates loading, denied fetch, and expiration without grants", () => {
    expect(
      decideUserPermissions(
        { status: "loading", permissions: [], entitlements: [] },
        []
      )
    ).toEqual({ status: "loading" });
    expect(
      decideUserPermissions(
        {
          status: "denied",
          reason: "snapshot_fetch_failed",
          permissions: [],
          entitlements: [],
        },
        []
      )
    ).toEqual({ status: "denied", reason: "snapshot_fetch_failed" });
    expect(
      decideUserPermissions(
        {
          status: "expired",
          reason: "snapshot_expired",
          permissions: [],
          entitlements: [],
        },
        []
      )
    ).toEqual({ status: "expired", reason: "snapshot_expired" });
  });
});

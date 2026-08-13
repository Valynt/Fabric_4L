import { describe, expect, it } from "vitest";
import { parseAuthorizationSnapshot } from "./useAuthorizationSnapshot";

const valid = {
  tenantId: "tenant-id",
  tenantSlug: "tenant-a",
  role: "org:member",
  expiresAt: "2099-01-01T00:00:00.000Z",
  permissions: ["account:read"],
  entitlements: ["feature.a"],
  tenantMember: true,
  accountIds: ["acc-1"],
};

describe("parseAuthorizationSnapshot", () => {
  it("exposes grants only for a current tenant-matched verified snapshot", () => {
    expect(parseAuthorizationSnapshot(valid, "tenant-a").status).toBe(
      "verified"
    );
  });

  it.each([
    ["missing snapshot", undefined, "denied"],
    ["malformed claims", { ...valid, permissions: "account:read" }, "denied"],
    ["unexpected Clerk role", { ...valid, role: "org:unexpected" }, "denied"],
    ["tenant mismatch", valid, "denied", "tenant-b"],
    [
      "expired snapshot",
      { ...valid, expiresAt: "2020-01-01T00:00:00.000Z" },
      "expired",
    ],
  ])("fails closed for %s", (_name, snapshot, status, tenant = "tenant-a") => {
    const result = parseAuthorizationSnapshot(snapshot, tenant);
    expect(result.status).toBe(status);
    expect(result.permissions).toEqual([]);
    expect(result.entitlements).toEqual([]);
  });
});

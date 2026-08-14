import { describe, expect, it } from "vitest";
import {
  decideAuthorization,
  deniedAuthorization,
  parseAuthorizationSnapshot,
  type AuthorizationSnapshot,
} from "./authorizationSnapshot";

const future = new Date(Date.now() + 60_000).toISOString();
const valid = {
  tenantId: "tenant-1",
  tenantSlug: "tenant-a",
  role: "org:custom-role",
  expiresAt: future,
  permissions: ["account:read", "signals:read"],
  entitlements: ["reports"],
  tenantMember: true,
  accountIds: ["account-1"],
};

describe("authorization snapshot boundary", () => {
  it("verifies a current tenant-matched snapshot without a role allowlist", () => {
    const resolution = parseAuthorizationSnapshot(valid, "tenant-a");
    expect(resolution.status).toBe("verified");
    expect(resolution.permissions).toEqual(valid.permissions);
  });

  it.each([
    undefined,
    { ...valid, permissions: "account:read" },
    { ...valid, entitlements: [""] },
    { ...valid, accountIds: [1] },
    { ...valid, tenantId: "" },
    { ...valid, expiresAt: "invalid" },
    { ...valid, tenantMember: false },
  ])("fails closed for missing or malformed payload %#", payload => {
    expect(parseAuthorizationSnapshot(payload, "tenant-a").status).toBe(
      "denied"
    );
  });

  it("fails closed for tenant mismatch and expiry", () => {
    expect(parseAuthorizationSnapshot(valid, "tenant-b").status).toBe("denied");
    const expired = parseAuthorizationSnapshot(
      { ...valid, expiresAt: new Date(0).toISOString() },
      "tenant-a"
    );
    expect(expired).toEqual({
      status: "expired",
      permissions: [],
      entitlements: [],
    });
  });

  it("allows only a verified snapshot containing every required grant and scope", () => {
    const resolution = parseAuthorizationSnapshot(valid, "tenant-a");
    expect(
      decideAuthorization(resolution, {
        permissions: ["account:read"],
        entitlements: ["reports"],
        tenantMember: true,
        accountId: "account-1",
      }).status
    ).toBe("allowed");
    expect(
      decideAuthorization(resolution, { permissions: ["admin:write"] }).status
    ).toBe("denied");
    expect(resolution.status).toBe("verified");
  });

  it("never exposes grants from non-verified states or feature flags", () => {
    expect(deniedAuthorization.permissions).toEqual([]);
    expect(decideAuthorization(deniedAuthorization, {}, true).status).toBe(
      "denied"
    );
    const resolution = parseAuthorizationSnapshot(valid, "tenant-a");
    expect(decideAuthorization(resolution, {}, false).status).toBe("denied");
  });
});

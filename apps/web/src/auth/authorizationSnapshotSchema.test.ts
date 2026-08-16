import { describe, expect, it } from "vitest";
import { parseAuthorizationCandidate } from "./authorizationSnapshotSchema";

const candidate = {
  schemaVersion: "1",
  source: "backend",
  identity: {
    clerkUserId: "user_1",
    fabricUserId: "u1",
    sessionDiscriminator: "sess_1",
  },
  tenant: {
    fabricTenantId: "ten_1",
    clerkOrganizationId: "org_1",
    tenantSlug: "acme",
    membershipId: "mem_1",
    membershipStatus: "active",
  },
  accountScope: { scopeType: "account", accountId: "acc_1" },
  roles: ["tenant_admin"],
  permissions: ["account:read"],
  entitlements: ["billing.manage"],
  issuedAt: "2026-08-14T00:00:00.000Z",
  expiresAt: "2026-08-14T00:05:00.000Z",
};

describe("parseAuthorizationCandidate", () => {
  it("accepts only an exact current identity and scope tuple", () => {
    expect(
      parseAuthorizationCandidate(candidate, {
        clerkUserId: "user_1",
        sessionDiscriminator: "sess_1",
        clerkOrganizationId: "org_1",
        fabricTenantId: "ten_1",
        accountId: "acc_1",
        now: new Date("2026-08-14T00:01:00.000Z"),
      }).status
    ).toBe("verified");
  });

  it.each([
    ["unknown role", { ...candidate, roles: ["super_admin"] }],
    [
      "session mismatch",
      {
        ...candidate,
        identity: { ...candidate.identity, sessionDiscriminator: "other" },
      },
    ],
    [
      "account mismatch",
      { ...candidate, accountScope: { scopeType: "tenant", accountId: null } },
    ],
    [
      "fabric tenant mismatch",
      {
        ...candidate,
        tenant: { ...candidate.tenant, fabricTenantId: "other_tenant" },
      },
    ],
  ])("denies %s", (_name, value) => {
    expect(
      parseAuthorizationCandidate(value, {
        clerkUserId: "user_1",
        sessionDiscriminator: "sess_1",
        clerkOrganizationId: "org_1",
        fabricTenantId: "ten_1",
        accountId: "acc_1",
        now: new Date("2026-08-14T00:01:00.000Z"),
      }).status
    ).toBe("denied");
  });

  it("accepts the legacy Playwright contract-mode snapshot", async () => {
    const { verifiedLegacyAuthorizationSnapshot } = await import(
      "../../e2e/helpers/verified-authorization-snapshot"
    );
    const now = new Date("2026-08-16T04:30:00.000Z");
    const result = parseAuthorizationCandidate(
      verifiedLegacyAuthorizationSnapshot(now),
      {
        clerkUserId: "legacy",
        sessionDiscriminator: "legacy",
        clerkOrganizationId: "legacy",
        fabricTenantId: "legacy",
        accountId: null,
        now,
      }
    );
    expect(result.status).toBe("verified");
  });

  it("classifies an expired candidate without exposing it", () => {
    const result = parseAuthorizationCandidate(candidate, {
      clerkUserId: "user_1",
      sessionDiscriminator: "sess_1",
      clerkOrganizationId: "org_1",
      fabricTenantId: "ten_1",
      accountId: "acc_1",
      now: new Date("2026-08-14T00:06:00.000Z"),
    });
    expect(result).toEqual({
      status: "expired",
      snapshot: null,
      expiredAt: candidate.expiresAt,
    });
  });
});

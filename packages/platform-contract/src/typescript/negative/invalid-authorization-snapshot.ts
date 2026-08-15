import type {
  AuthorizationResolution,
  AuthorizationSnapshot,
} from "@fabric/platform-contract/authorization-snapshot";

const invalidRole: AuthorizationSnapshot = {
  principalId: "user-1",
  sessionDiscriminator: "session-1",
  tenant: { id: "tenant-1", slug: "tenant-one" },
  accountScope: { kind: "tenant" },
  roles: ["unknown_role"],
  permissions: [],
  entitlements: [],
  source: "backend",
  issuedAt: "2026-08-14T18:00:00Z",
  expiresAt: "2026-08-14T19:00:00Z",
};

const deniedWithSnapshot: AuthorizationResolution = {
  status: "denied",
  snapshot: invalidRole,
  reason: "policy_denied",
};

void deniedWithSnapshot;

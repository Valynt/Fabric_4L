import type {
  AuthorizationResolution,
  AuthorizationSnapshot,
} from "@fabric/platform-contract/authorization-snapshot";

const snapshot: AuthorizationSnapshot = {
  principalId: "user_123",
  sessionDiscriminator: "session-binding-123",
  tenant: { id: "tenant-123", slug: "acme" },
  accountScope: { kind: "account", accountId: "account-123" },
  roles: ["tenant_admin"],
  permissions: ["accounts:read"],
  entitlements: [{ key: "advanced-analytics", expiresAt: "2026-08-15T00:00:00Z" }],
  source: "backend",
  issuedAt: "2026-08-14T18:00:00Z",
  expiresAt: "2026-08-14T19:00:00Z",
};

const verified: AuthorizationResolution = { status: "verified", snapshot };
const loading: AuthorizationResolution = { status: "loading", snapshot: null };
const denied: AuthorizationResolution = {
  status: "denied",
  snapshot: null,
  reason: "tenant_mismatch",
};
const expired: AuthorizationResolution = {
  status: "expired",
  snapshot: null,
  reason: "expired",
};

void verified;
void loading;
void denied;
void expired;

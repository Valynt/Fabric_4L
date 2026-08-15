import { z } from "zod";

export const canonicalAuthorizationRoleSchema = z.enum([
  "tenant_admin",
  "content_admin",
  "analyst",
  "read_only",
]);

const authorizationSnapshotSchema = z.object({
  schemaVersion: z.literal("1"),
  source: z.literal("backend"),
  identity: z.object({
    clerkUserId: z.string().min(1),
    fabricUserId: z.string().min(1),
    sessionDiscriminator: z.string().min(1),
  }),
  tenant: z.object({
    fabricTenantId: z.string().min(1),
    clerkOrganizationId: z.string().min(1),
    tenantSlug: z.string().nullable(),
    membershipId: z.string().min(1),
    membershipStatus: z.literal("active"),
  }),
  accountScope: z.discriminatedUnion("scopeType", [
    z.object({ scopeType: z.literal("tenant"), accountId: z.null() }),
    z.object({ scopeType: z.literal("account"), accountId: z.string().min(1) }),
  ]),
  roles: z
    .array(canonicalAuthorizationRoleSchema)
    .refine(values => new Set(values).size === values.length),
  permissions: z
    .array(z.string().min(1))
    .refine(values => new Set(values).size === values.length),
  entitlements: z
    .array(z.string().min(1))
    .refine(values => new Set(values).size === values.length),
  issuedAt: z.string().datetime({ offset: true }),
  expiresAt: z.string().datetime({ offset: true }),
});

export type AuthorizationSnapshot = z.infer<typeof authorizationSnapshotSchema>;

export type AuthorizationResolution =
  | { status: "loading"; snapshot: null }
  | { status: "verified"; snapshot: AuthorizationSnapshot }
  | {
      status: "denied";
      snapshot: null;
      reason: "malformed" | "mismatch" | "unavailable" | "unauthenticated";
    }
  | { status: "expired"; snapshot: null; expiredAt: string };

interface ExpectedAuthorizationContext {
  clerkUserId: string;
  sessionDiscriminator: string;
  clerkOrganizationId: string;
  fabricTenantId: string;
  accountId: string | null;
  now?: Date;
}

export function parseAuthorizationCandidate(
  candidate: unknown,
  expected: ExpectedAuthorizationContext
): AuthorizationResolution {
  const parsed = authorizationSnapshotSchema.safeParse(candidate);
  if (!parsed.success)
    return { status: "denied", snapshot: null, reason: "malformed" };
  const snapshot = parsed.data;
  const expectedScope =
    expected.accountId === null
      ? snapshot.accountScope.scopeType === "tenant" &&
        snapshot.accountScope.accountId === null
      : snapshot.accountScope.scopeType === "account" &&
        snapshot.accountScope.accountId === expected.accountId;
  if (
    snapshot.identity.clerkUserId !== expected.clerkUserId ||
    snapshot.identity.sessionDiscriminator !== expected.sessionDiscriminator ||
    snapshot.tenant.clerkOrganizationId !== expected.clerkOrganizationId ||
    snapshot.tenant.fabricTenantId !== expected.fabricTenantId ||
    !expectedScope
  )
    return { status: "denied", snapshot: null, reason: "mismatch" };

  const issuedAt = Date.parse(snapshot.issuedAt);
  const expiresAt = Date.parse(snapshot.expiresAt);
  const now = (expected.now ?? new Date()).getTime();
  if (
    issuedAt > now + 30_000 ||
    expiresAt <= issuedAt ||
    expiresAt - issuedAt > 300_000
  ) {
    return { status: "denied", snapshot: null, reason: "malformed" };
  }
  if (expiresAt <= now)
    return { status: "expired", snapshot: null; expiredAt: snapshot.expiresAt };
  return { status: "verified", snapshot };
}

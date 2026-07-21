/**
 * Auth Schemas — Zod validation for identity provider contracts
 *
 * Defines the formal contract between Frontend and Identity Provider.
 * All token responses must conform to these schemas.
 */
import { z } from 'zod';

/**
 * Backend-canonical roles from identity provider
 * These are the source-of-truth roles from the backend permission system
 */
export const BackendRoles = [
  'super_admin',
  'tenant_admin',
  'content_admin',
  'analyst',
  'read_only',
  'system',
] as const;

/**
 * Frontend presentation tiers (UI abstraction layer)
 * These are normalized from backend roles for UI feature gating
 */
export const FrontendTiers = ['standard', 'advanced', 'admin'] as const;

/**
 * All valid role values the frontend accepts
 * Union of backend-canonical roles and frontend presentation tiers
 */
export const AllRoles = [...BackendRoles, ...FrontendTiers] as const;

export type BackendRole = typeof BackendRoles[number];
export type FrontendTier = typeof FrontendTiers[number];
export type UserRole = typeof AllRoles[number];

const unsafeEmailInputPattern = /[<>"'`\\\u0000-\u001f]|javascript:|data:/i;

export const SafeEmailSchema = z
  .string()
  .trim()
  .max(254, 'Email must be 254 characters or fewer')
  .refine((value) => !unsafeEmailInputPattern.test(value), 'Email contains unsafe characters')
  .email('Valid email required');

export function isSafeEmail(value: string): boolean {
  return SafeEmailSchema.safeParse(value).success;
}

/**
 * UserInfo schema — user identity attributes from IdP
 *
 * Accepts both backend-canonical roles and frontend tiers for backward compatibility.
 * Normalization to UI tiers happens in userTierStore.setUserRole()
 */
export const UserInfoSchema = z.object({
  id: z.string().min(1, 'User ID is required'),
  email: SafeEmailSchema,
  role: z.enum(AllRoles).default('standard'),
  tenantId: z.string().min(1, 'Tenant ID is required'),
  tenantSlug: z.string().min(1, 'Tenant slug is required'),
});

export type UserInfo = z.infer<typeof UserInfoSchema>;

/**
 * TokenResponse schema — OAuth2/OIDC token exchange response
 *
 * This is the formal contract for the callback endpoint response.
 * All fields are validated to ensure type safety across the auth boundary.
 *
 * Note: role accepts both backend-canonical roles and frontend tiers.
 * The backend returns canonical roles (super_admin, tenant_admin, etc.)
 * which are normalized to UI tiers in the auth flow.
 */
export const TokenResponseSchema = z.object({
  /**
   * access_token is optional: the backend delivers the token exclusively via
   * the httpOnly `vf_session` cookie and omits it from the JSON body.
   * Legacy clients that still send it in the body are also accepted.
   */
  access_token: z.string().min(1).optional(),
  refresh_token: z.string().optional(),
  expires_in: z.number().int().positive().optional().default(3600),
  token_type: z.string().transform(val => val.charAt(0).toUpperCase() + val.slice(1).toLowerCase()).default('Bearer'),
  user_id: z.string().min(1, 'User ID is required'),
  email: SafeEmailSchema,
  role: z.enum(AllRoles).default('standard'),
});

export type TokenResponse = z.infer<typeof TokenResponseSchema>;

/**
 * LoginInitiationResponse schema — OIDC authorization URL response
 */
export const LoginInitiationResponseSchema = z.object({
  authorization_url: z.url('Valid authorization URL required'),
  state: z.string().min(1, 'State parameter is required'),
});

export type LoginInitiationResponse = z.infer<typeof LoginInitiationResponseSchema>;

/**
 * Auth error categories for deterministic error handling
 */
export enum AuthErrorCategory {
  NETWORK = 'NETWORK',
  AUTHENTICATION = 'AUTHENTICATION',
  MALFORMED_RESPONSE = 'MALFORMED_RESPONSE',
  SSO_PROVIDER_ERROR = 'SSO_PROVIDER_ERROR',
  SESSION_EXPIRED = 'SESSION_EXPIRED',
  VALIDATION = 'VALIDATION',
}

/**
 * Structured auth error with category for precise handling
 */
export class AuthError extends Error {
  public readonly category: AuthErrorCategory;
  public readonly statusCode?: number;

  constructor(
    message: string,
    category: AuthErrorCategory,
    statusCode?: number
  ) {
    super(message);
    this.name = 'AuthError';
    this.category = category;
    this.statusCode = statusCode;
  }
}

/**
 * Validate a token response against the schema
 * @throws AuthError with MALFORMED_RESPONSE category if validation fails
 */
export function validateTokenResponse(data: unknown): TokenResponse {
  const result = TokenResponseSchema.safeParse(data);
  if (!result.success) {
    throw new AuthError(
      `Invalid token response: ${result.error.message}`,
      AuthErrorCategory.MALFORMED_RESPONSE
    );
  }
  return result.data;
}

/**
 * Validate login initiation response
 * @throws AuthError with MALFORMED_RESPONSE category if validation fails
 */
export function validateLoginInitiationResponse(data: unknown): LoginInitiationResponse {
  const result = LoginInitiationResponseSchema.safeParse(data);
  if (!result.success) {
    throw new AuthError(
      `Invalid login initiation response: ${result.error.message}`,
      AuthErrorCategory.MALFORMED_RESPONSE
    );
  }
  return result.data;
}

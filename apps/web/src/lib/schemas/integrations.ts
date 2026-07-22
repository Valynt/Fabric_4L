import { z } from "zod";

export const CRMProviderSchema = z.enum(["salesforce", "hubspot"]);

export const IntegrationSchema = z.object({
  id: z.string(),
  tenant_id: z.string(),
  provider: CRMProviderSchema,
  enabled: z.boolean(),
  instance_url: z.string().nullable(),
  sync_interval_minutes: z.number(),
  sync_batch_size: z.number(),
  last_sync_at: z.string().nullable(),
  last_successful_sync_at: z.string().nullable(),
  records_synced: z.number(),
  records_updated: z.number(),
  records_failed: z.number(),
  status: z.enum(["idle", "running", "failed", "pending", "degraded"]),
  last_error_message: z.string().nullable(),
  has_refresh_token: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const IntegrationListResponseSchema = z.object({
  integrations: z.array(IntegrationSchema),
});

export const ConnectionTestResultSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  details: z.record(z.string(), z.unknown()).optional(),
  error_code: z.string().optional(),
});

export const SyncTriggerResultSchema = z.object({
  sync_id: z.string(),
  job_id: z.string(),
  status: z.string(),
  provider: z.string(),
  queued_at: z.string().optional(),
});

export const OAuthAuthorizeResultSchema = z.object({
  authorization_url: z.url().optional(),
  authorize_url: z.url().optional(),
  state_expires_at: z.string(),
}).refine((value) => Boolean(value.authorization_url || value.authorize_url), {
  message: "authorization_url or authorize_url is required",
}).transform((value) => ({
  authorization_url: value.authorization_url ?? value.authorize_url ?? "",
  authorize_url: value.authorize_url ?? value.authorization_url ?? "",
  state_expires_at: value.state_expires_at,
}));

export type CRMProvider = z.infer<typeof CRMProviderSchema>;
export type Integration = z.infer<typeof IntegrationSchema>;
export type ConnectionTestResult = z.infer<typeof ConnectionTestResultSchema>;
export type SyncTriggerResult = z.infer<typeof SyncTriggerResultSchema>;
export type OAuthAuthorizeResult = z.infer<typeof OAuthAuthorizeResultSchema>;
export type IntegrationListResponse = z.infer<
  typeof IntegrationListResponseSchema
>;

export function parseIntegration(data: unknown): Integration {
  return IntegrationSchema.parse(data);
}

export function parseIntegrations(data: unknown): Integration[] {
  return IntegrationListResponseSchema.parse(data).integrations;
}

export function parseConnectionTestResult(data: unknown): ConnectionTestResult {
  return ConnectionTestResultSchema.parse(data);
}

export function parseSyncTriggerResult(data: unknown): SyncTriggerResult {
  return SyncTriggerResultSchema.parse(data);
}

export function parseOAuthAuthorizeResult(data: unknown): OAuthAuthorizeResult {
  return OAuthAuthorizeResultSchema.parse(data);
}

import { z } from "zod";
import { boolStringSchema, parseEnvOrThrow } from "./shared.js";

const pathPrefixSchema = z
  .string()
  .trim()
  .min(1)
  .refine((value) => value.startsWith("/"), {
    message: "must start with /",
  });

export const frontendEnvSchema = z.object({
  VITE_API_BASE: pathPrefixSchema,
  VITE_API_VERSION_PREFIX: pathPrefixSchema.optional(),
  VITE_L1_PREFIX: pathPrefixSchema,
  VITE_L2_PREFIX: pathPrefixSchema,
  VITE_L2_5_PREFIX: pathPrefixSchema,
  VITE_L3_PREFIX: pathPrefixSchema,
  VITE_L4_PREFIX: pathPrefixSchema,
  VITE_L5_PREFIX: pathPrefixSchema,
  VITE_L6_PREFIX: pathPrefixSchema,
  VITE_L7_PREFIX: pathPrefixSchema,
  VITE_LAYER1_ROUTE_PREFIX: pathPrefixSchema.optional(),
  VITE_LAYER2_ROUTE_PREFIX: pathPrefixSchema.optional(),
  VITE_LAYER2_5_ROUTE_PREFIX: pathPrefixSchema.optional(),
  VITE_LAYER3_ROUTE_PREFIX: pathPrefixSchema.optional(),
  VITE_LAYER4_ROUTE_PREFIX: pathPrefixSchema.optional(),
  VITE_LAYER5_ROUTE_PREFIX: pathPrefixSchema.optional(),
  VITE_LAYER6_ROUTE_PREFIX: pathPrefixSchema.optional(),
  VITE_LAYER7_ROUTE_PREFIX: pathPrefixSchema.optional(),
  VITE_ENABLE_CRM_SYNC: boolStringSchema,
  VITE_CRM_PROVIDER: z.enum(["salesforce", "hubspot", "pipedrive", "zoho"]),
  VITE_CRM_API_PROXY: pathPrefixSchema,
  VITE_ENABLE_C1_REPORTS: boolStringSchema,
  VITE_USE_MOCKS: boolStringSchema,
});

export type FrontendEnv = z.infer<typeof frontendEnvSchema>;

export function loadFrontendEnv(env: Record<string, unknown>): FrontendEnv {
  return parseEnvOrThrow(frontendEnvSchema, env);
}

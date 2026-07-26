import { z } from "zod";

const UnknownRecordSchema = z.record(z.string(), z.unknown());

export const ProductFeatureSchema = UnknownRecordSchema;

export const ProductCapabilitySchema = UnknownRecordSchema;

export const ProductSchema = z.looseObject({
    id: z.string(),
    name: z.string(),
    description: z.string().nullable().optional(),
    category: z.string().nullable().optional(),
    sku: z.string().nullable().optional(),
    pricing_model: z.string().nullable().optional(),
    target_personas: z.array(z.string()).optional().default([]),
    industries: z.array(z.string()).optional().default([]),
    features: z.array(ProductFeatureSchema).optional().default([]),
    capabilities: z.array(ProductCapabilitySchema).optional().default([]),
    created_at: z.string().nullable().optional(),
    updated_at: z.string().nullable().optional(),
  });

export const ProductListResponseSchema = z.looseObject({
    products: z.array(ProductSchema),
    total: z.number().int().min(0),
    skip: z.number().int().min(0).optional().default(0),
    limit: z.number().int().min(0).optional().default(0),
  });

export const SignalMatchSchema = z.looseObject({
    product: ProductSchema.or(UnknownRecordSchema),
    total_score: z.number(),
    signal_count: z.number().int().min(0),
    top_matches: z.array(UnknownRecordSchema),
  });

export const PortfolioSummarySchema = z.looseObject({
    total_products: z.number().int().min(0),
    total_features: z.number().int().min(0),
    total_capabilities: z.number().int().min(0),
    categories: z.array(z.string()),
    avg_features_per_product: z.number(),
    avg_capabilities_per_product: z.number(),
  });

export const CapabilityCoverageSchema = z.looseObject({
    capability: ProductCapabilitySchema,
    products: z.array(ProductSchema.or(UnknownRecordSchema)),
    signal_demand: z.number().int().min(0),
    status: z.string(),
  });

export const FeatureMutationResponseSchema = UnknownRecordSchema;

export const CapabilityMutationResponseSchema = UnknownRecordSchema;

export type ProductFeature = z.infer<typeof ProductFeatureSchema>;
export type ProductCapability = z.infer<typeof ProductCapabilitySchema>;
export type Product = z.infer<typeof ProductSchema>;
export type ProductListResponse = z.infer<typeof ProductListResponseSchema>;
export type SignalMatch = z.infer<typeof SignalMatchSchema>;
export type PortfolioSummary = z.infer<typeof PortfolioSummarySchema>;
export type CapabilityCoverage = z.infer<typeof CapabilityCoverageSchema>;
export type FeatureMutationResponse = z.infer<typeof FeatureMutationResponseSchema>;
export type CapabilityMutationResponse = z.infer<typeof CapabilityMutationResponseSchema>;

export function parseProduct(data: unknown): Product {
  return ProductSchema.parse(data);
}

export function parseProductListResponse(data: unknown): ProductListResponse {
  return ProductListResponseSchema.parse(data);
}

export function parseSignalMatchList(data: unknown): SignalMatch[] {
  return z.array(SignalMatchSchema).parse(data);
}

export function parsePortfolioSummary(data: unknown): PortfolioSummary {
  return PortfolioSummarySchema.parse(data);
}

export function parseCapabilityCoverageList(data: unknown): CapabilityCoverage[] {
  return z.array(CapabilityCoverageSchema).parse(data);
}

export function parseFeatureMutationResponse(data: unknown): FeatureMutationResponse {
  return FeatureMutationResponseSchema.parse(data);
}

export function parseCapabilityMutationResponse(data: unknown): CapabilityMutationResponse {
  return CapabilityMutationResponseSchema.parse(data);
}

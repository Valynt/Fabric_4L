import { apiRequest } from './client'

export type EntitlementDecision = {
  tenant_id: string
  plan_id: string
  feature: string
  allowed: boolean
  policy: string
}

export async function getEntitlementDecision(planId: string, feature: string): Promise<EntitlementDecision> {
  return apiRequest<EntitlementDecision>(`/v1/billing/entitlements/${planId}/decision?feature=${encodeURIComponent(feature)}`)
}

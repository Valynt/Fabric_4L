import { apiGet } from './typedClient'

export type EntitlementDecision = {
  tenant_id: string
  plan_id: string
  feature: string
  allowed: boolean
  policy: string
}

export async function getEntitlementDecision(planId: string, feature: string): Promise<EntitlementDecision> {
  const response = await apiGet<EntitlementDecision>('l1', `/billing/entitlements/${planId}/decision?feature=${encodeURIComponent(feature)}`)
  return response.data
}

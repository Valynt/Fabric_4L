/**
 * Deliverable route helpers — canonical §2.6 route construction for deliverables.
 */
import { getStatePath } from "@/navigation/navigationService";

export const deliverableRoutes = {
  /** /t/:tenantSlug/accounts/:accountId/deliverables/business-cases/:caseId */
  businessCaseDetail: (tenantSlug: string, accountId: string, caseId: string): string =>
    getStatePath("deliverables-business-case-detail", { tenantSlug, accountId, caseId }),

  /** /t/:tenantSlug/accounts/:accountId/deliverables/business-cases */
  businessCaseList: (tenantSlug: string, accountId: string): string =>
    getStatePath("deliverables-business-cases", { tenantSlug, accountId }),
};

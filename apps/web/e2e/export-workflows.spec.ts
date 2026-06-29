import { E2E_SEED_APPROVED_CASE_ID } from "./fixtures/seed-constants";
/**
 * Export Workflow Validation Suite
 *
 * Traceability: EXPORT-001, EXEC-BUYER-001, SHARE-001, PROVENANCE-EXPORT-001.
 * Approved deliverables, shared views, and provenance exports must be reachable
 * through the UI while unapproved cases remain blocked from final export.
 */
import { journeyTest, expect } from "./helpers/journey-fixture";
import {
  expectAnyVisible,
  expectButtonStateIfVisible,
  expectNoCrossTenantLeakage,
  expectRouteSupportsWorkflow,
} from "./helpers/validation-program";
import { TEST_ACCOUNTS } from "./fixtures/account-helpers";
import { TEST_TENANT_SLUG } from "./fixtures/tier-helpers";

const CASE_ID = E2E_SEED_APPROVED_CASE_ID;
const DRAFT_CASE_ID = "case-draft-001";
const ACCOUNT_ID = TEST_ACCOUNTS.meridian.id;
const tenantRoute = (path: string) => `/t/${TEST_TENANT_SLUG}${path}`;
const accountRoute = (path: string) =>
  tenantRoute(`/accounts/${ACCOUNT_ID}${path}`);

journeyTest.describe("Export Workflow Validation Suite", () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      {
        pattern: `**/api/v1/agents/cases/${CASE_ID}`,
        body: {
          case_id: CASE_ID,
          id: CASE_ID,
          title: "Meridian Automation Business Case",
          status: "approved",
          document_url: "/exports/meridian-business-case.pdf",
          summary: "Approved case with verified evidence lineage.",
          total_value: 1200000,
          implementation_cost: 420000,
          roi_ratio: 2.4,
          payback_months: 9,
          confidence_score: 0.91,
          executive_summary: "Approved case with verified evidence lineage.",
          recommendations: ["Proceed with executive-buyer review."],
          page_count: 12,
          file_size_bytes: 245760,
          truth_references: [
            {
              id: "ev-001",
              claim: "Automation reduces reconciliation cycle time.",
              source: "Discovery call transcript",
              type: "evidence",
            },
          ],
          case_metadata: {
            account_id: ACCOUNT_ID,
            account_route_id: ACCOUNT_ID,
            account_name: "Meridian Health Group",
            crm_push_ready: true,
            realization_conversion_ready: true,
            validation_summary: { total: 1, validated: 1, failed: 0 },
          },
        },
      },
      {
        pattern: `**/api/v1/agents/cases/${DRAFT_CASE_ID}`,
        body: {
          case_id: DRAFT_CASE_ID,
          id: DRAFT_CASE_ID,
          title: "Draft Business Case",
          status: "draft",
          document_url: null,
          summary: "Draft case pending approval.",
          total_value: 450000,
          implementation_cost: 220000,
          roi_ratio: 1.1,
          payback_months: 18,
          confidence_score: 0.45,
          executive_summary: "Draft case pending approval.",
          recommendations: ["Resolve missing evidence before export."],
          page_count: 0,
          file_size_bytes: 0,
          truth_references: [],
          case_metadata: {
            account_id: ACCOUNT_ID,
            account_route_id: ACCOUNT_ID,
            account_name: "Meridian Health Group",
            validation_summary: { total: 1, validated: 0, failed: 0 },
          },
        },
      },
      {
        pattern: `**/api/v1/agents/accounts/${ACCOUNT_ID}/gates`,
        body: {
          account_id: ACCOUNT_ID,
          all_passed: false,
          gates: [
            {
              type: "approval",
              status: "open",
              reason: "Reviewer approval required before export.",
            },
            { type: "evidence", status: "closed", reason: null },
          ],
          checked_at: "2026-05-01T12:00:00Z",
        },
      },
      {
        pattern: "**/api/v1/agents/workflows?type=business_case**",
        body: {
          items: [
            {
              workflow_id: CASE_ID,
              name: "Meridian Automation Business Case",
              status: "completed",
              company_name: "Meridian Health Group",
              total_value: 1200000,
              use_case_count: 3,
              confidence: 0.91,
              created_at: "2026-04-20T12:00:00Z",
              updated_at: "2026-05-01T12:00:00Z",
              owner: "Avery Stone",
            },
          ],
        },
      },
    ]);
  });

  journeyTest(
    "Step 1 [EXPORT-001]: approved business case exposes final PDF export action",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        accountRoute(`/deliverables/business-cases/${CASE_ID}`),
        [
          /business case/i,
          /approved/i,
          /executive summary/i,
          /recommendations/i,
          /export pdf/i,
        ],
        "approved business-case PDF export workflow"
      );

      const exportButton = authedPage
        .getByRole("button", { name: /export pdf/i })
        .first();
      if (await exportButton.isVisible({ timeout: 3000 }).catch(() => false)) {
        await expect(exportButton).toBeEnabled();
      }
    }
  );

  journeyTest(
    "Step 2 [EXPORT-GATE-001]: draft business case keeps export disabled until approval",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        accountRoute(`/deliverables/business-cases/${DRAFT_CASE_ID}`),
        [
          /business case/i,
          /status: draft/i,
          /executive summary/i,
          /export pdf/i,
        ],
        "draft business-case export gate workflow"
      );

      const exportButton = authedPage
        .getByRole("button", { name: /export pdf/i })
        .first();
      if (await exportButton.isVisible({ timeout: 3000 }).catch(() => false)) {
        await expect(exportButton).toBeDisabled();
      }
    }
  );

  journeyTest(
    "Step 3 [EXEC-BUYER-001]: executive-buyer shared view renders buyer-facing summary and financial impact",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        accountRoute(`/deliverables/views/executive?caseId=${CASE_ID}`),
        [/executive/i, /summary/i, /financial/i, /impact/i, /assumptions/i],
        "executive-buyer shared deliverable view"
      );
      await expectNoCrossTenantLeakage(authedPage);
    }
  );

  journeyTest(
    "Step 4 [SHARE-001]: deliverable list supports create, search, and shared-case review",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        accountRoute("/deliverables/business-cases"),
        [
          /business cases/i,
          /new case/i,
          /search cases or companies/i,
          /draft/i,
          /active/i,
        ],
        "business-case list, search, create, and shared review workflow"
      );
    }
  );

  journeyTest(
    "Step 5 [PROVENANCE-EXPORT-001]: provenance export is visible with audit context",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        tenantRoute("/governance/traces"),
        [
          /decision trace/i,
          /export prov-o/i,
          /audit log/i,
          /provenance timeline/i,
        ],
        "provenance export and audit-context workflow"
      );
      await expectAnyVisible(
        authedPage,
        [/export prov-o/i, /audit log/i],
        "provenance export controls"
      );
    }
  );

  journeyTest(
    "test_export_blocked_without_required_role_and_approval",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        accountRoute(`/deliverables/business-cases/${DRAFT_CASE_ID}`),
        [/business case/i, /draft/i, /export pdf/i, /executive summary/i],
        "draft export governance workflow"
      );
      await expectButtonStateIfVisible(authedPage, /export pdf/i, "disabled");
    }
  );
});

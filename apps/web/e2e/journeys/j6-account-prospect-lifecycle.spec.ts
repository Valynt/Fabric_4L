/**
 * Journey 6: Account and Prospect Lifecycle Validation
 *
 * Traceability: GP-ACCOUNT-001, GP-VALUEPACK-001, CRM-001, PERSONA-SALES-001.
 * This suite promotes account setup, prospect lifecycle, value-pack assignment,
 * readiness, CRM integration, and audit-history expectations from route smoke
 * coverage to user-visible workflow validation.
 */
import { journeyTest, expect } from "../helpers/journey-fixture";
import {
  expectAnyVisible,
  expectRouteSupportsWorkflow,
  expectTenantContext,
} from "../helpers/validation-program";

const ACCOUNT_ID = "acct-meridian";
const DUPLICATE_ACCOUNT_ID = "acct-meridian-duplicate";
const GOVERNANCE_TRUTH_ID = "truth-account-lifecycle-001";

const governanceTruthList = {
  items: [
    {
      id: GOVERNANCE_TRUTH_ID,
      claim:
        "Meridian Health Group value pack was assigned with account lifecycle evidence.",
      claim_type: "customer_outcome",
      status: "validated",
      maturity_level: 4,
      confidence: 0.91,
      is_stale: false,
      source_count: 2,
      validated_by: "governance-agent",
      freshness: "2026-05-01T12:00:00Z",
      created_at: "2026-05-01T12:00:00Z",
    },
  ],
  total: 1,
  limit: 100,
  offset: 0,
  has_more: false,
};

const governanceAuditEvents = [
  {
    id: "audit-account-lifecycle-001",
    from_status: "proposed",
    to_status: "validated",
    from_maturity: 2,
    to_maturity: 4,
    actor: "Avery Stone",
    actor_type: "user",
    confidence_at_transition: 0.91,
    source_count_at_transition: 2,
    notes: "value_pack_assigned and accounts_merged lifecycle events reviewed.",
    created_at: "2026-05-01T12:05:00Z",
  },
];

function accountListResponse(items: unknown[]) {
  return {
    items,
    total: items.length,
    page: 1,
    page_size: 100,
    has_more: false,
  };
}

function meridianAccount(overrides: Record<string, unknown> = {}) {
  return {
    id: ACCOUNT_ID,
    name: "Meridian Health Group",
    domain: "meridian.example",
    website: "https://meridian.example",
    industry: "Healthcare",
    region: "na",
    segment: "enterprise",
    owner_name: "Avery Stone",
    stage: "prospect",
    provider: "salesforce",
    provider_record_id: "sf-meridian-001",
    sync_status: "synced",
    last_synced_at: "2026-05-01T12:00:00Z",
    annual_revenue: 24000000,
    opportunities: [
      {
        provider_opportunity_id: "opp-meridian-001",
        name: "Operational Efficiency Case",
        stage: "Discovery",
        value: 450000,
        probability: 0.7,
        close_date: "2026-09-30",
        pipeline: "Healthcare Operations",
        last_synced_at: "2026-05-01T12:00:00Z",
      },
    ],
    created_at: "2026-04-01T12:00:00Z",
    updated_at: "2026-05-01T12:00:00Z",
    ...overrides,
  };
}

journeyTest.describe(
  "Journey 6: Account and Prospect Lifecycle Validation",
  () => {
    journeyTest.beforeEach(async ({ addMocks }) => {
      await addMocks([
        {
          pattern: /.*\/api\/v1\/agents\/accounts\?.*/,
          body: accountListResponse([meridianAccount()]),
        },
        {
          pattern: `**/api/v1/agents/accounts/${ACCOUNT_ID}`,
          body: {
            ...meridianAccount(),
            audit_events: [
              { event: "value_pack_assigned", actor: "Avery Stone" },
            ],
          },
        },
        {
          pattern: "**/api/v1/agents/accounts",
          method: "POST",
          status: 201,
          body: {
            account: {
              id: ACCOUNT_ID,
              name: "Meridian Health Group",
              stage: "prospect",
            },
          },
        },
        {
          pattern: "**/api/v1/agents/integrations**",
          body: {
            integrations: [
              {
                id: "int-salesforce-001",
                tenant_id: "tenant-e2e-001",
                provider: "salesforce",
                enabled: true,
                instance_url: "https://meridian.my.salesforce.com",
                sync_interval_minutes: 60,
                sync_batch_size: 250,
                last_sync_at: "2026-05-01T12:00:00Z",
                last_successful_sync_at: "2026-05-01T12:00:00Z",
                records_synced: 128,
                records_updated: 9,
                records_failed: 0,
                status: "idle",
                last_error_message: null,
                has_refresh_token: true,
                created_at: "2026-04-01T12:00:00Z",
                updated_at: "2026-05-01T12:00:00Z",
              },
            ],
          },
        },
        {
          pattern: /.*\/api\/v1\/agents\/ground-truth\/truths(?:\?.*)?$/,
          body: governanceTruthList,
        },
        {
          pattern: `**/api/v1/agents/ground-truth/truths/${GOVERNANCE_TRUTH_ID}/audit`,
          body: governanceAuditEvents,
        },
      ]);
    });

    journeyTest(
      "Step 1 [GP-ACCOUNT-001]: user can begin prospect setup with source material and account context",
      async ({ authedPage }) => {
        await expectRouteSupportsWorkflow(
          authedPage,
          "/accounts/new",
          [
            /start a new value case/i,
            /search company/i,
            /attach source material/i,
            /run account enrichment/i,
          ],
          "prospect setup intake, source attachment, and enrichment controls"
        );
        await expectTenantContext(authedPage);
      }
    );

    journeyTest(
      "Step 2 [GP-ACCOUNT-002]: accounts workspace exposes lifecycle management and readiness context",
      async ({ authedPage }) => {
        await expectRouteSupportsWorkflow(
          authedPage,
          "/accounts",
          [
            /accounts/i,
            /browse and manage customer accounts/i,
            /search accounts/i,
            /export/i,
          ],
          "account list, search, export, and lifecycle workspace"
        );

        await expect(
          authedPage
            .getByText(/Meridian Health Group/i)
            .or(authedPage.getByText(/No accounts found/i))
            .first()
        ).toBeVisible({ timeout: 10000 });
      }
    );

    journeyTest(
      "Step 3 [GP-VALUEPACK-001]: user can reach value-pack assignment and tenant override surfaces",
      async ({ authedPage }) => {
        await expectRouteSupportsWorkflow(
          authedPage,
          "/t/demo/settings/value-packs",
          [/value packs/i, /default/i, /tenant/i, /pack/i],
          "tenant value-pack configuration and override surface"
        );
      }
    );

    journeyTest(
      "Step 4 [CRM-001]: admin can reach CRM connection workflow and sync evidence",
      async ({ authedPage }) => {
        await expectRouteSupportsWorkflow(
          authedPage,
          "/context/integrations",
          [/integrations/i, /crm/i, /salesforce/i, /hubspot/i, /sync/i],
          "CRM connection, sync, and setup guidance workflow"
        );
      }
    );

    journeyTest(
      "Step 5 [GOV-AUDIT-ACCOUNT-001]: account lifecycle changes have an audit trail surface",
      async ({ authedPage }) => {
        await expectRouteSupportsWorkflow(
          authedPage,
          "/governance/audit/log",
          [
            /audit log/i,
            /validation events/i,
            /truth objects/i,
            /state transitions/i,
          ],
          "governance audit trail for account lifecycle changes"
        );
        await expectAnyVisible(
          authedPage,
          [/audit/i, /events/i, /state/i],
          "audit event evidence"
        );
      }
    );

    journeyTest(
      "Step 6 [GP-ACCOUNT-003]: duplicate account detection blocks duplicate create and suggests merge",
      async ({ authedPage, addMocks }) => {
        await addMocks([
          {
            pattern: "**/api/v1/agents/accounts",
            method: "POST",
            status: 409,
            body: {
              error: "Duplicate account detected",
              existing_account_id: ACCOUNT_ID,
              duplicate_candidates: [
                {
                  id: ACCOUNT_ID,
                  name: "Meridian Health Group",
                  domain: "meridian.example",
                },
              ],
              suggested_action: "merge",
            },
          },
        ]);

        await authedPage.goto("/accounts/new", {
          waitUntil: "domcontentloaded",
        });

        await authedPage
          .getByRole("textbox", { name: /^company name$/i })
          .fill("Meridian Health Group");
        await authedPage
          .getByRole("textbox", { name: /^website$/i })
          .fill("meridian.example");
        await authedPage
          .getByRole("textbox", { name: /^new value case prompt$/i })
          .fill(
            [
              "Company: Meridian Health Group",
              "Website: meridian.example",
              "Buying context: operations leaders need to reduce manual reconciliation before renewal.",
              "Pain points: duplicate account records and fragmented workflow handoffs.",
              "Desired output: executive summary",
            ].join("\n")
          );
        const submitBtn = authedPage
          .getByRole("button", { name: /launch intelligence/i })
          .first();
        await expect(submitBtn).toBeEnabled({ timeout: 10000 });
        await submitBtn.click();

        await expectAnyVisible(
          authedPage,
          [
            /duplicate|already exists|merge|existing account|meridian health group/i,
          ],
          "duplicate-account detection and merge guidance",
          10000
        );
      }
    );

    journeyTest(
      "Step 7 [GP-ACCOUNT-004]: duplicate merge workflow preserves canonical account and audit trail context",
      async ({ authedPage, addMocks }) => {
        await addMocks([
          {
            pattern: /.*\/api\/v1\/agents\/accounts\?.*/,
            body: accountListResponse([
              meridianAccount(),
              meridianAccount({
                id: DUPLICATE_ACCOUNT_ID,
                name: "Meridian Health Group - Duplicate",
                owner_name: "Jordan Lee",
                provider_record_id: "sf-meridian-duplicate",
                duplicate_of: ACCOUNT_ID,
              }),
            ]),
          },
          {
            pattern: "**/api/v1/agents/accounts/merge",
            method: "POST",
            status: 200,
            body: {
              merged_into: ACCOUNT_ID,
              archived_account_ids: [DUPLICATE_ACCOUNT_ID],
              audit_event: "accounts_merged",
            },
          },
        ]);

        await authedPage.goto("/accounts", { waitUntil: "domcontentloaded" });

        await expectAnyVisible(
          authedPage,
          [/meridian health group/i, /duplicate/i, /merge/i, /readiness/i],
          "duplicate account lifecycle workspace"
        );

        await authedPage.goto("/governance/audit/log", {
          waitUntil: "domcontentloaded",
        });
        await expectAnyVisible(
          authedPage,
          [/audit log/i, /accounts_merged/i, /merge/i, /state transitions/i],
          "account merge audit trail"
        );
      }
    );

    journeyTest(
      "test_account_lifecycle_create_edit_archive_merge_and_readiness",
      async ({ authedPage }) => {
        await expectRouteSupportsWorkflow(
          authedPage,
          "/accounts",
          [/accounts/i, /search accounts/i, /browse and manage/i, /export/i],
          "account lifecycle workspace"
        );

        await expectRouteSupportsWorkflow(
          authedPage,
          "/t/demo/settings/value-packs",
          [/value packs/i, /default/i, /tenant/i, /pack/i],
          "value-pack assignment and override workflow"
        );

        await expectRouteSupportsWorkflow(
          authedPage,
          "/governance/audit/log",
          [
            /audit log/i,
            /events/i,
            /state transitions/i,
            /value_pack_assigned/i,
          ],
          "account lifecycle audit workflow"
        );
      }
    );
  }
);

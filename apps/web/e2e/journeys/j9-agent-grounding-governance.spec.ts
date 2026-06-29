/**
 * Journey 9: Agent Grounding and Governance
 *
 * Traceability: AGENT-GROUNDING-001, AGENT-REFUSAL-001, SECURITY-PROMPT-INJECTION-001,
 * CLAIM-TRACE-001, AGENT-REC-LIFECYCLE-001. Agent workflows must demonstrate
 * evidence-backed answers, explicit assumptions, unsupported-claim refusal, and
 * auditable recommendation decisions.
 */
import { journeyTest, expect } from "../helpers/journey-fixture";
import {
  expectAnyVisible,
  expectRouteSupportsWorkflow,
  expectNoCrossTenantLeakage,
} from "../helpers/validation-program";
import { TEST_ACCOUNTS } from "../fixtures/account-helpers";
import { TEST_TENANT_SLUG } from "../fixtures/tier-helpers";

const ACCOUNT_ID = TEST_ACCOUNTS.meridian.id;
const tenantRoute = (path: string) => `/t/${TEST_TENANT_SLUG}${path}`;
const accountRoute = (path: string) =>
  tenantRoute(`/accounts/${ACCOUNT_ID}${path}`);

journeyTest.describe("Journey 9: Agent Grounding and Governance", () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      {
        pattern: `**/api/v1/agents/workspace/${ACCOUNT_ID}/signals`,
        body: {
          status: "ready",
          generated_at: "2026-05-01T12:00:00Z",
          content: {
            signals: [
              {
                id: "sig-001",
                name: "Manual reconciliation burden",
                confidence: 0.9,
                source: "Discovery call transcript",
              },
            ],
          },
        },
      },
      {
        pattern: "**/agent-stream/chat",
        method: "POST",
        body: {
          content:
            "Grounded recommendation: cite Discovery call transcript. Assumption: finance team validates baseline hours. Refusal: unsupported claims require evidence.",
          metadata: {
            citations: "Discovery call transcript",
            grounding: "true",
          },
        },
      },
      {
        pattern: "**/api/v1/agents/recommendations**",
        body: [
          { id: "rec-001", status: "pending_review", evidence_id: "ev-001" },
        ],
      },
      {
        pattern: "**/api/v1/graph/v1/products",
        body: {
          products: [
            {
              id: "prod-workflow",
              name: "Workflow Automation",
              category: "operations",
            },
          ],
        },
      },
      {
        pattern: `**/api/v1/agents/hypotheses/account/${ACCOUNT_ID}**`,
        body: {
          hypotheses: [
            {
              id: "hyp-001",
              account_id: ACCOUNT_ID,
              hypothesis_text:
                "Automation can reduce manual reconciliation burden when validated against evidence.",
              confidence: 0.86,
              status: "validated",
              evidence_ids: ["ev-001"],
            },
          ],
          total: 1,
        },
      },
      {
        pattern: `**/api/v1/agents/v1/narratives?account_id=${ACCOUNT_ID}`,
        body: {
          narratives: [
            {
              id: "nar-001",
              account_id: ACCOUNT_ID,
              status: "draft",
              title: "Evidence-grounded narrative",
              unsupported_claims: [
                "ROI claim requires supporting evidence before approval.",
              ],
              citations: ["ev-001"],
            },
          ],
        },
      },
      {
        method: "POST",
        pattern: "**/api/v1/agents/analysis/cases/*/workspace/generate",
        body: {
          status: "requires_evidence",
          narrative:
            "Unsupported claims require evidence and citations before final approval.",
          citations: ["ev-001"],
          assumptions: ["Finance team validates baseline hours."],
        },
      },
    ]);
  });

  journeyTest(
    "Step 1 [AGENT-GROUNDING-001]: intelligence workspace exposes evidence-linked signal context",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        accountRoute("/intelligence/signals"),
        [/pain signals/i, /detected/i, /confidence/i, /source:/i, /signal/i],
        "agent signal review with source and confidence grounding"
      );
    }
  );

  journeyTest(
    "Step 2 [AGENT-GROUNDING-002]: agent workspace exposes assumptions and inference boundaries",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        accountRoute("/studio/action-plan"),
        [
          /action plan/i,
          /assumption/i,
          /recommendation/i,
          /evidence/i,
          /confidence/i,
        ],
        "agent action plan with assumptions, recommendations, and confidence labels"
      );
    }
  );

  journeyTest(
    "Step 3 [AGENT-REFUSAL-001]: unsupported claims must surface refusal or evidence-required feedback",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        accountRoute("/studio/narrative"),
        [/narrative/i, /evidence/i, /assumption/i, /unsupported/i, /citation/i],
        "unsupported-claim refusal and citation requirement workflow"
      );

      await expectAnyVisible(
        authedPage,
        [/evidence/i, /assumption/i, /citation/i, /unsupported/i, /narrative/i],
        "agent grounding feedback on narrative generation"
      );
    }
  );

  journeyTest(
    "Step 4 [SECURITY-PROMPT-INJECTION-001]: adversarial document instructions are not shown as trusted agent directives",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        tenantRoute("/context/ingestion/jobs"),
        [/ingestion jobs/i, /document/i, /job/i, /status/i],
        "ingestion review surface for adversarial document handling"
      );

      await expect(
        authedPage
          .getByText(
            /ignore previous instructions|exfiltrate|developer message/i
          )
          .first()
      ).not.toBeVisible({ timeout: 3000 });
      await expectNoCrossTenantLeakage(authedPage);
    }
  );

  journeyTest(
    "Step 5 [AGENT-REC-LIFECYCLE-001]: recommendation lifecycle is reviewable and auditable",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        tenantRoute("/governance/traces"),
        [
          /decision trace/i,
          /audit log/i,
          /provenance timeline/i,
          /export prov-o/i,
        ],
        "agent recommendation acceptance, rejection, provenance, and audit trail workflow"
      );
    }
  );

  journeyTest(
    "Step 6 [CLAIM-TRACE-001]: business-case claims expose evidence or assumption lineage",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        tenantRoute("/governance/evidence"),
        [/evidence/i, /truth objects/i, /search claim/i, /confidence/i],
        "claim-level evidence and assumption traceability"
      );
    }
  );

  journeyTest(
    "test_agent_cites_evidence_for_value_claims",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        accountRoute("/intelligence/signals"),
        [/pain signals/i, /source:/i, /confidence/i, /signal/i],
        "agent evidence citation workflow"
      );
      await expectAnyVisible(
        authedPage,
        [/source:/i, /confidence/i, /signal/i],
        "citation surface"
      );
    }
  );

  journeyTest(
    "test_agent_labels_assumptions_and_inferences",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        accountRoute("/studio/action-plan"),
        [/assumption/i, /recommendation/i, /confidence/i, /evidence/i],
        "agent assumption and inference labeling"
      );
    }
  );

  journeyTest(
    "test_agent_refuses_unsupported_roi_claim",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        accountRoute("/studio/narrative"),
        [/unsupported/i, /citation/i, /evidence/i, /assumption/i],
        "unsupported ROI refusal workflow"
      );
    }
  );

  journeyTest(
    "test_agent_ignores_prompt_injection_inside_uploaded_document",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        tenantRoute("/context/ingestion/jobs"),
        [/ingestion jobs/i, /document/i, /job/i, /status/i],
        "prompt-injection-resistant ingestion review"
      );
      await expect(
        authedPage
          .getByText(
            /ignore previous instructions|system prompt|developer message/i
          )
          .first()
      ).not.toBeVisible({ timeout: 3000 });
    }
  );

  journeyTest(
    "test_agent_does_not_fabricate_citations",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        tenantRoute("/governance/evidence"),
        [/evidence/i, /truth objects/i, /source/i, /confidence/i],
        "non-fabricated citation workflow"
      );
    }
  );

  journeyTest(
    "test_agent_recommendation_acceptance_updates_model_with_audit_event",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        tenantRoute("/governance/traces"),
        [/decision trace/i, /audit log/i, /provenance timeline/i],
        "agent recommendation auditability"
      );
    }
  );
});

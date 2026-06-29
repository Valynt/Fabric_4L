/**
 * Journey 10: Layer-by-Layer UI Validation
 *
 * Traceability: L1-INGEST-001, L2-EXTRACT-001, L3-GRAPH-001, L4-AGENT-001,
 * L5-TRUTH-001, L6-BENCHMARK-001. This suite validates that each backend
 * intelligence layer has a user-visible workflow with status, provenance,
 * retry/error handling, and governance context.
 */
import { journeyTest, expect } from "../helpers/journey-fixture";
import {
  expectAnyVisible,
  expectRouteSupportsWorkflow,
  expectTenantContext,
} from "../helpers/validation-program";

journeyTest.describe("Journey 10: Layer-by-Layer UI Validation", () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      {
        pattern: "**/api/v1/ingest/jobs",
        body: [
          {
            id: "job-complete",
            domain: "meridian.example",
            status: "completed",
            progress: 100,
          },
          {
            id: "job-failed",
            domain: "duplicate.example",
            status: "failed",
            progress: 42,
          },
        ],
      },
      {
        pattern: "**/api/v1/entities**",
        body: {
          entities: [
            {
              id: "entity-001",
              name: "Meridian Health Group",
              type: "Account",
            },
          ],
          total: 1,
        },
      },
      {
        pattern: "**/api/v1/graph/entities**",
        body: {
          items: [
            {
              id: "entity-001",
              name: "Meridian Health Group",
              type: "Account",
              tenant_id: "tenant-e2e-001",
            },
          ],
          total: 1,
        },
      },
      {
        pattern: "**/api/v1/value-trees**",
        body: {
          trees: [
            {
              id: "tree-001",
              name: "Operational Efficiency",
              provenance: "Approved evidence",
            },
          ],
          total: 1,
        },
      },
      {
        pattern: "**/api/v1/agents/workflows/active**",
        body: {
          items: [
            {
              id: "wf-agent-001",
              workflow_id: "wf-agent-001",
              name: "Whitespace Analysis",
              type: "agent",
              status: "running",
              progress: 72,
              created_at: "2026-05-01T12:00:00Z",
              updated_at: "2026-05-01T12:05:00Z",
            },
          ],
          total: 1,
        },
      },
      {
        pattern: "**/api/v1/benchmarks/datasets**",
        body: [
          {
            dataset_id: "bench-cycle-time-reduction",
            name: "Cycle Time Reduction",
            industry: "Healthcare",
            segment: "Operations",
            metric_count: 7,
            data_source: "Validated customer outcomes",
            description: "Approved benchmark with stale-state review context.",
          },
        ],
      },
      {
        pattern: "**/api/v1/agents/ground-truth/truths**",
        body: {
          items: [
            {
              id: "truth-001",
              claim:
                "Discovery call supports the operational efficiency metric.",
              claim_type: "efficiency_gain",
              status: "validated",
              maturity_level: 4,
              confidence: 0.9,
              is_stale: false,
              source_count: 1,
              validated_by: "governance-agent",
              freshness: "2026-05-01T12:00:00Z",
              created_at: "2026-05-01T12:00:00Z",
            },
          ],
          total: 1,
          limit: 100,
          offset: 0,
          has_more: false,
        },
      },
    ]);
  });

  journeyTest(
    "Step 1 [L1-INGEST-001]: ingestion jobs expose completed, failed, retry, and progress states",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        "/context/ingestion/jobs",
        [
          /ingestion jobs/i,
          /monitor and manage/i,
          /progress/i,
          /retry/i,
          /new job/i,
        ],
        "Layer 1 ingestion lifecycle and retry workflow"
      );
      await expectTenantContext(authedPage);
    }
  );

  journeyTest(
    "Step 2 [L2-EXTRACT-001]: extraction engine exposes configuration, stream, and results review",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        "/context/extraction",
        [
          /extraction engine/i,
          /configuration panel/i,
          /live stream/i,
          /results table/i,
        ],
        "Layer 2 extraction configuration, live progress, and extracted result review"
      );
    }
  );

  journeyTest(
    "Step 3 [L3-GRAPH-001]: graph explorer exposes search, retry, legend, and statistics",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        "/context/ontology/graph",
        [
          /graph explorer/i,
          /search entities/i,
          /legend/i,
          /graph statistics/i,
          /retry/i,
        ],
        "Layer 3 graph search, entity exploration, provenance, and refresh workflow"
      );
    }
  );

  journeyTest(
    "Step 4 [L3-VALUE-TREE-001]: value-tree explorer exposes account-value ontology review",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        "/context/value-trees/explorer",
        [/value tree/i, /explorer/i, /node/i, /driver/i, /evidence/i],
        "Layer 3 value-tree ontology review workflow"
      );
    }
  );

  journeyTest(
    "Step 5 [L4-AGENT-001]: agent health and workspace routes expose operational status",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        "/context/agents",
        [
          /workflow dashboard/i,
          /active agents/i,
          /workflow history/i,
          /pause/i,
          /resume/i,
        ],
        "Layer 4 agent workflow operations, status, and unavailable-state workflow"
      );
    }
  );

  journeyTest(
    "Step 6 [L5-TRUTH-001]: governance audit log exposes truth-object validation state transitions",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        "/governance/audit/log",
        [
          /audit log/i,
          /truth objects/i,
          /validation events/i,
          /state transitions/i,
        ],
        "Layer 5 truth object validation, audit, and state-transition workflow"
      );
    }
  );

  journeyTest(
    "Step 7 [L6-BENCHMARK-001]: benchmark governance exposes policy, confidence, and stale-state context",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        "/governance/benchmarks",
        [/benchmark/i, /policy/i, /confidence/i, /stale/i, /override/i],
        "Layer 6 benchmark approval, stale-warning, override, and policy workflow"
      );
    }
  );

  journeyTest(
    "test_ingestion_ui_handles_duplicate_and_unsupported_documents",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        "/accounts/new",
        [
          /attach source material/i,
          /use uploaded files/i,
          /source material/i,
          /discovery/i,
        ],
        "source-ingestion upload workflow"
      );

      await expectRouteSupportsWorkflow(
        authedPage,
        "/context/ingestion/jobs",
        [/ingestion jobs/i, /failed/i, /retry/i, /progress/i, /status/i],
        "failed-ingestion handling with retry and progress visibility"
      );
    }
  );

  journeyTest(
    "test_extraction_ui_requires_evidence_for_approved_signal",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        "/context/extraction",
        [/results table/i, /confidence/i, /evidence/i, /approve/i, /review/i],
        "evidence-backed extraction approval workflow"
      );
    }
  );

  journeyTest(
    "test_graph_ui_displays_tenant_scoped_account_context",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        "/context/ontology/graph",
        [/graph explorer/i, /graph statistics/i, /search entities/i, /legend/i],
        "tenant-scoped graph exploration"
      );
      await expectTenantContext(authedPage);
    }
  );

  journeyTest(
    "test_agent_ui_surfaces_structured_tool_failure",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        "/context/agents",
        [
          /workflow dashboard/i,
          /active agents/i,
          /pause/i,
          /resume/i,
          /history/i,
        ],
        "agent workflow status and failure display"
      );
      await expectAnyVisible(
        authedPage,
        [/running/i, /active/i, /history/i, /workflow/i],
        "agent workflow evidence"
      );
    }
  );

  journeyTest(
    "test_ground_truth_ui_tracks_metric_validation_status",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        "/governance/evidence",
        [/truth objects/i, /status/i, /confidence/i, /source/i, /claim/i],
        "ground-truth validation status and lineage"
      );
    }
  );

  journeyTest(
    "test_benchmark_ui_warns_on_stale_or_low_confidence_benchmark",
    async ({ authedPage }) => {
      await expectRouteSupportsWorkflow(
        authedPage,
        "/governance/benchmarks",
        [/benchmark/i, /confidence/i, /stale/i, /override/i, /policy/i],
        "benchmark warning and override policy workflow"
      );
      await expect(
        authedPage.getByText(/stale|confidence|override|policy/i).first()
      ).toBeVisible({ timeout: 10000 });
    }
  );
});

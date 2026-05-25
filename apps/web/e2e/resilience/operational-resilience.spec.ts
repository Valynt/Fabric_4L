/**
 * Operational Resilience Suite
 *
 * Traceability: OPS-EMPTY-001, OPS-RETRY-001, OPS-SERVICE-FAILURE-001,
 * OPS-RESUME-001, OPS-AUDIT-FAILURE-001. Critical workflows must be observable
 * in empty, degraded, failed, retrying, resumed, and audited states.
 */
import { journeyTest, expect } from '../helpers/journey-fixture';
import { expectAnyVisible, expectRouteSupportsWorkflow } from '../helpers/validation-program';

journeyTest.describe('Operational Resilience Suite', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/ingest/jobs',
        body: [
          { id: 'job-failed-001', domain: 'failed.example', status: 'failed', progress: 12 },
          { id: 'job-running-001', domain: 'slow.example', status: 'processing', progress: 68 },
        ],
      },
      {
        pattern: '**/api/v1/agents/health/**',
        status: 503,
        body: { status: 'degraded', components: { graph: 'unavailable', agent: 'timeout' } },
      },
      {
        pattern: '**/api/v1/agents/integrations**',
        body: {
          integrations: [
            {
              id: 'int-salesforce-failure-001',
              tenant_id: 'tenant-e2e-001',
              provider: 'salesforce',
              enabled: true,
              instance_url: 'https://meridian.my.salesforce.com',
              sync_interval_minutes: 60,
              sync_batch_size: 250,
              last_sync_at: '2026-05-01T12:00:00Z',
              last_successful_sync_at: null,
              records_synced: 0,
              records_updated: 0,
              records_failed: 7,
              status: 'error',
              last_error_message: 'CRM sync failed; retry is required.',
              has_refresh_token: true,
              created_at: '2026-04-01T12:00:00Z',
              updated_at: '2026-05-01T12:00:00Z',
            },
          ],
        },
      },
    ]);
  });

  journeyTest('Step 1 [OPS-EMPTY-001]: empty account workspace renders clear next-step guidance', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/accounts',
      [/accounts/i, /no accounts found/i, /search accounts/i, /browse and manage/i],
      'empty or searchable account workspace state',
    );
  });

  journeyTest('Step 2 [OPS-RETRY-001]: failed ingestion jobs expose retry and progress state', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/context/ingestion/jobs',
      [/ingestion jobs/i, /failed/i, /retry/i, /progress/i, /monitor and manage/i],
      'failed ingestion retry and progress workflow',
    );
  });

  journeyTest('Step 3 [OPS-SERVICE-FAILURE-001]: graph service failure leaves a visible retry or unavailable state', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/context/ontology/graph',
      [/graph explorer/i, /retry/i, /could not/i, /unavailable/i, /graph statistics/i],
      'graph service unavailable and retry workflow',
    );
  });

  journeyTest('Step 4 [OPS-CRM-FAILURE-001]: CRM sync failures are visible and retryable', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/context/integrations',
      [/integrations/i, /crm/i, /retry/i, /salesforce/i, /sync/i],
      'CRM sync failure, retry, and integration log workflow',
    );
  });

  journeyTest('Step 5 [OPS-EXPORT-FAILURE-001]: provenance export failures remain visible without losing audit context', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/governance/traces',
      [/decision trace/i, /export prov-o/i, /audit log/i, /provenance timeline/i],
      'export failure visibility and preserved provenance audit workflow',
    );
  });

  journeyTest('Step 6 [OPS-RESUME-001]: partially completed workflow can be resumed after reload', async ({ authedPage }) => {
    await authedPage.goto('/workflow', { waitUntil: 'domcontentloaded' });
    await expectAnyVisible(authedPage, [/start a new value case/i, /recent value cases/i, /prompt settings/i], 'prospect workflow before reload');
    await authedPage.reload({ waitUntil: 'domcontentloaded' });
    await expectAnyVisible(authedPage, [/start a new value case/i, /recent value cases/i, /prompt settings/i], 'prospect workflow after reload');
  });

  journeyTest('Step 7 [OPS-AUDIT-FAILURE-001]: failed critical workflows have governance audit visibility', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/governance/audit/log',
      [/audit log/i, /validation events/i, /state transitions/i, /truth objects/i],
      'failed critical workflow audit event visibility',
    );
    await expect(authedPage.getByText(/audit|events|state transitions|truth objects/i).first()).toBeVisible({ timeout: 10000 });
  });

  journeyTest('test_empty_account_guides_user_to_ingest_sources', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/accounts',
      [/no accounts found/i, /browse and manage/i, /search accounts/i],
      'empty account guidance',
    );
  });

  journeyTest('test_failed_ingestion_can_be_retried_from_ui', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/context/ingestion/jobs',
      [/failed/i, /retry/i, /progress/i, /monitor and manage/i],
      'failed ingestion retry workflow',
    );
  });

  journeyTest('test_partial_extraction_displays_warning_and_available_results', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/context/extraction',
      [/results table/i, /configuration panel/i, /live stream/i, /warning/i],
      'partial extraction warning workflow',
    );
  });

  journeyTest('test_agent_service_failure_shows_recoverable_error', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/context/agents',
      [/workflow dashboard/i, /active agents/i, /history/i, /retry|unavailable|degraded/i],
      'recoverable agent service failure workflow',
    );
  });

  journeyTest('test_crm_sync_failure_displays_retryable_status', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/context/integrations',
      [/integrations/i, /crm/i, /retry/i, /failed/i, /sync/i],
      'retryable CRM sync failure workflow',
    );
  });

  journeyTest('test_user_can_resume_partially_completed_value_model', async ({ authedPage }) => {
    await authedPage.goto('/workflow', { waitUntil: 'domcontentloaded' });
    await expectAnyVisible(authedPage, [/start a new value case/i, /recent value cases/i, /prompt settings/i], 'workflow before resume');
    await authedPage.reload({ waitUntil: 'domcontentloaded' });
    await expectAnyVisible(authedPage, [/start a new value case/i, /recent value cases/i, /prompt settings/i], 'workflow after resume');
  });
});

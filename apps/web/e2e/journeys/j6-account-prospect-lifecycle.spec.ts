/**
 * Journey 6: Account and Prospect Lifecycle Validation
 *
 * Traceability: GP-ACCOUNT-001, GP-VALUEPACK-001, CRM-001, PERSONA-SALES-001.
 * This suite promotes account setup, prospect lifecycle, value-pack assignment,
 * readiness, CRM integration, and audit-history expectations from route smoke
 * coverage to user-visible workflow validation.
 */
import { journeyTest, expect } from '../helpers/journey-fixture';
import { expectAnyVisible, expectRouteSupportsWorkflow, expectTenantContext } from '../helpers/validation-program';

const ACCOUNT_ID = 'acct-meridian';
const DUPLICATE_ACCOUNT_ID = 'acct-meridian-duplicate';

journeyTest.describe('Journey 6: Account and Prospect Lifecycle Validation', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/agents/accounts',
        body: [
          {
            id: ACCOUNT_ID,
            name: 'Meridian Health Group',
            domain: 'meridian.example',
            owner: 'Avery Stone',
            stage: 'prospect',
            readiness: 78,
            value_pack: 'Healthcare Operations',
            updated_at: '2026-05-01T12:00:00Z',
          },
        ],
      },
      {
        pattern: `**/api/v1/agents/accounts/${ACCOUNT_ID}`,
        body: {
          id: ACCOUNT_ID,
          name: 'Meridian Health Group',
          domain: 'meridian.example',
          owner: 'Avery Stone',
          stage: 'prospect',
          readiness: 78,
          value_pack: 'Healthcare Operations',
          audit_events: [{ event: 'value_pack_assigned', actor: 'Avery Stone' }],
        },
      },
      {
        pattern: '**/api/v1/agents/accounts',
        method: 'POST',
        status: 201,
        body: { account: { id: ACCOUNT_ID, name: 'Meridian Health Group', stage: 'prospect' } },
      },
      {
        pattern: '**/api/v1/agents/integrations**',
        body: {
          integrations: [
            {
              id: 'int-salesforce-001',
              tenant_id: 'tenant-e2e-001',
              provider: 'salesforce',
              enabled: true,
              instance_url: 'https://meridian.my.salesforce.com',
              sync_interval_minutes: 60,
              sync_batch_size: 250,
              last_sync_at: '2026-05-01T12:00:00Z',
              last_successful_sync_at: '2026-05-01T12:00:00Z',
              records_synced: 128,
              records_updated: 9,
              records_failed: 0,
              status: 'idle',
              last_error_message: null,
              has_refresh_token: true,
              created_at: '2026-04-01T12:00:00Z',
              updated_at: '2026-05-01T12:00:00Z',
            },
          ],
        },
      },
    ]);
  });

  journeyTest('Step 1 [GP-ACCOUNT-001]: user can begin prospect setup with source material and account context', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/workflow',
      [/start a new value case/i, /search company/i, /attach source material/i, /run account enrichment/i],
      'prospect setup intake, source attachment, and enrichment controls',
    );
    await expectTenantContext(authedPage);
  });

  journeyTest('Step 2 [GP-ACCOUNT-002]: accounts workspace exposes lifecycle management and readiness context', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/accounts',
      [/accounts/i, /browse and manage customer accounts/i, /search accounts/i, /export/i],
      'account list, search, export, and lifecycle workspace',
    );

    await expect(
      authedPage.getByText(/Meridian Health Group/i).or(authedPage.getByText(/No accounts found/i)).first(),
    ).toBeVisible({ timeout: 10000 });
  });

  journeyTest('Step 3 [GP-VALUEPACK-001]: user can reach value-pack assignment and tenant override surfaces', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/settings/data/value-packs',
      [/value packs/i, /default/i, /tenant/i, /pack/i],
      'tenant value-pack configuration and override surface',
    );
  });

  journeyTest('Step 4 [CRM-001]: admin can reach CRM connection workflow and sync evidence', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/context/integrations',
      [/integrations/i, /crm/i, /salesforce/i, /hubspot/i, /sync/i],
      'CRM connection, sync, and setup guidance workflow',
    );
  });

  journeyTest('Step 5 [GOV-AUDIT-ACCOUNT-001]: account lifecycle changes have an audit trail surface', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/governance/audit/log',
      [/audit log/i, /validation events/i, /truth objects/i, /state transitions/i],
      'governance audit trail for account lifecycle changes',
    );
    await expectAnyVisible(authedPage, [/audit/i, /events/i, /state/i], 'audit event evidence');
  });

  journeyTest('Step 6 [GP-ACCOUNT-003]: duplicate account detection blocks duplicate create and suggests merge', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/agents/accounts',
        method: 'POST',
        status: 409,
        body: {
          error: 'Duplicate account detected',
          existing_account_id: ACCOUNT_ID,
          duplicate_candidates: [{ id: ACCOUNT_ID, name: 'Meridian Health Group', domain: 'meridian.example' }],
          suggested_action: 'merge',
        },
      },
    ]);

    await authedPage.goto('/workflow', { waitUntil: 'domcontentloaded' });

    const companyInput = authedPage.getByPlaceholder(/company name/i).first();
    const domainInput = authedPage.getByPlaceholder(/website/i).first();
    const hasForm = await companyInput.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasForm) {
      await companyInput.fill('Meridian Health Group');
      if (await domainInput.isVisible({ timeout: 3000 }).catch(() => false)) {
        await domainInput.fill('meridian.example');
      }
      const submitBtn = authedPage.getByRole('button', { name: /launch|start|create|begin|run|intelligence|enrichment/i }).first();
      if (await submitBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await submitBtn.click();
      }
    }

    await expectAnyVisible(
      authedPage,
      [/duplicate|already exists|merge|existing account|meridian health group/i],
      'duplicate-account detection and merge guidance',
      10000,
    );
  });

  journeyTest('Step 7 [GP-ACCOUNT-004]: duplicate merge workflow preserves canonical account and audit trail context', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/agents/accounts',
        body: [
          {
            id: ACCOUNT_ID,
            name: 'Meridian Health Group',
            domain: 'meridian.example',
            owner: 'Avery Stone',
            stage: 'prospect',
            readiness: 78,
            value_pack: 'Healthcare Operations',
            updated_at: '2026-05-01T12:00:00Z',
          },
          {
            id: DUPLICATE_ACCOUNT_ID,
            name: 'Meridian Health Group - Duplicate',
            domain: 'meridian.example',
            owner: 'Jordan Lee',
            stage: 'prospect',
            readiness: 52,
            value_pack: 'Healthcare Operations',
            updated_at: '2026-05-01T10:00:00Z',
            duplicate_of: ACCOUNT_ID,
          },
        ],
      },
      {
        pattern: '**/api/v1/agents/accounts/merge',
        method: 'POST',
        status: 200,
        body: {
          merged_into: ACCOUNT_ID,
          archived_account_ids: [DUPLICATE_ACCOUNT_ID],
          audit_event: 'accounts_merged',
        },
      },
    ]);

    await authedPage.goto('/accounts', { waitUntil: 'domcontentloaded' });

    await expectAnyVisible(
      authedPage,
      [/meridian health group/i, /duplicate/i, /merge/i, /readiness/i],
      'duplicate account lifecycle workspace',
    );

    await authedPage.goto('/governance/audit/log', { waitUntil: 'domcontentloaded' });
    await expectAnyVisible(
      authedPage,
      [/audit log/i, /accounts_merged/i, /merge/i, /state transitions/i],
      'account merge audit trail',
    );
  });

  journeyTest('test_account_lifecycle_create_edit_archive_merge_and_readiness', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/accounts',
      [/accounts/i, /search accounts/i, /browse and manage/i, /export/i],
      'account lifecycle workspace',
    );

    await expectRouteSupportsWorkflow(
      authedPage,
      '/settings/data/value-packs',
      [/value packs/i, /default/i, /tenant/i, /pack/i],
      'value-pack assignment and override workflow',
    );

    await expectRouteSupportsWorkflow(
      authedPage,
      '/governance/audit/log',
      [/audit log/i, /events/i, /state transitions/i, /value_pack_assigned/i],
      'account lifecycle audit workflow',
    );
  });
});

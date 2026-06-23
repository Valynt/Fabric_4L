/**
 * Journey 13: Long-Running Workflow Progress
 *
 * Traceability: PROGRESS-001 through PROGRESS-006.
 *
 * This suite validates progress indicators for long-running workflows:
 * - Slow agent job shows meaningful progress (not just spinner)
 * - Long ingestion jobs show ETA/stage breakdown
 * - Cancel operation is available and works correctly
 * - Progress persists across page refresh
 * - Progress stages are clearly communicated
 * - Error states during long workflows are handled
 *
 * Priority: P1 production confidence
 * Mode: Contract (mocked progress updates)
 */

import { journeyTest, expect } from '../helpers/journey-fixture';
import { expectAnyVisible, expectRouteSupportsWorkflow } from '../helpers/validation-program';

journeyTest.describe('Journey 13: Long-Running Workflow Progress', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    // Default mocks for job data
    await addMocks([
      {
        pattern: '**/api/v1/ingest/jobs',
        body: [
          { id: 'job-001', domain: 'example.com', status: 'processing', progress: 45 },
        ],
      },
    ]);
  });

  // ── Meaningful Progress Indicators ─────────────────────────────────────────

  journeyTest('PROGRESS-001: slow agent job shows meaningful progress beyond spinner', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/agents/workflows/**',
        body: {
          id: 'workflow-001',
          status: 'running',
          progress: 35,
          current_stage: 'Analyzing signals',
          stages: [
            { name: 'Ingestion', status: 'completed', progress: 100 },
            { name: 'Analysis', status: 'running', progress: 35 },
            { name: 'Synthesis', status: 'pending', progress: 0 },
          ],
        },
      },
    ]);

    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Should show progress percentage and current stage
    await expectAnyVisible(
      authedPage,
      [/35%|progress|analyzing|signals/i],
      'progress indicator with stage',
    );
  });

  journeyTest('PROGRESS-002: progress indicator shows percentage complete', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/ingest/jobs/job-001',
        body: {
          id: 'job-001',
          domain: 'example.com',
          status: 'processing',
          progress: 67,
          current_stage: 'Extraction',
        },
      },
    ]);

    await authedPage.goto('/context/ingestion/jobs/job-001', { waitUntil: 'domcontentloaded' });

    // Should show percentage
    await expectAnyVisible(
      authedPage,
      [/67%|progress|67 percent/i],
      'progress percentage',
    );
  });

  // ── ETA and Stage Breakdown ───────────────────────────────────────────────

  journeyTest('PROGRESS-003: long ingestion job shows ETA', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/ingest/jobs/job-001',
        body: {
          id: 'job-001',
          domain: 'example.com',
          status: 'processing',
          progress: 45,
          eta_seconds: 180,
          current_stage: 'Extraction',
        },
      },
    ]);

    await authedPage.goto('/context/ingestion/jobs/job-001', { waitUntil: 'domcontentloaded' });

    // Should show ETA or time remaining
    await expectAnyVisible(
      authedPage,
      [/eta|time remaining|minutes|seconds/i],
      'ETA display',
    );
  });

  journeyTest('PROGRESS-004: job shows stage breakdown', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/ingest/jobs/job-001',
        body: {
          id: 'job-001',
          domain: 'example.com',
          status: 'processing',
          progress: 45,
          stages: [
            { name: 'Crawling', status: 'completed', progress: 100 },
            { name: 'Extraction', status: 'running', progress: 50 },
            { name: 'Graph Generation', status: 'pending', progress: 0 },
          ],
        },
      },
    ]);

    await authedPage.goto('/context/ingestion/jobs/job-001', { waitUntil: 'domcontentloaded' });

    // Should show stage names and statuses
    await expectAnyVisible(
      authedPage,
      [/crawling|extraction|graph|completed|running|pending/i],
      'stage breakdown',
    );
  });

  // ── Cancel Operation ─────────────────────────────────────────────────────

  journeyTest('PROGRESS-005: cancel button is available during long-running job', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/ingest/jobs/job-001',
        body: {
          id: 'job-001',
          domain: 'example.com',
          status: 'processing',
          progress: 30,
          cancellable: true,
        },
      },
    ]);

    await authedPage.goto('/context/ingestion/jobs/job-001', { waitUntil: 'domcontentloaded' });

    // Cancel button should be visible
    const cancelBtn = authedPage.getByRole('button', { name: /cancel|stop/i }).first();
    await expect(cancelBtn).toBeVisible({ timeout: 10000 });
  });

  journeyTest('PROGRESS-006: cancel operation works correctly', async ({ authedPage, addMocks }) => {
    let cancelled = false;
    await addMocks([
      {
        pattern: '**/api/v1/ingest/jobs/job-001/cancel',
        handler: async (route) => {
          cancelled = true;
          await route.fulfill({ status: 200, body: JSON.stringify({ success: true }) });
        },
      },
      {
        pattern: '**/api/v1/ingest/jobs/job-001',
        body: {
          id: 'job-001',
          domain: 'example.com',
          status: 'processing',
          progress: 30,
          cancellable: true,
        },
      },
    ]);

    await authedPage.goto('/context/ingestion/jobs/job-001', { waitUntil: 'domcontentloaded' });

    const cancelBtn = authedPage.getByRole('button', { name: /cancel|stop/i }).first();
    await cancelBtn.click();

    // Verify cancel was called
    expect(cancelled).toBe(true);

    // Should show cancelled status
    await expectAnyVisible(
      authedPage,
      [/cancelled|stopped|canceled/i],
      'cancelled status',
    );
  });

  journeyTest('PROGRESS-007: cancel confirmation dialog appears', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/ingest/jobs/job-001',
        body: {
          id: 'job-001',
          domain: 'example.com',
          status: 'processing',
          progress: 30,
          cancellable: true,
        },
      },
    ]);

    await authedPage.goto('/context/ingestion/jobs/job-001', { waitUntil: 'domcontentloaded' });

    const cancelBtn = authedPage.getByRole('button', { name: /cancel|stop/i }).first();
    await cancelBtn.click();

    // Should show confirmation dialog
    await expectAnyVisible(
      authedPage,
      [/are you sure|confirm|cancel job/i],
      'cancel confirmation',
    );
  });

  // ── Progress Persistence Across Refresh ───────────────────────────────────

  journeyTest('PROGRESS-008: progress persists across page refresh', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/ingest/jobs/job-001',
        body: {
          id: 'job-001',
          domain: 'example.com',
          status: 'processing',
          progress: 55,
          current_stage: 'Extraction',
        },
      },
    ]);

    await authedPage.goto('/context/ingestion/jobs/job-001', { waitUntil: 'domcontentloaded' });

    // Verify progress is shown
    await expectAnyVisible(authedPage, [/55%|progress/i], 'initial progress');

    // Refresh page
    await authedPage.reload({ waitUntil: 'domcontentloaded' });

    // Progress should still be shown
    await expectAnyVisible(authedPage, [/55%|progress/i], 'progress after refresh');
  });

  journeyTest('PROGRESS-009: progress stages persist across refresh', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/ingest/jobs/job-001',
        body: {
          id: 'job-001',
          domain: 'example.com',
          status: 'processing',
          progress: 55,
          stages: [
            { name: 'Crawling', status: 'completed', progress: 100 },
            { name: 'Extraction', status: 'running', progress: 55 },
            { name: 'Graph Generation', status: 'pending', progress: 0 },
          ],
        },
      },
    ]);

    await authedPage.goto('/context/ingestion/jobs/job-001', { waitUntil: 'domcontentloaded' });

    // Refresh page
    await authedPage.reload({ waitUntil: 'domcontentloaded' });

    // Stages should still be shown
    await expectAnyVisible(
      authedPage,
      [/crawling|extraction|graph/i],
      'stages after refresh',
    );
  });

  // ── Progress Stage Communication ─────────────────────────────────────────

  journeyTest('PROGRESS-010: current stage is clearly highlighted', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/ingest/jobs/job-001',
        body: {
          id: 'job-001',
          domain: 'example.com',
          status: 'processing',
          progress: 55,
          current_stage: 'Extraction',
          stages: [
            { name: 'Crawling', status: 'completed', progress: 100 },
            { name: 'Extraction', status: 'running', progress: 55 },
            { name: 'Graph Generation', status: 'pending', progress: 0 },
          ],
        },
      },
    ]);

    await authedPage.goto('/context/ingestion/jobs/job-001', { waitUntil: 'domcontentloaded' });

    // Current stage should be visually distinct (active, highlighted, etc.)
    await expectAnyVisible(
      authedPage,
      [/extraction|running|active|current/i],
      'current stage highlight',
    );
  });

  journeyTest('PROGRESS-011: completed stages are marked as done', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/ingest/jobs/job-001',
        body: {
          id: 'job-001',
          domain: 'example.com',
          status: 'processing',
          progress: 55,
          stages: [
            { name: 'Crawling', status: 'completed', progress: 100 },
            { name: 'Extraction', status: 'running', progress: 55 },
            { name: 'Graph Generation', status: 'pending', progress: 0 },
          ],
        },
      },
    ]);

    await authedPage.goto('/context/ingestion/jobs/job-001', { waitUntil: 'domcontentloaded' });

    // Completed stages should show checkmarks or similar indicators
    await expectAnyVisible(
      authedPage,
      [/crawling|completed|done|✓|check/i],
      'completed stage indicator',
    );
  });

  // ── Error States During Long Workflows ───────────────────────────────────

  journeyTest('PROGRESS-012: error during long workflow shows actionable message', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/ingest/jobs/job-001',
        body: {
          id: 'job-001',
          domain: 'example.com',
          status: 'failed',
          progress: 45,
          error: 'Connection timeout during extraction',
          error_code: 'TIMEOUT',
          retryable: true,
        },
      },
    ]);

    await authedPage.goto('/context/ingestion/jobs/job-001', { waitUntil: 'domcontentloaded' });

    // Should show error message
    await expectAnyVisible(
      authedPage,
      [/error|failed|timeout|retry/i],
      'error message',
    );
  });

  journeyTest('PROGRESS-013: retry option available for failed workflow', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/ingest/jobs/job-001',
        body: {
          id: 'job-001',
          domain: 'example.com',
          status: 'failed',
          progress: 45,
          error: 'Connection timeout',
          retryable: true,
        },
      },
    ]);

    await authedPage.goto('/context/ingestion/jobs/job-001', { waitUntil: 'domcontentloaded' });

    // Retry button should be available
    const retryBtn = authedPage.getByRole('button', { name: /retry|restart/i }).first();
    await expect(retryBtn).toBeVisible({ timeout: 10000 });
  });

  journeyTest('PROGRESS-014: workflow completion shows success state', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/ingest/jobs/job-001',
        body: {
          id: 'job-001',
          domain: 'example.com',
          status: 'completed',
          progress: 100,
          completed_at: '2026-05-27T12:00:00Z',
        },
      },
    ]);

    await authedPage.goto('/context/ingestion/jobs/job-001', { waitUntil: 'domcontentloaded' });

    // Should show success state
    await expectAnyVisible(
      authedPage,
      [/completed|success|done|finished|100%/i],
      'success state',
    );
  });
});

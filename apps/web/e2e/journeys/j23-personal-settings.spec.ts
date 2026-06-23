/**
 * Journey 23: Personal Settings
 *
 * Traceability: PERSONAL-001 through PERSONAL-006.
 * Validates direct P1 coverage for the /personal/* route family so personal
 * profile, security, preferences, notifications, sessions, and activity pages
 * are not covered only indirectly through collaboration or layout tests.
 */
import { journeyTest, expect } from '../helpers/journey-fixture';
import {
  expectAnyVisible,
  expectRouteSupportsWorkflow,
} from '../helpers/validation-program';

const SECURITY_AUDIT_RESPONSE = {
  entries: [
    {
      id: 'personal-audit-001',
      timestamp: '2026-05-15T12:00:00Z',
      source: 'access_log',
      event_type: 'security',
      entity_id: 'test-user-e2e',
      entity_type: 'user',
      action: 'Password changed',
      agent: 'auth-service',
      details: { route: '/personal/security' },
      event_hash: 'hash-personal-audit-001',
      event_reference: 'evt-personal-audit-001',
    },
    {
      id: 'personal-audit-002',
      timestamp: '2026-05-16T08:30:00Z',
      source: 'access_log',
      event_type: 'security',
      entity_id: 'test-user-e2e',
      entity_type: 'user',
      action: 'Session revoked',
      agent: 'auth-service',
      details: { route: '/personal/sessions' },
      event_hash: 'hash-personal-audit-002',
      event_reference: 'evt-personal-audit-002',
    },
  ],
  total: 2,
  page: 1,
  per_page: 20,
};

journeyTest.describe('Journey 23: Personal Settings', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/agents/audit/logs**',
        body: SECURITY_AUDIT_RESPONSE,
      },
    ]);
  });

  journeyTest('PERSONAL-001: profile page exposes editable identity fields', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/personal/profile',
      [/profile information/i, /full name/i, /default workspace/i],
      'personal profile settings',
    );

    await expect(authedPage.getByLabel(/full name/i)).toBeVisible();
    await expect(authedPage.getByLabel(/email/i)).toBeVisible();
  });

  journeyTest('PERSONAL-002: security page exposes password, MFA, and linked-account controls', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/personal/security',
      [/password/i, /two-factor authentication/i, /linked accounts/i],
      'personal security settings',
    );

    await expect(authedPage.getByLabel(/current password/i)).toBeVisible();
    await expect(authedPage.getByRole('button', { name: /update password/i })).toBeVisible();
    await expect(authedPage.getByRole('button', { name: /enable authenticator app/i })).toBeVisible();
  });

  journeyTest('PERSONAL-003: preferences page exposes appearance, localization, and permission state', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/personal/preferences',
      [/appearance/i, /localization/i, /access & permissions/i],
      'personal preferences settings',
    );

    await expectAnyVisible(
      authedPage,
      [/personal/i, /allowed/i],
      'personal capability state',
    );
  });

  journeyTest('PERSONAL-004: notification settings expose channels and event subscriptions', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/personal/notifications',
      [/notification channels/i, /event subscriptions/i, /security alerts/i],
      'personal notification settings',
    );

    await expect(authedPage.getByText(/email alerts/i).first()).toBeVisible();
    await expect(authedPage.getByText(/data ingestion completions/i).first()).toBeVisible();
  });

  journeyTest('PERSONAL-005: sessions page exposes current session and revoke affordances', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/personal/sessions',
      [/active sessions/i, /current/i, /sign out everywhere/i],
      'personal active sessions',
    );

    await expect(authedPage.getByRole('button', { name: /sign out all other sessions/i })).toBeVisible();
    await expect(authedPage.getByRole('button', { name: /revoke/i }).first()).toBeVisible();
  });

  journeyTest('PERSONAL-006: activity page shows personal security and account audit events', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/personal/activity',
      [/recent security & account events/i, /password changed|session revoked/i],
      'personal activity audit trail',
    );
  });
});

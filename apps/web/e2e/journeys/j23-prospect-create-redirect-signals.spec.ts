import { journeyTest, expect } from '../helpers/journey-fixture';

journeyTest.describe('Prospect create-account routing', () => {
  journeyTest('CREATE-ACCOUNT-001: create-account lands on signals for created account and loads account-scoped data', async ({ authedPage, addMocks }) => {
    const createdAccountId = 'acct-create-flow-001';
    let requestedSignalsPath: string | null = null;

    await addMocks([
      {
        pattern: '**/api/v1/agents/accounts',
        method: 'POST',
        status: 201,
        body: {
          account: {
            id: createdAccountId,
            name: 'Create Flow Account',
            industry: 'Technology',
            created_at: '2026-05-07T00:00:00Z',
          },
        },
      },
      {
        pattern: `**/api/v1/agents/workspace/${createdAccountId}/signals`,
        body: {
          status: 'ready',
          generated_at: '2026-05-07T00:01:00Z',
          content: {
            signals: [
              {
                id: 'sig-create-001',
                label: 'Create-flow scoped signal',
                confidence: 0.91,
                source: 'E2E test fixture',
              },
            ],
          },
        },
      },
    ]);

    await authedPage.route(`**/api/v1/agents/workspace/${createdAccountId}/signals`, async (route) => {
      requestedSignalsPath = new URL(route.request().url()).pathname;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ready',
          generated_at: '2026-05-07T00:01:00Z',
          content: {
            signals: [
              {
                id: 'sig-create-001',
                label: 'Create-flow scoped signal',
                confidence: 0.91,
                source: 'E2E test fixture',
              },
            ],
          },
        }),
      });
    });

    await authedPage.goto('/accounts/new', { waitUntil: 'domcontentloaded' });

    await authedPage.getByPlaceholder(/company name/i).first().fill('Create Flow Account');
    await authedPage.getByPlaceholder(/website/i).first().fill('create-flow.example');

    const submitBtn = authedPage.getByRole('button', { name: /launch|start|create|begin|run|intelligence|enrichment/i }).first();
    await expect(submitBtn).toBeVisible({ timeout: 5000 });
    await submitBtn.click();

    await expect(authedPage).toHaveURL(new RegExp(`/intelligence/${createdAccountId}/signals`));
    await expect(authedPage.getByText(/create-flow scoped signal/i).first()).toBeVisible({ timeout: 10000 });
    expect(requestedSignalsPath).toBe(`/api/v1/agents/workspace/${createdAccountId}/signals`);
  });
});

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import ProspectSetup from './ProspectSetup';
import { DEFAULT_COMPANIES, DEFAULT_ACTIVITIES } from '@/lib/demoData';

describe('ProspectSetup example prompt submission', () => {
  it('submits the first demo example from the beginning step with full payload', async () => {
    const user = userEvent.setup();
    const demoCompany = DEFAULT_COMPANIES[0];
    const demoActivity = DEFAULT_ACTIVITIES[0];
    const onCreateSetup = vi.fn().mockResolvedValue({ accountId: 'acct-demo-001' });

    render(
      <MemoryRouter>
        <ProspectSetup onCreateSetup={onCreateSetup} />
      </MemoryRouter>
    );

    // 1. Verify we are at the beginning step (Launch Intelligence is disabled before context)
    const launchButton = screen.getByRole('button', { name: 'Launch Intelligence' });
    expect(launchButton).toBeDisabled();

    // 2. Restore the demo example activity (simulates clicking the recent-activity menu)
    const recentActivityTrigger = screen.getByRole('button', { name: /recent value cases/i });
    await user.click(recentActivityTrigger);

    const demoActivityEl = await screen.findByText(demoActivity.title);
    await user.click(demoActivityEl);

    // 3. Verify the prompt textarea is populated with the demo example
    const promptTextarea = screen.getByLabelText(/new value case prompt/i) as HTMLTextAreaElement;
    expect(promptTextarea.value).toContain(`Company: ${demoCompany.name}`);
    expect(promptTextarea.value).toContain(demoCompany.domain);
    expect(promptTextarea.value).toContain(demoCompany.industry);

    // 4. Launch Intelligence should now be enabled
    expect(launchButton).toBeEnabled();

    // 5. Submit the prompt
    await user.click(launchButton);

    // 6. Verify onCreateSetup was called with the expected payload shape
    expect(onCreateSetup).toHaveBeenCalledTimes(1);
    const payload = onCreateSetup.mock.calls[0][0];

    // Core identifiers
    expect(payload.companyName).toBe(demoCompany.name);
    expect(payload.companyDomain).toBe(demoCompany.domain);
    expect(payload.industry).toBe(demoCompany.industry);

    // Parsed business context
    expect(payload.buyingContext).toBe(
      'New product launch readiness across distributed field teams'
    );
    expect(payload.whyNow).toBe(
      'Need stronger rep ramp, compliant messaging, and executive discovery prep'
    );
    expect(payload.knownInitiative).toBe('Field launch enablement refresh');

    // Stakeholders
    expect(payload.stakeholders).toMatchObject({
      economicBuyer: 'VP Sales',
      champion: 'Sales Enablement Leader',
      evaluator: 'RevOps / IT',
      compliance: 'Regulatory and legal operations',
    });

    // Business pains & friction
    expect(payload.businessPain).toEqual([
      'Rep onboarding is slow for complex offerings',
      'Messaging consistency is difficult across field teams',
      'Launch content is fragmented across systems',
    ]);
    expect(payload.currentFriction).toEqual([
      'Multiple systems create version confusion',
      'Coaching quality varies by manager',
    ]);
    expect(payload.desiredOutcomes).toEqual([
      'Faster rep ramp time',
      'More consistent compliant messaging',
      'Better launch readiness',
    ]);

    // Outputs & mode
    expect(payload.desiredOutputs).toEqual([
      'account_brief',
      'discovery_prep',
      'value_hypotheses',
    ]);
    expect(payload.outputType).toBe('account_brief');
    expect(['Fast', 'Balanced', 'Deep']).toContain(payload.mode);
    expect(['light', 'standard', 'deep']).toContain(payload.enrichmentDepth);

    // Flags
    expect(payload.useUploadedFiles).toBeTypeOf('boolean');
    expect(payload.usePriorAccountContext).toBeTypeOf('boolean');
    expect(payload.runWebEnrichment).toBeTypeOf('boolean');
    expect(payload.complianceSensitive).toBeTypeOf('boolean');

    // Freeform prompt is preserved
    expect(payload.freeformPrompt).toContain(`Company: ${demoCompany.name}`);
  });

  it('submits the second demo minimal example successfully', async () => {
    const user = userEvent.setup();
    const demoActivity = DEFAULT_ACTIVITIES[1];
    const onCreateSetup = vi.fn().mockResolvedValue({ accountId: 'acct-demo-002' });

    render(
      <MemoryRouter>
        <ProspectSetup onCreateSetup={onCreateSetup} />
      </MemoryRouter>
    );

    const recentActivityTrigger = screen.getByRole('button', { name: /recent value cases/i });
    await user.click(recentActivityTrigger);

    const demoActivityEl = await screen.findByText(demoActivity.title);
    await user.click(demoActivityEl);

    const launchButton = screen.getByRole('button', { name: 'Launch Intelligence' });
    expect(launchButton).toBeEnabled();

    await user.click(launchButton);

    expect(onCreateSetup).toHaveBeenCalledTimes(1);
    const payload = onCreateSetup.mock.calls[0][0];

    expect(payload.desiredOutputs).toEqual([
      'executive_summary',
      'value_hypotheses',
    ]);
    expect(payload.freeformPrompt).toContain(demoActivity.prompt.slice(0, 20));
  });
});

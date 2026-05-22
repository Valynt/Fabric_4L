import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import ProspectSetup from './ProspectSetup';

describe('value-pilot ProspectSetup wrapper', () => {
  it('passes value-pilot mode contract and submits via shared page', async () => {
    const user = userEvent.setup();
    const onCreateSetup = vi.fn().mockResolvedValue({ accountId: 'acct-001' });

    render(<MemoryRouter><ProspectSetup onCreateSetup={onCreateSetup} /></MemoryRouter>);

    await user.type(screen.getByLabelText('New value case prompt'), 'Company: ModeCheck Inc');
    await user.click(screen.getByRole('button', { name: 'Launch Intelligence' }));

    expect(onCreateSetup).toHaveBeenCalledTimes(1);
    expect(onCreateSetup.mock.calls[0][0].companyName).toBe('ModeCheck Inc');
  });
});

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';

import ProspectSetup from '../pages/ProspectSetup';

function Wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return (
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </MemoryRouter>
  );
}

describe('prospect setup interaction smoke', () => {
  it('submits after minimum context is provided', async () => {
    const user = userEvent.setup();
    const onCreateSetup = vi.fn().mockResolvedValue({ accountId: 'acct-1' });
    render(
      <Wrapper>
        <ProspectSetup onCreateSetup={onCreateSetup} />
      </Wrapper>
    );

    await user.type(screen.getByLabelText('New value case prompt'), 'Company: TestCo');
    await user.click(screen.getByRole('button', { name: 'Launch Intelligence' }));

    expect(onCreateSetup).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole('status')).toHaveTextContent('Intelligence launched. Opening workspace...');
  });
});


describe('workflow intelligence route smoke', () => {
  it('keeps launch CTA disabled when prompt is unsafe or empty', async () => {
    const user = userEvent.setup();
    const onCreateSetup = vi.fn();
    render(
      <Wrapper>
        <ProspectSetup onCreateSetup={onCreateSetup} />
      </Wrapper>
    );

    const launch = screen.getByRole('button', { name: 'Launch Intelligence' });
    expect(launch).toBeDisabled();

    await user.type(screen.getByLabelText('New value case prompt'), '   ');
    expect(launch).toBeDisabled();
    expect(onCreateSetup).not.toHaveBeenCalled();
  });
});

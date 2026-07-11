import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { type ReactNode } from 'react';
import userEvent from '@testing-library/user-event';

import ProspectSetup from '../pages/ProspectSetup';
import { AuthProvider } from '@/contexts/AuthContext';
import { createWrapper } from '@/test-utils';
import { withAuthProvider } from '@/test/utils/withAuthProvider';

function Wrapper({ children }: { children: ReactNode }) {
  const BaseWrapper = createWrapper();
  return (
    <BaseWrapper>
      <AuthProvider>{children}</AuthProvider>
    </BaseWrapper>
  );
}

describe('prospect setup interaction smoke', () => {
  it('submits after minimum context is provided', async () => {
    await withAuthProvider('legacy', async () => {
      const user = userEvent.setup();
      const onCreateSetup = vi.fn().mockResolvedValue({ accountId: 'acct-1' });
      render(
        <ProspectSetup onCreateSetup={onCreateSetup} />,
        { wrapper: Wrapper }
      );

      await user.type(screen.getByLabelText('New value case prompt'), 'Company: TestCo');
      await user.click(screen.getByRole('button', { name: 'Launch Intelligence' }));

      expect(onCreateSetup).toHaveBeenCalledTimes(1);
      expect(await screen.findByRole('status')).toHaveTextContent('Intelligence launched. Opening workspace...');
    });
  });
});


describe('workflow intelligence route smoke', () => {
  it('keeps launch CTA disabled when prompt is unsafe or empty', async () => {
    await withAuthProvider('legacy', async () => {
      const user = userEvent.setup();
      const onCreateSetup = vi.fn();
      render(
        <ProspectSetup onCreateSetup={onCreateSetup} />,
        { wrapper: Wrapper }
      );

      const launch = screen.getByRole('button', { name: 'Launch Intelligence' });
      expect(launch).toBeDisabled();

      await user.type(screen.getByLabelText('New value case prompt'), '   ');
      expect(launch).toBeDisabled();
      expect(onCreateSetup).not.toHaveBeenCalled();
    });
  });
});

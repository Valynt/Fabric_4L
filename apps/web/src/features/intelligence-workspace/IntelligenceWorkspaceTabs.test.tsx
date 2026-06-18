import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import IntelligenceWorkspaceTabs from './IntelligenceWorkspaceTabs';

vi.mock('./hooks/useWorkspaceContext', () => ({
  useWorkspaceContext: () => ({ tenantSlug: 'acme', accountId: 'acct-123', tabId: 'signals' }),
}));

describe('IntelligenceWorkspaceTabs', () => {
  it('renders horizontal tablist navigation', () => {
    render(<MemoryRouter><IntelligenceWorkspaceTabs /></MemoryRouter>);
    expect(screen.getByRole('tablist')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Signals' })).toBeInTheDocument();
  });

  it('marks only active tab as selected', () => {
    render(<MemoryRouter><IntelligenceWorkspaceTabs /></MemoryRouter>);
    expect(screen.getByRole('tab', { name: 'Signals' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: 'Account Enrichment' })).toHaveAttribute('aria-selected', 'false');
  });

  it('builds tab links using tenant, account, and tab id', () => {
    render(<MemoryRouter><IntelligenceWorkspaceTabs /></MemoryRouter>);

    expect(screen.getByRole('link', { name: 'Signals' })).toHaveAttribute(
      'href',
      '/t/acme/accounts/acct-123/intelligence/signals',
    );
    expect(screen.getByRole('link', { name: 'Drivers' })).toHaveAttribute(
      'href',
      '/t/acme/accounts/acct-123/intelligence/drivers',
    );
    expect(screen.getByRole('link', { name: 'Evidence' })).toHaveAttribute(
      'href',
      '/t/acme/accounts/acct-123/intelligence/evidence',
    );
    expect(screen.getByRole('link', { name: 'Stakeholders' })).toHaveAttribute(
      'href',
      '/t/acme/accounts/acct-123/intelligence/stakeholders',
    );
  });
});

import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../test/mocks/server';
import GovernanceEvidence from './GovernanceEvidence';
import GovernanceCompliance from './GovernanceCompliance';
import GovernanceAuditLog from './GovernanceAuditLog';
import GovernanceChangeHistory from './GovernanceChangeHistory';

function wrapperWithPath(path: string) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    return (
      <MemoryRouter initialEntries={[path]}>
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </MemoryRouter>
    );
  };
}

function useGovernanceHandlers() {
  server.use(
    http.get('/api/v1/agents/ground-truth/truths', () => {
      return HttpResponse.json({
        items: [
          {
            id: 'truth-001',
            claim: 'Compliance requirement verified',
            claim_type: 'compliance_requirement',
            status: 'verified',
            maturity_level: 3,
            confidence: 0.92,
            is_stale: false,
            updated_at: '2026-04-27T10:00:00Z',
          },
        ],
        total: 1,
      });
    }),
    http.get('/api/v1/agents/ground-truth/maturity-ladder', () => {
      return HttpResponse.json({
        levels: [
          { level: 4, name: 'Validated', description: 'Human-validated truth', required_status: 'validated', advancement_trigger: 'Human review completed' },
        ],
      });
    }),
    http.get('/api/v1/agents/ground-truth/truths/freshness-summary', () => {
      return HttpResponse.json({
        tenant_id: "tenant-demo",
        timestamp: "2026-01-02T00:00:00Z",
        summary: { stale: 0, fresh: 1, expiring_soon: 0, total: 1 },
        warning_threshold_days: 14,
      });
    }),
    http.get('/api/v1/agents/ground-truth/truths/stale', () => {
      return HttpResponse.json({
        items: [],
        total: 0,
        limit: 50,
        offset: 0,
        has_more: false,
      });
    }),
    http.get('/api/v1/agents/ground-truth/truths/:truthId/audit', () => {
      return HttpResponse.json([
        {
          id: 'audit-001',
          timestamp: '2026-04-27T10:05:00Z',
          action: 'validate',
          actor: 'governance-agent',
        },
      ]);
    })
  );
}

describe('Governance pages (L5-backed)', () => {
  it('renders evidence page with L5 truth data', async () => {
    useGovernanceHandlers();
    render(<GovernanceEvidence />, { wrapper: wrapperWithPath('/governance/evidence') });

    expect(await screen.findByRole('heading', { name: 'Evidence' })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/Truth Objects \(\d+\)/)).toBeInTheDocument();
    });
  });

  it('renders compliance page with L5 handlers', async () => {
    useGovernanceHandlers();
    render(<GovernanceCompliance />, { wrapper: wrapperWithPath('/governance/compliance') });

    expect(await screen.findByRole('heading', { name: 'Compliance' })).toBeInTheDocument();
    expect(await screen.findByText(/Total truths/)).toBeInTheDocument();
  });

  it('renders governance audit-specific pages with L5 handlers', async () => {
    useGovernanceHandlers();
    const { unmount } = render(<GovernanceAuditLog />, {
      wrapper: wrapperWithPath('/governance/audit/log'),
    });

    expect(await screen.findByRole('heading', { name: 'Audit Log' })).toBeInTheDocument();
    unmount();

    useGovernanceHandlers();
    render(<GovernanceChangeHistory />, {
      wrapper: wrapperWithPath('/governance/audit/changes'),
    });

    expect(await screen.findByRole('heading', { name: 'Change History' })).toBeInTheDocument();
  });
});

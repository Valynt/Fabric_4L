import React from 'react';
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import {
  useBusinessCaseExport,
  useBusinessCase,
  useRegenerateBusinessCase,
  downloadExport,
  type BusinessCase,
} from './useDocuments';
import { QK } from './queryKeys';

// Mock the apiClient
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

// Helper to create mock responses
function createMockResponse<T>(data: T): { data: T; status: number } {
  return { data, status: 200 };
}

// Helper to create wrapper with QueryClient
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

// Sample data
const sampleBusinessCase: BusinessCase = {
  case_id: 'bc-001',
  title: 'Test Business Case',
  summary: 'A test business case summary',
  total_value: 1000000,
  implementation_cost: 500000,
  roi_ratio: 2.0,
  payback_months: 12,
  confidence_score: 0.85,
  recommendations: ['Implement feature A', 'Consider feature B'],
  status: 'completed',
  created_at: '2024-01-01T00:00:00Z',
  document_url: 'https://example.com/doc.pdf',
  page_count: 10,
  file_size_bytes: 1024000,
};

describe('useDocuments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useBusinessCaseExport hook', () => {
    it('should export business case via L4 endpoint', async () => {
      (apiClient.get as Mock).mockResolvedValueOnce(
        createMockResponse({
          case_id: 'bc-001',
          format: 'pdf',
          document_url: 'https://example.com/bc-001.pdf',
          download_ready: true,
        })
      );

      const { result } = renderHook(() => useBusinessCaseExport(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ caseId: 'bc-001', format: 'pdf' });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(apiClient.get).toHaveBeenCalledWith(
        'l4',
        '/cases/bc-001/export?format=pdf'
      );
      expect(result.current.data?.download_ready).toBe(true);
    });

    it('should handle missing business case', async () => {
      (apiClient.get as Mock).mockRejectedValueOnce(
        new Error('Business case not found')
      );

      const { result } = renderHook(() => useBusinessCaseExport(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ caseId: 'bc-999', format: 'pdf' });

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe('useBusinessCase hook', () => {
    it('should fetch business case successfully', async () => {
      (apiClient.get as Mock).mockResolvedValueOnce(
        createMockResponse(sampleBusinessCase)
      );

      const { result } = renderHook(() => useBusinessCase('bc-001'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(apiClient.get).toHaveBeenCalledWith('l4', '/cases/bc-001');
      expect(result.current.data?.case_id).toBe('bc-001');
      expect(result.current.data?.title).toBe('Test Business Case');
    });

    it('should not fetch when businessCaseId is null', () => {
      renderHook(() => useBusinessCase(null), {
        wrapper: createWrapper(),
      });

      expect(apiClient.get).not.toHaveBeenCalled();
    });

    it('should handle missing business case', async () => {
      (apiClient.get as Mock).mockRejectedValueOnce(new Error('Not found'));

      const { result } = renderHook(() => useBusinessCase('bc-999'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe('useRegenerateBusinessCase hook', () => {
    it('should invalidate the cached business case detail after successful regeneration', async () => {
      (apiClient.post as Mock).mockResolvedValueOnce(
        createMockResponse(sampleBusinessCase)
      );

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
          },
        },
      });
      queryClient.setQueryData(QK.documents.businessCase('bc-001'), sampleBusinessCase);

      function Wrapper({ children }: { children: React.ReactNode }) {
        return (
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        );
      }

      const { result } = renderHook(() => useRegenerateBusinessCase(), {
        wrapper: Wrapper,
      });

      result.current.mutate({ caseId: 'bc-001', accountId: 'acc-001' });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(apiClient.post).toHaveBeenCalledWith(
        'l4',
        '/cases/bc-001/regenerate',
        expect.objectContaining({
          previous_case_id: 'bc-001',
          account_id: 'acc-001',
        })
      );
      expect(
        queryClient.getQueryState(QK.documents.businessCase('bc-001'))?.isInvalidated
      ).toBe(true);
    });
  });

  describe('downloadExport helper', () => {
    let mockLink: HTMLAnchorElement;
    let mockClick: Mock;

    beforeEach(() => {
      mockClick = vi.fn();
      mockLink = {
        href: '',
        download: '',
        click: mockClick,
      } as unknown as HTMLAnchorElement;

      vi.spyOn(document, 'createElement').mockReturnValue(mockLink);
      vi.spyOn(document.body, 'appendChild').mockImplementation(() => mockLink);
      vi.spyOn(document.body, 'removeChild').mockImplementation(() => mockLink);
    });

    it('should trigger download with valid URL', () => {
      downloadExport('https://example.com/doc.pdf', 'business-case.pdf');

      expect(document.createElement).toHaveBeenCalledWith('a');
      expect(mockLink.href).toBe('https://example.com/doc.pdf');
      expect(mockLink.download).toBe('business-case.pdf');
      expect(mockClick).toHaveBeenCalled();
    });

    it('should throw error for javascript: URL (XSS prevention)', () => {
      expect(() => {
        downloadExport('javascript:alert("xss")', 'bad.pdf');
      }).toThrow('unsupported protocol');
    });

    it('should throw error for unsupported URL protocol', () => {
      expect(() => {
        downloadExport('ftp://example.com/doc.pdf', 'bad.pdf');
      }).toThrow('unsupported protocol');
    });

    it('should support blob URLs', () => {
      downloadExport('blob:https://example.com/abc123', 'blob.pdf');

      expect(mockLink.href).toBe('blob:https://example.com/abc123');
      expect(mockClick).toHaveBeenCalled();
    });

    it('should support data URLs', () => {
      downloadExport('data:application/pdf;base64,ABC123', 'data.pdf');

      expect(mockLink.href).toBe('data:application/pdf;base64,ABC123');
      expect(mockClick).toHaveBeenCalled();
    });
  });
});

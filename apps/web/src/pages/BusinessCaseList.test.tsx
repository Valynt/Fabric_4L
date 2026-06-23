/**
 * BusinessCaseList Component Tests
 *
 * Tests for P2/P3 fixes including:
 * - shadcn Select usage for status filter (replaced native <select>)
 * - shadcn Select usage for sort field (replaced native <select>)
 * - VirtualList integration for case list
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { createWrapper } from '../test-utils';
import BusinessCaseList from './BusinessCaseList';

// Mock useBusinessCases to avoid API dependency
vi.mock('@/hooks/useBusinessCases', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/useBusinessCases')>();
  return {
    ...actual,
    useBusinessCases: () => ({
      data: [
        {
          id: 'case-001',
          name: 'Q1 Expansion',
          company: 'Acme Corp',
          status: 'active' as const,
          totalValue: '$1.2M',
          confidence: 0.92,
          updatedAt: '2024-01-15T10:00:00Z',
        },
      ],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    }),
    useCreateBusinessCase: () => ({
      mutate: vi.fn(),
      isPending: false,
    }),
    useArchiveBusinessCase: () => ({
      mutate: vi.fn(),
      isPending: false,
    }),
  };
});

// Mock matchMedia for responsive tests
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

describe('BusinessCaseList', () => {
  it('renders page header', () => {
    const wrapper = createWrapper();
    render(<BusinessCaseList />, { wrapper });

    expect(screen.getByRole('heading', { name: /business cases/i })).toBeInTheDocument();
  });

  it('uses shadcn Select for status filter (not native select)', () => {
    const wrapper = createWrapper();
    render(<BusinessCaseList />, { wrapper });

    // Should NOT have native <select> elements
    const nativeSelects = document.querySelectorAll('select');
    expect(nativeSelects.length).toBe(0);
  });

  it('uses shadcn Select for sort field (not native select)', () => {
    const wrapper = createWrapper();
    render(<BusinessCaseList />, { wrapper });

    // Should NOT have native <select> elements
    const nativeSelects = document.querySelectorAll('select');
    expect(nativeSelects.length).toBe(0);

    // Should have sort label
    expect(screen.getByText(/sort by/i)).toBeInTheDocument();
  });

  it('renders virtualized case list container', () => {
    const wrapper = createWrapper();
    render(<BusinessCaseList />, { wrapper });

    // VirtualList applies contain: strict
    const virtualContainer = document.querySelector('[style*="contain: strict"]');
    expect(virtualContainer).toBeInTheDocument();
  });

  it('has aria-label on sort direction toggle', () => {
    const wrapper = createWrapper();
    render(<BusinessCaseList />, { wrapper });

    // The sort direction button should have an aria-label
    const sortToggle = screen.getByRole('button', { name: /sort/i });
    expect(sortToggle).toBeInTheDocument();
  });

  it('shadcn Select triggers are present for filters', () => {
    const wrapper = createWrapper();
    render(<BusinessCaseList />, { wrapper });

    // shadcn Select renders trigger buttons with combobox role
    const triggers = document.querySelectorAll('[role="combobox"]');
    expect(triggers.length).toBeGreaterThanOrEqual(2);
  });
});

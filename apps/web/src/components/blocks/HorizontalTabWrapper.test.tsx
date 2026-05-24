/**
 * HorizontalTabWrapper Component Tests
 *
 * Tests for the HorizontalTabWrapper component.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { HorizontalTabWrapper } from './HorizontalTabWrapper';

// Mock react-router-dom
const mockUseSearchParams = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useSearchParams: () => mockUseSearchParams(),
  };
});

describe('HorizontalTabWrapper', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders null when tabs array is empty', () => {
    mockUseSearchParams.mockReturnValue([new URLSearchParams(), vi.fn()]);
    
    const { container } = render(
      <HorizontalTabWrapper tabs={[]} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders tabs from configuration', () => {
    mockUseSearchParams.mockReturnValue([new URLSearchParams(), vi.fn()]);
    
    const tabs = [
      { id: 'tab1', label: 'Tab 1', content: <div>Content 1</div> },
      { id: 'tab2', label: 'Tab 2', content: <div>Content 2</div> },
    ];
    
    render(<HorizontalTabWrapper tabs={tabs} />);
    
    expect(screen.getByText('Tab 1')).toBeInTheDocument();
    expect(screen.getByText('Tab 2')).toBeInTheDocument();
  });

  it('renders active tab content', () => {
    const setSearchParams = vi.fn();
    mockUseSearchParams.mockReturnValue([new URLSearchParams('tab=tab1'), setSearchParams]);
    
    const tabs = [
      { id: 'tab1', label: 'Tab 1', content: <div>Content 1</div> },
      { id: 'tab2', label: 'Tab 2', content: <div>Content 2</div> },
    ];
    
    render(<HorizontalTabWrapper tabs={tabs} />);
    
    expect(screen.getByText('Content 1')).toBeInTheDocument();
    expect(screen.queryByText('Content 2')).not.toBeInTheDocument();
  });

  it('uses defaultTab when no tab in URL', () => {
    const setSearchParams = vi.fn();
    mockUseSearchParams.mockReturnValue([new URLSearchParams(), setSearchParams]);
    
    const tabs = [
      { id: 'tab1', label: 'Tab 1', content: <div>Content 1</div> },
      { id: 'tab2', label: 'Tab 2', content: <div>Content 2</div> },
    ];
    
    render(<HorizontalTabWrapper tabs={tabs} defaultTab="tab2" />);
    
    expect(screen.getByText('Content 2')).toBeInTheDocument();
  });

  it('uses first tab when no tab in URL and no defaultTab', () => {
    const setSearchParams = vi.fn();
    mockUseSearchParams.mockReturnValue([new URLSearchParams(), setSearchParams]);
    
    const tabs = [
      { id: 'tab1', label: 'Tab 1', content: <div>Content 1</div> },
      { id: 'tab2', label: 'Tab 2', content: <div>Content 2</div> },
    ];
    
    render(<HorizontalTabWrapper tabs={tabs} />);
    
    expect(screen.getByText('Content 1')).toBeInTheDocument();
  });

  it('calls setSearchParams when tab is changed', () => {
    const setSearchParams = vi.fn();
    mockUseSearchParams.mockReturnValue([new URLSearchParams(), setSearchParams]);
    
    const tabs = [
      { id: 'tab1', label: 'Tab 1', content: <div>Content 1</div> },
      { id: 'tab2', label: 'Tab 2', content: <div>Content 2</div> },
    ];
    
    render(<HorizontalTabWrapper tabs={tabs} />);
    
    // Click on tab2
    screen.getByText('Tab 2').click();
    expect(setSearchParams).toHaveBeenCalledTimes(1);
    expect(typeof setSearchParams.mock.calls[0][0]).toBe('function');
  });

  it('falls back to first tab when URL tab does not exist', () => {
    const setSearchParams = vi.fn();
    mockUseSearchParams.mockReturnValue([new URLSearchParams('tab=nonexistent'), setSearchParams]);
    
    const tabs = [
      { id: 'tab1', label: 'Tab 1', content: <div>Content 1</div> },
      { id: 'tab2', label: 'Tab 2', content: <div>Content 2</div> },
    ];
    
    render(<HorizontalTabWrapper tabs={tabs} />);
    
    // Should render first tab content as fallback
    expect(screen.getByText('Content 1')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    mockUseSearchParams.mockReturnValue([new URLSearchParams(), vi.fn()]);
    
    const tabs = [
      { id: 'tab1', label: 'Tab 1', content: <div>Content 1</div> },
    ];
    
    const { container } = render(
      <HorizontalTabWrapper tabs={tabs} className="custom-class" />
    );
    expect(container.firstChild).toHaveClass('custom-class');
  });
});

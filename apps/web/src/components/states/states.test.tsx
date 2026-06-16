/**
 * State Components Tests
 *
 * Tests for LoadingState, EmptyState, ErrorState, and PageState components.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { LoadingState } from './LoadingState';
import { EmptyState } from './EmptyState';
import { ErrorState } from './ErrorState';
import { PageState } from './PageState';
import { Lightbulb } from 'lucide-react';

describe('LoadingState', () => {
  it('renders with default message', () => {
    render(<LoadingState />);
    expect(screen.getByText('Loading…')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveAttribute('aria-busy', 'true');
  });

  it('renders with custom message', () => {
    render(<LoadingState message="Loading signals..." />);
    expect(screen.getByText('Loading signals...')).toBeInTheDocument();
  });

  it('has centered layout', () => {
    const { container } = render(<LoadingState />);
    expect(container.firstChild).toHaveClass('flex', 'flex-col', 'items-center', 'justify-center');
  });
});

describe('EmptyState', () => {
  it('renders with title', () => {
    render(<EmptyState title="No data" />);
    expect(screen.getByText('No data')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('No data');
  });

  it('renders with description', () => {
    render(<EmptyState title="No data" description="Try again later" />);
    expect(screen.getByText('Try again later')).toBeInTheDocument();
  });

  it('renders with custom icon', () => {
    render(<EmptyState title="No hypotheses" icon={Lightbulb} />);
    expect(document.querySelector('svg')).toBeInTheDocument();
  });

  it('renders with action', () => {
    const action = <button>Go to Accounts</button>;
    render(<EmptyState title="Select account" action={action} />);
    expect(screen.getByRole('button', { name: /go to accounts/i })).toBeInTheDocument();
  });
});

describe('ErrorState', () => {
  it('renders with title', () => {
    render(<ErrorState title="Failed to load" />);
    expect(screen.getByText('Failed to load')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Failed to load');
  });

  it('renders with description', () => {
    render(<ErrorState title="Error" description="Network error" />);
    expect(screen.getByText('Network error')).toBeInTheDocument();
  });

  it('renders retry button when onRetry provided', () => {
    const onRetry = vi.fn();
    render(<ErrorState title="Error" onRetry={onRetry} />);
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('calls onRetry when retry button clicked', () => {
    const onRetry = vi.fn();
    render(<ErrorState title="Error" onRetry={onRetry} />);
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('toggles error details when show details clicked', () => {
    const error = new Error('Detailed error message');
    render(<ErrorState title="Error" error={error} />);
    
    const toggle = screen.getByRole('button', { name: /show details/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(toggle);
    expect(screen.getByText('Detailed error message')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /hide details/i })).toHaveAttribute('aria-expanded', 'true');
    
    fireEvent.click(screen.getByText(/hide details/i));
    expect(screen.queryByText('Detailed error message')).not.toBeInTheDocument();
  });
});

describe('PageState', () => {
  it('shows loading state', () => {
    render(
      <PageState
        isLoading={true}
        isError={false}
        data={null}
        emptyTitle="Empty"
        errorTitle="Error"
      >
        <div>Content</div>
      </PageState>
    );
    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  it('shows empty state when data is undefined and isEmpty is provided', () => {
    render(
      <PageState
        isLoading={false}
        isError={false}
        data={undefined}
        isEmpty={(d: string[]) => d.length === 0}
        emptyTitle="No items"
        errorTitle="Error"
      >
        <div>Content</div>
      </PageState>
    );
    expect(screen.getByText('No items')).toBeInTheDocument();
  });

  it('does not throw when data is undefined and isEmpty is not provided', () => {
    expect(() => {
      render(
        <PageState
          isLoading={false}
          isError={false}
          data={undefined}
          emptyTitle="No items"
          errorTitle="Error"
        >
          <div>Content</div>
        </PageState>
      );
    }).not.toThrow();
    expect(screen.getByText('No items')).toBeInTheDocument();
  });

  it('shows error state', () => {
    render(
      <PageState
        isLoading={false}
        isError={true}
        data={null}
        emptyTitle="Empty"
        errorTitle="Signals could not be loaded"
      >
        <div>Content</div>
      </PageState>
    );
    expect(screen.getByText('Signals could not be loaded')).toBeInTheDocument();
  });

  it('shows empty state when data is empty array', () => {
    render(
      <PageState
        isLoading={false}
        isError={false}
        data={[]}
        isEmpty={(d) => d.length === 0}
        emptyTitle="No items"
        errorTitle="Error"
      >
        <div>Content</div>
      </PageState>
    );
    expect(screen.getByText('No items')).toBeInTheDocument();
  });

  it('renders children when data is present', () => {
    render(
      <PageState
        isLoading={false}
        isError={false}
        data={['item']}
        isEmpty={(d) => d.length === 0}
        emptyTitle="No items"
        errorTitle="Error"
      >
        <div>Content loaded</div>
      </PageState>
    );
    expect(screen.getByText('Content loaded')).toBeInTheDocument();
  });
});

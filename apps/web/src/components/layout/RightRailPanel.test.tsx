/**
 * RightRailPanel Component Tests
 *
 * Tests for the RightRailPanel component.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { RightRailPanel } from './RightRailPanel';

describe('RightRailPanel', () => {
  it('renders with title', () => {
    render(<RightRailPanel title="Test Panel" onClose={vi.fn()}>Content</RightRailPanel>);
    expect(screen.getByText('Test Panel')).toBeInTheDocument();
  });

  it('renders children content', () => {
    render(<RightRailPanel title="Panel" onClose={vi.fn()}>Panel Content</RightRailPanel>);
    expect(screen.getByText('Panel Content')).toBeInTheDocument();
  });

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn();
    render(<RightRailPanel title="Panel" onClose={onClose}>Content</RightRailPanel>);
    
    const closeButton = screen.getByLabelText('Close panel');
    fireEvent.click(closeButton);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('renders status when provided', () => {
    render(
      <RightRailPanel 
        title="Panel" 
        onClose={vi.fn()} 
        status={<span>Status Badge</span>}
      >
        Content
      </RightRailPanel>
    );
    expect(screen.getByText('Status Badge')).toBeInTheDocument();
  });

  it('renders footer when provided', () => {
    render(
      <RightRailPanel 
        title="Panel" 
        onClose={vi.fn()} 
        footer={<button>Footer Action</button>}
      >
        Content
      </RightRailPanel>
    );
    expect(screen.getByText('Footer Action')).toBeInTheDocument();
  });

  it('shows loading skeleton when isLoading is true', () => {
    render(
      <RightRailPanel 
        title="Panel" 
        onClose={vi.fn()} 
        isLoading
      >
        Content
      </RightRailPanel>
    );
    // Content should not be visible when loading
    expect(screen.queryByText('Content')).not.toBeInTheDocument();
  });

  it('shows content when isLoading is false', () => {
    render(
      <RightRailPanel 
        title="Panel" 
        onClose={vi.fn()} 
        isLoading={false}
      >
        Content
      </RightRailPanel>
    );
    expect(screen.getByText('Content')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <RightRailPanel 
        title="Panel" 
        onClose={vi.fn()} 
        className="custom-class"
      >
        Content
      </RightRailPanel>
    );
    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('has correct structure with header, content, and footer', () => {
    render(
      <RightRailPanel 
        title="Panel" 
        onClose={vi.fn()} 
        footer={<span>Footer</span>}
      >
        <span>Content</span>
      </RightRailPanel>
    );
    
    expect(screen.getByText('Panel')).toBeInTheDocument();
    expect(screen.getByText('Content')).toBeInTheDocument();
    expect(screen.getByText('Footer')).toBeInTheDocument();
  });
});

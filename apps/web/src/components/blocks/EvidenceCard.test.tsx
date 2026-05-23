/**
 * EvidenceCard Component Tests
 *
 * Tests for the EvidenceCard component.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { EvidenceCard } from './EvidenceCard';

describe('EvidenceCard', () => {
  const defaultProps = {
    source: 'Annual Report 2024',
    claim: 'Revenue increased by 15% year-over-year',
    confidence: 0.92,
    validated: true,
    timestamp: '2024-01-15T10:30:00Z',
  };

  it('renders with source', () => {
    render(<EvidenceCard {...defaultProps} />);
    expect(screen.getByText('Annual Report 2024')).toBeInTheDocument();
  });

  it('renders with claim', () => {
    render(<EvidenceCard {...defaultProps} />);
    expect(screen.getByText('Revenue increased by 15% year-over-year')).toBeInTheDocument();
  });

  it('displays confidence percentage', () => {
    render(<EvidenceCard {...defaultProps} />);
    expect(screen.getByText('92%')).toBeInTheDocument();
  });

  it('clamps confidence to 100% when above 1', () => {
    render(<EvidenceCard {...defaultProps} confidence={1.5} />);
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('clamps confidence to 0% when below 0', () => {
    render(<EvidenceCard {...defaultProps} confidence={-0.5} />);
    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('displays formatted timestamp', () => {
    render(<EvidenceCard {...defaultProps} />);
    // formatDate should format the ISO timestamp
    expect(screen.getByText(/2024/)).toBeInTheDocument();
  });

  it('displays em dash when timestamp is empty', () => {
    render(<EvidenceCard {...defaultProps} timestamp="" />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<EvidenceCard {...defaultProps} onClick={handleClick} />);
    
    const card = screen.getByText('Revenue increased by 15% year-over-year');
    fireEvent.click(card);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('renders as button when onClick is provided', () => {
    render(<EvidenceCard {...defaultProps} onClick={vi.fn()} />);
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });

  it('renders as div when onClick is not provided', () => {
    render(<EvidenceCard {...defaultProps} />);
    const button = screen.queryByRole('button');
    expect(button).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <EvidenceCard {...defaultProps} className="custom-class" />
    );
    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('shows validated status when validated is true', () => {
    render(<EvidenceCard {...defaultProps} validated={true} />);
    // StatusBadge should show completed status
    expect(screen.getByText(/completed/i)).toBeInTheDocument();
  });

  it('shows processing status when validated is false', () => {
    render(<EvidenceCard {...defaultProps} validated={false} />);
    // StatusBadge should show processing status
    expect(screen.getByText(/processing/i)).toBeInTheDocument();
  });

  it('truncates long claim text with line-clamp', () => {
    const longClaim = 'This is a very long claim that should be truncated because it exceeds the line-clamp limit of two lines that is set in the component styles.';
    render(<EvidenceCard {...defaultProps} claim={longClaim} />);
    const claimElement = screen.getByText(longClaim);
    expect(claimElement).toHaveClass('line-clamp-2');
  });

  it('truncates long source text', () => {
    const longSource = 'Very Long Source Name That Should Be Truncated Because It Exceeds The Available Space In The Card Header';
    render(<EvidenceCard {...defaultProps} source={longSource} />);
    const sourceElement = screen.getByText(longSource);
    expect(sourceElement).toHaveClass('truncate');
  });
});

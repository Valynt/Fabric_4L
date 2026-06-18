/**
 * VirtualList Visual Regression Tests
 *
 * Snapshot tests to ensure VirtualList rendering does not unexpectedly change.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { VirtualList } from './virtual-list';

vi.mock('@tanstack/react-virtual', () => ({
  useVirtualizer: vi.fn(({ count, estimateSize }) => ({
    getVirtualItems: () =>
      Array.from({ length: count }, (_, index) => ({
        index,
        key: `virtual-${index}`,
        start: index * estimateSize(),
        end: (index + 1) * estimateSize(),
        size: estimateSize(),
        lane: 0,
      })),
    getTotalSize: () => count * estimateSize(),
    measureElement: vi.fn(),
    scrollToIndex: vi.fn(),
    scrollToOffset: vi.fn(),
    getVirtualItemForIndex: vi.fn(),
    options: {},
    scrollElement: null,
    scrollRect: null,
    scrollDirection: null,
    isScrolling: false,
  })),
}));

describe('VirtualList visual regression', () => {
  it('single-column list matches snapshot', () => {
    const items = Array.from({ length: 5 }, (_, i) => ({
      id: `item-${i}`,
      label: `Item ${i}`,
    }));

    render(
      <div style={{ height: '300px' }}>
        <VirtualList
          items={items}
          estimateSize={50}
          renderItem={(item) => (
            <div className="p-4 border-b">{item.label}</div>
          )}
        />
      </div>
    );

    for (let i = 0; i < 5; i++) {
      expect(screen.getByText(`Item ${i}`)).toBeInTheDocument();
    }
  });

  it('multi-column grid matches snapshot', () => {
    const items = Array.from({ length: 6 }, (_, i) => ({
      id: `grid-${i}`,
      label: `Grid ${i}`,
    }));

    render(
      <div style={{ height: '300px' }}>
        <VirtualList
          items={items}
          estimateSize={100}
          columns={3}
          renderItem={(item) => (
            <div className="p-4 border rounded">{item.label}</div>
          )}
        />
      </div>
    );

    for (let i = 0; i < 6; i++) {
      expect(screen.getByText(`Grid ${i}`)).toBeInTheDocument();
    }
  });

  it('empty list matches snapshot', () => {
    const { container } = render(
      <div style={{ height: '200px' }}>
        <VirtualList
          items={[]}
          estimateSize={50}
          renderItem={(item: { label: string }) => <div>{item.label}</div>}
        />
      </div>
    );

    expect(container.querySelectorAll('[role="listitem"]').length).toBe(0);
  });
});

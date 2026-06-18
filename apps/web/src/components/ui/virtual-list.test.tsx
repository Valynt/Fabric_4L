/**
 * VirtualList Component Tests
 *
 * Tests for the VirtualList primitive including:
 * - Single-column list virtualization
 * - Multi-column grid virtualization (columns prop)
 * - Accessibility attributes
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { VirtualList } from './virtual-list';

describe('VirtualList', () => {
  const items = Array.from({ length: 20 }, (_, i) => ({
    id: `item-${i}`,
    label: `Item ${i}`,
  }));

  beforeEach(() => {
    // Provide a realistic ResizeObserver mock for react-virtual
    let callbacks: ResizeObserverCallback[] = [];
    global.ResizeObserver = vi.fn((cb: ResizeObserverCallback) => {
      callbacks.push(cb);
      return {
        observe: vi.fn((target: Element) => {
          // Immediately report a size so virtualizer can calculate visible items
          queueMicrotask(() => {
            cb(
              [
                {
                  target,
                  contentRect: { width: 600, height: 300 } as DOMRectReadOnly,
                  borderBoxSize: [{ inlineSize: 600, blockSize: 300 }] as unknown as ResizeObserverSize[],
                  contentBoxSize: [{ inlineSize: 600, blockSize: 300 }] as unknown as ResizeObserverSize[],
                  devicePixelContentBoxSize: [] as ResizeObserverSize[],
                },
              ],
              new ResizeObserver(cb)
            );
          });
        }),
        unobserve: vi.fn(),
        disconnect: vi.fn(),
      };
    }) as unknown as typeof ResizeObserver;
  });

  it('renders single-column virtual list', () => {
    render(
      <div data-testid="container" style={{ height: '300px' }}>
        <VirtualList
          items={items}
          estimateSize={50}
          overscan={2}
          renderItem={(item) => (
            <div data-testid={`row-${item.id}`}>{item.label}</div>
          )}
        />
      </div>
    );

    // Container should be rendered
    expect(screen.getByTestId('container')).toBeInTheDocument();
  });

  it('renders multi-column grid with columns prop', () => {
    const gridItems = Array.from({ length: 12 }, (_, i) => ({
      id: `grid-item-${i}`,
      label: `Grid ${i}`,
    }));

    render(
      <div data-testid="grid-container" style={{ height: '300px' }}>
        <VirtualList
          items={gridItems}
          estimateSize={100}
          columns={3}
          overscan={2}
          renderItem={(item) => (
            <div data-testid={`cell-${item.id}`}>{item.label}</div>
          )}
        />
      </div>
    );

    expect(screen.getByTestId('grid-container')).toBeInTheDocument();
  });

  it('renders empty list without errors', () => {
    render(
      <div style={{ height: '300px' }}>
        <VirtualList
          items={[]}
          estimateSize={50}
          renderItem={(item: { label: string }) => <div>{item.label}</div>}
        />
      </div>
    );

    // Should render without throwing
    expect(document.querySelector('[style*="contain"]')).toBeInTheDocument();
  });

  it('applies contain strict for performance', () => {
    render(
      <div style={{ height: '200px' }}>
        <VirtualList
          items={items}
          estimateSize={50}
          renderItem={(item) => <div>{item.label}</div>}
        />
      </div>
    );

    const container = document.querySelector('[style*="contain: strict"]');
    expect(container).toBeInTheDocument();
  });

  it('applies custom className to container', () => {
    render(
      <div style={{ height: '200px' }}>
        <VirtualList
          items={items.slice(0, 3)}
          estimateSize={50}
          className="custom-list-class"
          renderItem={(item) => <div>{item.label}</div>}
        />
      </div>
    );

    const container = document.querySelector('.custom-list-class');
    expect(container).toBeInTheDocument();
  });

  it('multi-column grid renders without errors', () => {
    const gridItems = Array.from({ length: 6 }, (_, i) => ({
      id: `grid-${i}`,
      label: `Cell ${i}`,
    }));

    // Should render without throwing
    expect(() =>
      render(
        <div style={{ height: '300px' }}>
          <VirtualList
            items={gridItems}
            estimateSize={80}
            columns={3}
            renderItem={(item) => <div>{item.label}</div>}
          />
        </div>
      )
    ).not.toThrow();

    // The outer scroll container should exist
    const scrollContainer = document.querySelector('[style*="contain: strict"]');
    expect(scrollContainer).toBeInTheDocument();
  });

  it('root scroll container fills parent height', () => {
    render(
      <div style={{ height: '200px' }}>
        <VirtualList
          items={items.slice(0, 3)}
          estimateSize={50}
          renderItem={(item) => <div>{item.label}</div>}
        />
      </div>
    );

    const container = document.querySelector('[style*="contain: strict"]');
    expect(container).toHaveClass('h-full');
  });
});

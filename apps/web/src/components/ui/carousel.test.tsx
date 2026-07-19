/**
 * Carousel Primitive Tests
 *
 * Behavior tests for the shadcn/ui carousel primitive:
 * - Embla event subscriptions created in useEffect are fully cleaned up
 *   on unmount (both "select" and "reInit" listeners are removed).
 */
import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import type { CarouselApi } from './carousel';

const apiMock = {
  on: vi.fn(),
  off: vi.fn(),
  canScrollPrev: vi.fn(() => false),
  canScrollNext: vi.fn(() => false),
};

vi.mock('embla-carousel-react', () => ({
  default: vi.fn(() => [vi.fn(), apiMock]),
}));

import { Carousel } from './carousel';

describe('Carousel', () => {
  it('subscribes to embla select and reInit events on mount', () => {
    apiMock.on.mockClear();

    render(
      <Carousel>
        <div>slide</div>
      </Carousel>
    );

    const subscribedEvents = apiMock.on.mock.calls.map(([event]) => event);
    expect(subscribedEvents).toContain('select');
    expect(subscribedEvents).toContain('reInit');
  });

  it('removes every embla subscription on unmount', () => {
    apiMock.on.mockClear();
    apiMock.off.mockClear();

    const { unmount } = render(
      <Carousel>
        <div>slide</div>
      </Carousel>
    );

    const subscriptions = new Map(
      apiMock.on.mock.calls.map(([event, handler]) => [event, handler])
    );

    unmount();

    const removals = new Map(
      apiMock.off.mock.calls.map(([event, handler]) => [event, handler])
    );
    for (const [event, handler] of subscriptions) {
      expect(removals.get(event)).toBe(handler);
    }
  });

  it('forwards the embla api through setApi', () => {
    const setApi = vi.fn();

    render(
      <Carousel setApi={setApi}>
        <div>slide</div>
      </Carousel>
    );

    expect(setApi).toHaveBeenCalledWith(apiMock as unknown as CarouselApi);
  });
});

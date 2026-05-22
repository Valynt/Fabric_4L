/**
 * Vitest test setup file.
 * Configures testing environment with MSW, cleanup, and global utilities.
 */

import '@testing-library/jest-dom/vitest';
import { toHaveNoViolations } from 'jest-axe';
import { server } from '../src/test/mocks/server';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach, vi } from 'vitest';

expect.extend(toHaveNoViolations);

// Start MSW server before all tests
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});

// Reset handlers and cleanup after each test
afterEach(() => {
  server.resetHandlers();
  cleanup();
});

// Close MSW server after all tests
afterAll(() => {
  server.close();
});

// Radix UI uses pointer capture, scroll, and PointerEvent APIs that jsdom
// does not fully implement.  Polyfill them so Radix Select, DropdownMenu,
// and Dialog components work in tests.
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
}
if (!Element.prototype.setPointerCapture) {
  Element.prototype.setPointerCapture = () => undefined;
}
if (!Element.prototype.releasePointerCapture) {
  Element.prototype.releasePointerCapture = () => undefined;
}
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => undefined;
}
// Radix DropdownMenu uses PointerEvent to detect open/close.
if (typeof window !== 'undefined' && !window.PointerEvent) {
  (window as Window & typeof globalThis & { PointerEvent: typeof MouseEvent }).PointerEvent = class PointerEvent extends MouseEvent {
    constructor(type: string, params: PointerEventInit = {}) {
      super(type, params);
    }
  };
}

// Mock matchMedia for responsive component tests
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
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

// Mock IntersectionObserver
const mockIntersectionObserver = vi.fn();
mockIntersectionObserver.mockReturnValue({
  observe: () => null,
  unobserve: () => null,
  disconnect: () => null,
});
window.IntersectionObserver = mockIntersectionObserver;

// Mock ResizeObserver with realistic callback behavior for virtual list tests
const mockResizeObserver = vi.fn((callback: ResizeObserverCallback) => {
  return {
    observe: (target: Element) => {
      // Report a realistic size so virtualizers can calculate visible items
      queueMicrotask(() => {
        callback(
          [
            {
              target,
              contentRect: { width: 800, height: 600 } as DOMRectReadOnly,
              borderBoxSize: [{ inlineSize: 800, blockSize: 600 }] as unknown as ResizeObserverSize[],
              contentBoxSize: [{ inlineSize: 800, blockSize: 600 }] as unknown as ResizeObserverSize[],
              devicePixelContentBoxSize: [] as ResizeObserverSize[],
            },
          ],
          new ResizeObserver(callback)
        );
      });
    },
    unobserve: () => null,
    disconnect: () => null,
  };
});
window.ResizeObserver = mockResizeObserver as unknown as typeof ResizeObserver;

// Suppress console errors/warnings in tests (optional - remove if you want to see them)
// vi.spyOn(console, 'error').mockImplementation(() => {});
// vi.spyOn(console, 'warn').mockImplementation(() => {});

// Deterministic EventSource mock for SSE hook tests.
class MockEventSource {
  static instances: MockEventSource[] = [];

  readonly url: string;
  readonly withCredentials = false;
  readyState = 1;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  close(): void {
    this.readyState = 2;
  }

  addEventListener(): void {
    // The application assigns onmessage/onerror directly; addEventListener is present for API compatibility.
  }

  removeEventListener(): void {
    // No-op API compatibility shim.
  }

  dispatchEvent(): boolean {
    return true;
  }

  _emitMessage(payload: unknown): void {
    this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent);
  }

  _simulateProgress(progress: number): void {
    this._emitMessage({ type: 'progress', data: progress });
  }

  _emitError(): void {
    this.onerror?.(new Event('error'));
  }
}

export function getLastEventSource(): MockEventSource | undefined {
  return MockEventSource.instances.at(-1);
}

Object.defineProperty(globalThis, 'EventSource', {
  configurable: true,
  writable: true,
  value: MockEventSource,
});
Object.defineProperty(window, 'EventSource', {
  configurable: true,
  writable: true,
  value: MockEventSource,
});

beforeEach(() => {
  MockEventSource.instances = [];
});

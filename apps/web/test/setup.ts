/**
 * Vitest test setup file.
 * Configures testing environment with MSW, cleanup, and global utilities.
 */

import '@testing-library/jest-dom/vitest';
import { toHaveNoViolations } from 'jest-axe';
import { server } from '../src/test/mocks/server';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach, vi } from 'vitest';

// Type declaration for import.meta.env in tests
declare global {
  interface ImportMetaEnv {
    VITE_AUTH_PROVIDER?: string;
    [key: string]: string | undefined;
  }
  interface ImportMeta {
    env: ImportMetaEnv;
  }
}

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
  const MockPointerEvent = class extends MouseEvent implements PointerEvent {
    altitudeAngle = 0;
    azimuthAngle = 0;
    height = 1;
    isPrimary = false;
    pointerId = 0;
    pointerType = 'mouse';
    pressure = 0;
    tangentialPressure = 0;
    tiltX = 0;
    tiltY = 0;
    twist = 0;
    width = 1;

    constructor(type: string, params: PointerEventInit = {}) {
      super(type, params);
      Object.assign(this, params);
    }

    getCoalescedEvents(): PointerEvent[] {
      return [this];
    }

    getPredictedEvents(): PointerEvent[] {
      return [];
    }
  };
  (window as any).PointerEvent = MockPointerEvent as any;
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

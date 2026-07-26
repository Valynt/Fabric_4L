/**
 * useAccessibility — Apple-Level A11y Hooks
 *
 * Provides accessibility utilities following WCAG 2.1 AA standards.
 */

import { useEffect, useCallback, useState, useRef } from 'react';

/**
 * Detect if user prefers reduced motion
 * Respects system preferences for animations
 */
export function usePrefersReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);

    const handler = (event: MediaQueryListEvent) => {
      setPrefersReducedMotion(event.matches);
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return prefersReducedMotion;
}

/**
 * Detect high contrast mode
 */
export function usePrefersHighContrast(): boolean {
  const [prefersHighContrast, setPrefersHighContrast] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-contrast: high)');
    setPrefersHighContrast(mediaQuery.matches);

    const handler = (event: MediaQueryListEvent) => {
      setPrefersHighContrast(event.matches);
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return prefersHighContrast;
}

/**
 * Focus management hook for modals and dialogs
 * Traps focus within a container
 */
export function useFocusTrap(
  containerRef: React.RefObject<HTMLElement | null>,
  isActive: boolean
): void {
  useEffect(() => {
    if (!isActive || !containerRef.current) return;

    const container = containerRef.current;
    const focusableElements = container.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          lastElement?.focus();
          e.preventDefault();
        }
      } else {
        if (document.activeElement === lastElement) {
          firstElement?.focus();
          e.preventDefault();
        }
      }
    };

    // Focus first element when activated
    firstElement?.focus();

    container.addEventListener('keydown', handleKeyDown);
    return () => container.removeEventListener('keydown', handleKeyDown);
  }, [isActive, containerRef]);
}

/**
 * Announce messages to screen readers
 * Creates aria-live region if it doesn't exist (self-initializing)
 */
export function useAnnouncer(): (message: string, priority?: 'polite' | 'assertive') => void {
  // Ensure aria-live regions exist in DOM
  useEffect(() => {
    const createAriaLive = (id: string, priority: 'polite' | 'assertive') => {
      if (!document.getElementById(id)) {
        const el = document.createElement('div');
        el.id = id;
        el.setAttribute('aria-live', priority);
        el.setAttribute('aria-atomic', 'true');
        el.className = 'sr-only';
        document.body.appendChild(el);
      }
    };
    createAriaLive('aria-live-polite', 'polite');
    createAriaLive('aria-live-assertive', 'assertive');
  }, []);

  const announce = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    const ariaLive = document.getElementById(`aria-live-${priority}`);
    if (ariaLive) {
      ariaLive.textContent = message;
      // Clear after announcement
      setTimeout(() => {
        ariaLive.textContent = '';
      }, 1000);
    }
  }, []);

  return announce;
}

/**
 * Keyboard navigation hook for lists
 * Handles arrow keys, home, end, enter
 */
export function useListKeyboardNavigation(
  itemCount: number,
  onSelect: (index: number) => void,
  onActivate?: (index: number) => void
): {
  selectedIndex: number;
  setSelectedIndex: (index: number) => void;
  handleKeyDown: (e: React.KeyboardEvent) => void;
} {
  const [selectedIndex, setSelectedIndex] = useState(0);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      // Guard against empty lists to prevent division by zero
      if (itemCount <= 0) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev) => (prev + 1) % itemCount);
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) => (prev - 1 + itemCount) % itemCount);
          break;
        case 'Home':
          e.preventDefault();
          setSelectedIndex(0);
          break;
        case 'End':
          e.preventDefault();
          setSelectedIndex(itemCount - 1);
          break;
        case 'Enter':
        case ' ':
          e.preventDefault();
          onActivate?.(selectedIndex);
          break;
      }
    },
    [itemCount, selectedIndex, onActivate]
  );

  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    onSelectRef.current(selectedIndex);
  }, [selectedIndex]);

  return { selectedIndex, setSelectedIndex, handleKeyDown };
}

/**
 * Skip link hook for keyboard navigation
 */
export function useSkipLink(targetId: string): {
  skipLinkProps: {
    href: string;
    onClick: (e: React.MouseEvent) => void;
    className: string;
  };
} {
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      const target = document.getElementById(targetId);
      if (target) {
        target.focus();
        target.scrollIntoView({ behavior: 'smooth' });
      }
    },
    [targetId]
  );

  return {
    skipLinkProps: {
      href: `#${targetId}`,
      onClick: handleClick,
      className:
        'sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-primary focus:text-primary-foreground focus:px-4 focus:py-2 focus:rounded',
    },
  };
}

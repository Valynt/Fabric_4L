# Responsive & Accessibility Hardening Checklist

Prototypes are rarely mobile-first or keyboard-first. This checklist retrofits
responsive and accessible behavior **without** breaking the desktop layout.
Work top-down: it's easier to preserve accessibility when you structure the
markup correctly the first time.

## Breakpoints & Responsive Layout
- [ ] Breakpoints defined as tokens/theme, not scattered magic numbers
- [ ] Core flows usable at 320px, 768px, 1280px (test against prototype at each)
- [ ] Grid/flex degenerate gracefully (no horizontal overflow at small widths)
- [ ] Touch targets ≥ 44×44px on interactive elements
- [ ] No frozen desktop-only widths hiding content on mobile
- [ ] Text scales without clipping (no fixed-height text containers)

## Keyboard Navigation
- [ ] Tab order follows visual/logical order
- [ ] All interactive elements reachable via keyboard (no mouse-only handlers on divs)
- [ ] Visible focus indicator on every focusable element
- [ ] Tab traps avoided: dialogs/side-panels trap focus while open, release on close
- [ ] Esc closes overlays/drawers/modals
- [ ] Skip-link present for main content navigation

## ARIA & Semantics
- [ ] Native semantic elements used where possible (`button`, `input`, `nav`, `main`)
- [ ] Non-obvious custom widgets given roles (`region`, `dialog`, `combobox`)
- [ ] Labels/aria-labels on all inputs and icon-only buttons
- [ ] `aria-live` regions for async updates (loading, streaming, status changes)
- [ ] `aria-expanded` / `aria-controls` on disclosure widgets
- [ ] No duplicate IDs; no empty `alt` on informative images

## Focus Management
- [ ] Focus moves into dialogs/drawers on open
- [ ] Focus returns to the trigger on close
- [ ] Route changes reset scroll/focus appropriately
- [ ] Programmatic focus used for meaningful transitions only (not every render)

## Motion & Contrast
- [ ] Respect `prefers-reduced-motion` (disable non-essential animation)
- [ ] Color contrast meets WCAG AA baseline
- [ ] No color-only status signaling (paired with icon/text)

## Verification
- [ ] Manual keyboard pass of the changed flow
- [ ] Covered by a11y test (repo: `pnpm --dir apps/web run test:a11y:*`)
- [ ] Responsive pass at breakpoints against prototype reference

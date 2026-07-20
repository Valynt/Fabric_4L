# UI Component Migration Checklist

> Canonical target: `frontend/client/src/components/ui`.

## Duplicate filename decisions

- [ ] `accordion.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/accordion.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/accordion.tsx`.
- [ ] `alert-dialog.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/alert-dialog.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/alert-dialog.tsx`.
- [ ] `alert.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/alert.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/alert.tsx`.
- [ ] `aspect-ratio.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/aspect-ratio.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/aspect-ratio.tsx`.
- [ ] `avatar.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/avatar.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/avatar.tsx`.
- [ ] `badge.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/badge.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/badge.tsx`.
- [ ] `breadcrumb.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/breadcrumb.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/breadcrumb.tsx`.
- [ ] `button-group.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/button-group.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/button-group.tsx`.
- [ ] `button.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/button.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/button.tsx`.
- [ ] `calendar.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/calendar.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/calendar.tsx`.
- [ ] `card.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/card.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/card.tsx`.
- [ ] `carousel.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/carousel.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/carousel.tsx`.
- [ ] `chart.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/chart.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/chart.tsx`.
- [ ] `checkbox.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/checkbox.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/checkbox.tsx`.
- [ ] `collapsible.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/collapsible.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/collapsible.tsx`.
- [ ] `command.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/command.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/command.tsx`.
- [ ] `context-menu.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/context-menu.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/context-menu.tsx`.
- [ ] `dialog.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/dialog.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/dialog.tsx`.
- [ ] `drawer.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/drawer.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/drawer.tsx`.
- [ ] `dropdown-menu.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/dropdown-menu.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/dropdown-menu.tsx`.
- [ ] `empty.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/empty.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/empty.tsx`.
- [ ] `field.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/field.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/field.tsx`.
- [ ] `form.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/form.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/form.tsx`.
- [ ] `hover-card.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/hover-card.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/hover-card.tsx`.
- [ ] `input-group.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/input-group.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/input-group.tsx`.
- [ ] `input-otp.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/input-otp.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/input-otp.tsx`.
- [ ] `input.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/input.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/input.tsx`.
- [ ] `item.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/item.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/item.tsx`.
- [ ] `kbd.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/kbd.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/kbd.tsx`.
- [ ] `label.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/label.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/label.tsx`.
- [ ] `menubar.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/menubar.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/menubar.tsx`.
- [ ] `navigation-menu.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/navigation-menu.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/navigation-menu.tsx`.
- [ ] `pagination.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/pagination.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/pagination.tsx`.
- [ ] `popover.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/popover.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/popover.tsx`.
- [ ] `progress.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/progress.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/progress.tsx`.
- [ ] `radio-group.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/radio-group.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/radio-group.tsx`.
- [ ] `resizable.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/resizable.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/resizable.tsx`.
- [ ] `scroll-area.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/scroll-area.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/scroll-area.tsx`.
- [ ] `select.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/select.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/select.tsx`.
- [ ] `separator.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/separator.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/separator.tsx`.
- [ ] `sheet.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/sheet.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/sheet.tsx`.
- [ ] `sidebar.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/sidebar.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/sidebar.tsx`.
- [ ] `skeleton.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/skeleton.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/skeleton.tsx`.
- [ ] `slider.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/slider.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/slider.tsx`.
- [ ] `sonner.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/sonner.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/sonner.tsx`.
- [ ] `spinner.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/spinner.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/spinner.tsx`.
- [ ] `switch.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/switch.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/switch.tsx`.
- [ ] `table.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/table.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/table.tsx`.
- [ ] `tabs.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/tabs.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/tabs.tsx`.
- [ ] `textarea.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/textarea.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/textarea.tsx`.
- [ ] `toggle-group.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/toggle-group.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/toggle-group.tsx`.
- [ ] `toggle.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/toggle.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/toggle.tsx`.
- [ ] `tooltip.tsx` — **Migrate** (production source of truth: `frontend/client/src/components/ui/tooltip.tsx`); **Archive** prototype copy in `_ui-prototype/non-production/ui-components-archive/tooltip.tsx`.

## Legacy prototype tree decision

- [x] `_ui-prototype/app-value-old/src/components/ui` — **Delete** (path does not exist in repository).
- [x] `_ui-prototype/app-value-old` — **Archive** moved to `_ui-prototype/non-production/app-value-old-archive`.

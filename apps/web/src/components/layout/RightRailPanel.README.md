# RightRailPanel Component

Consistent right sidebar panel for detail views in the Value Fabric application.

## Purpose

Provides a standardized pattern for right-rail detail panels across the application, ensuring consistent layout, responsive behavior, and accessibility.

## Features

- **Sticky positioning** on desktop (md:sticky md:top-8)
- **Full height** with scrollable content
- **Header** with title, optional status badge, and close button
- **Action footer** when provided
- **Loading state** with skeleton matching content structure
- **Responsive behavior** - designed for desktop with parent handling mobile/tablet

## Usage

```tsx
import { RightRailPanel } from "@/components";

function MyPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  
  return (
    <div className="grid grid-cols-12 gap-6">
      {/* Main content */}
      <div className="col-span-12 md:col-span-9">
        {/* Primary content */}
      </div>
      
      {/* Right rail */}
      {selectedId && (
        <div className="col-span-12 md:col-span-3">
          <RightRailPanel
            title="Item Details"
            status={<StatusBadge status="completed" />}
            onClose={() => setSelectedId(null)}
            footer={<ActionButtons />}
            isLoading={isLoading}
          >
            <DetailContent />
          </RightRailPanel>
        </div>
      )}
    </div>
  );
}
```

## Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `title` | `string` | Yes | Panel title displayed in header |
| `onClose` | `() => void` | Yes | Callback when close button clicked |
| `status` | `ReactNode` | No | Optional status badge or indicator |
| `children` | `ReactNode` | Yes | Panel content |
| `footer` | `ReactNode` | No | Optional action footer |
| `isLoading` | `boolean` | No | Show loading skeleton state |
| `className` | `string` | No | Additional CSS classes |

## Responsive Behavior

- **Desktop**: Fixed width panel with sticky positioning
- **Tablet/Mobile**: Should be wrapped in Sheet/Drawer by parent component
- Parent components should handle mobile collapse behavior

## Accessibility

- Close button has `aria-label="Close panel"`
- Focus management handled by parent
- Keyboard navigation supported through standard button elements

## Examples

### Basic Usage

```tsx
<RightRailPanel
  title="Account Details"
  onClose={() => setShowPanel(false)}
>
  <p>Account information here</p>
</RightRailPanel>
```

### With Status and Footer

```tsx
<RightRailPanel
  title="Account Details"
  status={<StatusBadge status="completed" />}
  onClose={() => setShowPanel(false)}
  footer={
    <div className="flex gap-2">
      <Button>Save</Button>
      <Button variant="outline">Cancel</Button>
    </div>
  }
>
  <AccountDetails />
</RightRailPanel>
```

### With Loading State

```tsx
<RightRailPanel
  title="Account Details"
  onClose={() => setShowPanel(false)}
  isLoading={isLoading}
>
  <AccountDetails />
</RightRailPanel>
```

## Design System Alignment

- Uses design system spacing tokens
- Follows color scheme (bg-card, border-border)
- Consistent with SectionCard patterns
- Matches PageShell layout conventions

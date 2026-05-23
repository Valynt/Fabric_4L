# HorizontalTabWrapper Component

Tab navigation with URL state management for the Value Fabric application.

## Purpose

Provides a standardized pattern for horizontal tab navigation with URL-based state persistence, ensuring consistent tab behavior across workspaces and multi-view pages.

## Features

- **URL state management** - tab selection persisted in search params (e.g., ?tab=signals)
- **Deep linking** - specific tabs can be shared via URL
- **Tab persistence** - tab selection survives navigation
- **Horizontal orientation** - uses TabNav in horizontal mode
- **Fade-in animation** - smooth transition when switching tabs
- **Type-safe** - TypeScript interfaces for tab configuration

## Usage

```tsx
import { HorizontalTabWrapper } from "@/components/blocks";

function IntelligenceWorkspace() {
  return (
    <HorizontalTabWrapper
      tabs={[
        {
          id: 'signals',
          label: 'Signals',
          content: <SignalsContent />
        },
        {
          id: 'evidence',
          label: 'Evidence',
          content: <EvidenceContent />
        },
        {
          id: 'stakeholders',
          label: 'Stakeholders',
          content: <StakeholdersContent />
        }
      ]}
      defaultTab="signals"
    />
  );
}
```

## Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `tabs` | `TabConfig[]` | Yes | Array of tab configurations with id, label, and content |
| `defaultTab` | `string` | No | Default tab id if none in URL (defaults to first tab) |
| `className` | `string` | No | Additional CSS classes |

## TabConfig Interface

```tsx
interface TabConfig {
  id: string;           // Unique tab identifier (used in URL)
  label: string;        // Display label for the tab
  content: ReactNode;   // Content to render when tab is active
}
```

## URL Behavior

- Tab selection stored in URL search parameter: `?tab={tabId}`
- When no tab in URL, uses `defaultTab` or first tab
- Changing tab updates URL without page reload
- Back/forward browser navigation works correctly
- Deep linking to specific tabs supported

## Examples

### Basic Workspace Navigation

```tsx
<HorizontalTabWrapper
  tabs={[
    { id: 'signals', label: 'Signals', content: <SignalsTab /> },
    { id: 'evidence', label: 'Evidence', content: <EvidenceTab /> },
    { id: 'stakeholders', label: 'Stakeholders', content: <StakeholdersTab /> },
    { id: 'drivers', label: 'Value Drivers', content: <DriversTab /> }
  ]}
  defaultTab="signals"
/>
```

### Business Case Views

```tsx
<HorizontalTabWrapper
  tabs={[
    { id: 'summary', label: 'Summary', content: <SummaryView /> },
    { id: 'claims', label: 'Claims', content: <ClaimsView /> },
    { id: 'validation', label: 'Validation', content: <ValidationView /> },
    { id: 'settings', label: 'Settings', content: <SettingsView /> }
  ]}
/>
```

### With Custom Styling

```tsx
<HorizontalTabWrapper
  tabs={tabs}
  defaultTab="overview"
  className="mt-6"
/>
```

## Design System Alignment

- Uses `TabNav` component in horizontal orientation
- Follows design system spacing tokens
- Matches color scheme (bg-primary/10 for active tab)
- Consistent with PageShell layout conventions
- Fade-in animation for smooth transitions

## Use Cases

### Intelligence Workspace

```tsx
// URL: /intelligence?tab=signals
<HorizontalTabWrapper
  tabs={[
    { id: 'signals', label: 'Signals', content: <SignalsTab /> },
    { id: 'evidence', label: 'Evidence', content: <EvidenceTab /> },
    { id: 'stakeholders', label: 'Stakeholders', content: <StakeholdersTab /> },
    { id: 'drivers', label: 'Value Drivers', content: <DriversTab /> }
  ]}
/>
```

### Value Modeling Workspace

```tsx
// URL: /modeling?tab=formulas
<HorizontalTabWrapper
  tabs={[
    { id: 'formulas', label: 'Formulas', content: <FormulasTab /> },
    { id: 'benchmarks', label: 'Benchmarks', content: <BenchmarksTab /> },
    { id: 'assumptions', label: 'Assumptions', content: <AssumptionsTab /> }
  ]}
/>
```

### Business Case Viewer

```tsx
// URL: /business-case/123?tab=validation
<HorizontalTabWrapper
  tabs={[
    { id: 'summary', label: 'Summary', content: <SummaryView /> },
    { id: 'claims', label: 'Claims', content: <ClaimsView /> },
    { id: 'validation', label: 'Validation', content: <ValidationView /> }
  ]}
/>
```

## Accessibility

- Tabs use `role="tab"` and `aria-selected` (from TabNav)
- Keyboard navigation supported (TabNav handles this)
- Focus management handled by TabNav
- URL state provides clear navigation history

## Migration from Manual Tab State

**Before:**
```tsx
const [activeTab, setActiveTab] = useState('signals');
// Manual state management, no URL persistence
```

**After:**
```tsx
<HorizontalTabWrapper
  tabs={tabs}
  defaultTab="signals"
/>
// Automatic URL state management
```

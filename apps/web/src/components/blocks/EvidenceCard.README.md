# EvidenceCard Component

Consistent card for displaying evidence with provenance information in the Value Fabric application.

## Purpose

Provides a standardized pattern for displaying evidence items with source attribution, confidence scores, validation status, and timestamps. Used in intelligence workspaces, business case traceability, and provenance panels.

## Features

- **Source attribution** with truncation for long sources
- **Confidence score** display (0-100%)
- **Validation status** badge (validated/pending)
- **Timestamp** formatting
- **Clickable** for drill-down to evidence details
- **Truncated claim text** (line-clamp-2)
- **Hover state** when clickable

## Usage

```tsx
import { EvidenceCard } from "@/components/blocks";

function EvidenceList() {
  return (
    <div className="space-y-3">
      <EvidenceCard
        source="Annual Report 2024"
        claim="Revenue increased by 15% year-over-year"
        confidence={0.92}
        validated={true}
        timestamp="2024-01-15T10:30:00Z"
        onClick={() => handleEvidenceClick(id)}
      />
    </div>
  );
}
```

## Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `source` | `string` | Yes | Source attribution (document, URL, or system) |
| `claim` | `string` | Yes | The claim or evidence text |
| `confidence` | `number` | Yes | Confidence score (0-1) |
| `validated` | `boolean` | Yes | Whether the evidence has been validated |
| `timestamp` | `string` | Yes | When the evidence was extracted/created (ISO string) |
| `onClick` | `() => void` | No | Optional click handler for drill-down |
| `className` | `string` | No | Additional CSS classes |

## Design System Alignment

- Uses `SectionCard` for consistent card styling
- Uses `StatusBadge` for validation status
- Uses design system spacing and typography tokens
- Matches color scheme (hover:border-primary/50)
- Follows evidence display guidelines from UX plan

## Use Cases

### Evidence Lists in Intelligence Workspace

```tsx
<EvidenceCard
  source="CRM Opportunity Data"
  claim="Deal value estimated at $500,000"
  confidence={0.85}
  validated={false}
  timestamp="2024-01-15T10:30:00Z"
  onClick={() => navigateToEvidenceDetail(id)}
/>
```

### Claim Traceability in Business Cases

```tsx
<EvidenceCard
  source="Industry Benchmark Report"
  claim="Average deal size in financial services is $450,000"
  confidence={0.95}
  validated={true}
  timestamp="2024-01-10T14:20:00Z"
/>
```

### Provenance Panels in Right Rail

```tsx
<EvidenceCard
  source="Internal Analysis"
  claim="Customer has 3 active opportunities in pipeline"
  confidence={0.88}
  validated={true}
  timestamp="2024-01-12T09:15:00Z"
  onClick={() => showProvenanceDetails(id)}
/>
```

## Accessibility

- Clickable cards wrapped in `<button>` with `type="button"`
- Hover state provides visual feedback
- Truncated text has `title` attribute for full content
- Keyboard navigable when clickable

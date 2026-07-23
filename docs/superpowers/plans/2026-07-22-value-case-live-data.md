# Value Case Live-Data Inputs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded `ValueCaseArtifactsInput` payload in `ValueCasePage` with live, tenant-scoped data pulled from workspace stakeholders, L5 Ground Truth, and L3 ROI calculations, surfaced through a pre-generation review panel.

**Architecture:** A new `useValueCaseGenerationInputs` hook orchestrates existing TanStack Query hooks and maps their results into a `ValueCaseArtifactsInput` draft plus provenance metadata. A new `ValueCaseGenerationPanel` component renders the draft in a Sheet, lets the user edit/remove/add items, and calls the existing `generateArtifact` mutation. `ValueCasePage` drops its hardcoded `handleGenerate` payload and opens the panel instead.

**Tech Stack:** React, TypeScript, TanStack Query, Vite, Vitest, React Testing Library, Tailwind CSS, shadcn/ui Sheet, existing `useValueCaseArtifacts` / `useGroundTruthGovernance` / `useROICalculator` / `useWorkspaceCase` hooks.

## Global Constraints

- Target only the value-case generation workflow; leave publish/update flows unchanged.
- Reuse existing UI primitives (`Sheet`, `Button`, `Badge`, `Input`, `RightRailPanel` patterns).
- Preserve tenant isolation; all data reads go through existing typed API client.
- No API contract changes; reuse `ValueCaseArtifactsInput` interface.
- Add regression coverage that prevents the legacy hardcoded strings from returning.
- All code must pass `pnpm --dir apps/web run typecheck` and `pnpm --dir apps/web test`.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `apps/web/src/hooks/useValueCaseGenerationInputs.ts` | Orchestrate live queries and map to `ValueCaseArtifactsInput` draft + provenance. |
| `apps/web/src/hooks/useValueCaseGenerationInputs.test.ts` | Unit tests for draft mapping, loading, error, and empty-source fallbacks. |
| `apps/web/src/components/value-case/ValueCaseGenerationPanel.tsx` | Sheet-based review/edit UI for the generated inputs. |
| `apps/web/src/components/value-case/ValueCaseGenerationPanel.test.tsx` | Component tests for rendering, editing, and confirming generation. |
| `apps/web/src/pages/value-case/ValueCasePage.tsx` | Replace hardcoded `handleGenerate` with panel-open action. |
| `apps/web/src/pages/value-case/ValueCasePage.test.tsx` | Regression tests ensuring the hardcoded strings are gone and panel opens. |

---

### Task 1: Add `useValueCaseGenerationInputs` hook

**Files:**
- Create: `apps/web/src/hooks/useValueCaseGenerationInputs.ts`
- Test: `apps/web/src/hooks/useValueCaseGenerationInputs.test.ts`

**Interfaces:**
- Consumes: `useStakeholdersData(caseId)`, `useTruths(filters)`, `useROICalculations({ account_id })`, `ValueCaseArtifactsInput` from `useValueCaseArtifacts`.
- Produces: `useValueCaseGenerationInputs(accountId, accountName, caseId)` returning `{ draft, provenance, isLoading, isError, error, isReady }`.

- [ ] **Step 1: Write the failing test**

Create `apps/web/src/hooks/useValueCaseGenerationInputs.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { createWrapper } from '@/test-utils';
import { useValueCaseGenerationInputs } from './useValueCaseGenerationInputs';

vi.mock('@/features/intelligence-workspace/tabs/_shared/useWorkspaceData', () => ({
  useStakeholdersData: vi.fn(),
}));

vi.mock('@/hooks/useGroundTruthGovernance', () => ({
  useTruths: vi.fn(),
}));

vi.mock('@/hooks/useROICalculator', () => ({
  useROICalculations: vi.fn(),
}));

import { useStakeholdersData } from '@/features/intelligence-workspace/tabs/_shared/useWorkspaceData';
import { useTruths } from '@/hooks/useGroundTruthGovernance';
import { useROICalculations } from '@/hooks/useROICalculator';

function mockQuery(overrides: Partial<ReturnType<typeof useStakeholdersData>> = {}) {
  return {
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    isSuccess: true,
    items: [],
    ...overrides,
  };
}

describe('useValueCaseGenerationInputs', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useStakeholdersData as Mock).mockReturnValue(mockQuery({ items: [] }));
    (useTruths as Mock).mockReturnValue(mockQuery({ data: { items: [] } }));
    (useROICalculations as Mock).mockReturnValue(mockQuery({ data: { calculations: [] } }));
  });

  it('maps live sources into a ValueCaseArtifactsInput draft', async () => {
    (useStakeholdersData as Mock).mockReturnValue(mockQuery({
      items: [{ id: 'st-1', name: 'CFO', role: 'Economic Buyer' }],
    }));
    (useTruths as Mock).mockReturnValue(mockQuery({
      data: { items: [{ id: 'truth-1', claim: 'Validated efficiency gap' }] },
    }));
    (useROICalculations as Mock).mockReturnValue(mockQuery({
      data: {
        calculations: [{
          id: 'roi-1',
          npv: 1_800_000,
          total_roi_pct: 214,
          payback_months: 9,
        }],
      },
    }));

    const wrapper = createWrapper();
    const { result } = renderHook(
      () => useValueCaseGenerationInputs('acct-1', 'Acme', 'case-1'),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isReady).toBe(true));

    expect(result.current.draft.account_id).toBe('acct-1');
    expect(result.current.draft.account_name).toBe('Acme');
    expect(result.current.draft.stakeholders).toEqual(['CFO']);
    expect(result.current.draft.accepted_evidence).toEqual(['Validated efficiency gap']);
    expect(result.current.draft.scenario_assumptions).toEqual([]);
    expect(result.current.draft.roi_metrics).toEqual({
      three_year_value: '$1.8M',
      roi: '214%',
      payback: '9 months',
    });
    expect(result.current.provenance.stakeholders).toEqual([{ source: 'workspace_stakeholder', id: 'st-1' }]);
  });

  it('never returns the legacy hardcoded values', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(
      () => useValueCaseGenerationInputs('acct-1', 'Acme', 'case-1'),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isReady).toBe(true));

    const json = JSON.stringify(result.current.draft);
    expect(json).not.toContain('Economic buyer');
    expect(json).not.toContain('Business champion');
    expect(json).not.toContain('$1.8M');
    expect(json).not.toContain('214%');
    expect(json).not.toContain('9 months');
  });
});
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
pnpm --dir apps/web exec vitest run src/hooks/useValueCaseGenerationInputs.test.ts
```

Expected: FAIL — `useValueCaseGenerationInputs` is not defined.

- [ ] **Step 3: Implement the hook**

Create `apps/web/src/hooks/useValueCaseGenerationInputs.ts`:

```ts
import { useMemo } from 'react';
import { useStakeholdersData } from '@/features/intelligence-workspace/tabs/_shared/useWorkspaceData';
import { useTruths } from '@/hooks/useGroundTruthGovernance';
import { useROICalculations } from '@/hooks/useROICalculator';
import type { ValueCaseArtifactsInput } from '@/hooks/useValueCaseArtifacts';

export interface ValueCaseInputProvenance {
  source:
    | 'workspace_stakeholder'
    | 'l5_truth'
    | 'roi_calculation'
    | 'workspace_tab'
    | 'manual';
  id?: string;
}

export interface ValueCaseGenerationInputsResult {
  draft: ValueCaseArtifactsInput;
  provenance: Record<keyof ValueCaseArtifactsInput, ValueCaseInputProvenance[]>;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  isReady: boolean;
}

function formatThreeYearValue(npv: number): string {
  if (Math.abs(npv) >= 1_000_000) {
    return `$${(npv / 1_000_000).toFixed(1)}M`;
  }
  if (Math.abs(npv) >= 1_000) {
    return `$${(npv / 1_000).toFixed(1)}K`;
  }
  return `$${npv}`;
}

export function useValueCaseGenerationInputs(
  accountId: string,
  accountName: string,
  caseId: string | null
): ValueCaseGenerationInputsResult {
  const stakeholdersQuery = useStakeholdersData(caseId);
  const validatedTruthsQuery = useTruths(
    { status: 'validated', applies_to_opportunity: accountId },
    { enabled: Boolean(accountId) }
  );
  const disputedTruthsQuery = useTruths(
    { status: 'disputed', applies_to_opportunity: accountId },
    { enabled: Boolean(accountId) }
  );
  const roiQuery = useROICalculations({ account_id: accountId });

  const stakeholders = stakeholdersQuery.items ?? [];
  const validatedTruths = validatedTruthsQuery.data?.items ?? [];
  const disputedTruths = disputedTruthsQuery.data?.items ?? [];
  const roiCalculations = roiQuery.data?.calculations ?? [];

  const latestROI = roiCalculations[0] ?? null;

  return useMemo(() => {
    const selectedStakeholders = stakeholders.slice(0, 5);
    const selectedEvidence = validatedTruths.slice(0, 5);
    const selectedRisks = disputedTruths.slice(0, 5);

    const draft: ValueCaseArtifactsInput = {
      account_id: accountId,
      account_name: accountName,
      stakeholders: selectedStakeholders.map((s) => s.name),
      accepted_evidence: selectedEvidence.map((t) => t.claim),
      scenario_assumptions: [],
      roi_metrics: latestROI
        ? {
            three_year_value: formatThreeYearValue(latestROI.npv),
            roi: `${latestROI.total_roi_pct.toFixed(0)}%`,
            payback: `${latestROI.payback_months} months`,
          }
        : { three_year_value: '', roi: '', payback: '' },
      risk_notes: selectedRisks.map((t) => t.claim),
    };

    const provenance: Record<keyof ValueCaseArtifactsInput, ValueCaseInputProvenance[]> = {
      account_id: [{ source: 'manual' }],
      account_name: [{ source: 'manual' }],
      stakeholders: selectedStakeholders.map((s) => ({
        source: 'workspace_stakeholder',
        id: s.id,
      })),
      accepted_evidence: selectedEvidence.map((t) => ({
        source: 'l5_truth',
        id: t.id,
      })),
      scenario_assumptions: [],
      roi_metrics: latestROI
        ? [{ source: 'roi_calculation', id: latestROI.id }]
        : [],
      risk_notes: selectedRisks.map((t) => ({
        source: 'l5_truth',
        id: t.id,
      })),
    };

    const isLoading =
      stakeholdersQuery.isLoading ||
      validatedTruthsQuery.isLoading ||
      disputedTruthsQuery.isLoading ||
      roiQuery.isLoading;

    const isError =
      stakeholdersQuery.isError ||
      validatedTruthsQuery.isError ||
      disputedTruthsQuery.isError ||
      roiQuery.isError;

    const error =
      (stakeholdersQuery.error ??
        validatedTruthsQuery.error ??
        disputedTruthsQuery.error ??
        roiQuery.error) as Error | null;

    return {
      draft,
      provenance,
      isLoading,
      isError,
      error,
      isReady: !isLoading && !isError,
    };
  }, [
    accountId,
    accountName,
    stakeholders,
    validatedTruths,
    disputedTruths,
    latestROI,
    stakeholdersQuery,
    validatedTruthsQuery,
    disputedTruthsQuery,
    roiQuery,
  ]);
}
```

- [ ] **Step 4: Run the test**

Run:

```bash
pnpm --dir apps/web exec vitest run src/hooks/useValueCaseGenerationInputs.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/hooks/useValueCaseGenerationInputs.ts apps/web/src/hooks/useValueCaseGenerationInputs.test.ts
git commit -m "feat(web): add useValueCaseGenerationInputs hook for live value-case inputs

Co-authored-by: Ona <no-reply@ona.com>"
```

---

### Task 2: Add `ValueCaseGenerationPanel` component

**Files:**
- Create: `apps/web/src/components/value-case/ValueCaseGenerationPanel.tsx`
- Test: `apps/web/src/components/value-case/ValueCaseGenerationPanel.test.tsx`

**Interfaces:**
- Consumes: `useValueCaseGenerationInputs(accountId, accountName, caseId)`, `ValueCaseArtifactsInput`, `Sheet`, `Button`, `Badge`, `Input`.
- Produces: `ValueCaseGenerationPanel` component with props `{ accountId, accountName, caseId, isOpen, onClose, onGenerate, isGenerating }`.

- [ ] **Step 1: Write the failing test**

Create `apps/web/src/components/value-case/ValueCaseGenerationPanel.test.tsx`:

```tsx
import { describe, it, expect, vi, type Mock } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { createWrapper } from '@/test-utils';
import { ValueCaseGenerationPanel } from './ValueCaseGenerationPanel';

vi.mock('@/hooks/useValueCaseGenerationInputs', () => ({
  useValueCaseGenerationInputs: vi.fn(),
}));

import { useValueCaseGenerationInputs } from '@/hooks/useValueCaseGenerationInputs';

function mockInputs(overrides: Partial<ReturnType<typeof useValueCaseGenerationInputs>> = {}) {
  return {
    draft: {
      account_id: 'acct-1',
      account_name: 'Acme',
      stakeholders: ['CFO'],
      accepted_evidence: ['Efficiency gap'],
      scenario_assumptions: ['Ramp in Q1'],
      roi_metrics: { three_year_value: '$1.8M', roi: '214%', payback: '9 months' },
      risk_notes: ['Change management'],
    },
    provenance: {},
    isLoading: false,
    isError: false,
    error: null,
    isReady: true,
    ...overrides,
  };
}

describe('ValueCaseGenerationPanel', () => {
  it('renders live inputs and calls onGenerate with the draft', async () => {
    const onGenerate = vi.fn();
    const onClose = vi.fn();
    (useValueCaseGenerationInputs as Mock).mockReturnValue(mockInputs());

    const wrapper = createWrapper();
    render(
      <ValueCaseGenerationPanel
        accountId="acct-1"
        accountName="Acme"
        caseId="case-1"
        isOpen={true}
        onClose={onClose}
        onGenerate={onGenerate}
        isGenerating={false}
      />,
      { wrapper }
    );

    expect(screen.getByText('Generate Value Case')).toBeInTheDocument();
    expect(screen.getByText('CFO')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /generate value case/i }));

    await waitFor(() => {
      expect(onGenerate).toHaveBeenCalledWith(expect.objectContaining({
        account_id: 'acct-1',
        stakeholders: ['CFO'],
      }));
    });
  });
});
```

- [ ] **Step 2: Run the failing test**

```bash
pnpm --dir apps/web exec vitest run src/components/value-case/ValueCaseGenerationPanel.test.tsx
```

Expected: FAIL — component and `useValueCaseGenerationInputs` import unresolved.

- [ ] **Step 3: Implement the component**

Create `apps/web/src/components/value-case/ValueCaseGenerationPanel.tsx`:

```tsx
import { useState, useEffect } from 'react';
import { Loader2, Plus, X, AlertCircle } from 'lucide-react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useValueCaseGenerationInputs } from '@/hooks/useValueCaseGenerationInputs';
import type { ValueCaseArtifactsInput } from '@/hooks/useValueCaseArtifacts';

export interface ValueCaseGenerationPanelProps {
  accountId: string;
  accountName: string;
  caseId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (input: ValueCaseArtifactsInput) => void;
  isGenerating: boolean;
}

function EditableStringList({
  label,
  items,
  onChange,
  placeholder,
}: {
  label: string;
  items: string[];
  onChange: (items: string[]) => void;
  placeholder?: string;
}) {
  const [newItem, setNewItem] = useState('');

  const addItem = () => {
    if (!newItem.trim()) return;
    onChange([...items, newItem.trim()]);
    setNewItem('');
  };

  const removeItem = (index: number) => {
    onChange(items.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium">{label}</h4>
      <div className="flex flex-wrap gap-2">
        {items.map((item, index) => (
          <Badge key={`${item}-${index}`} variant="secondary" className="gap-1">
            {item}
            <button
              type="button"
              onClick={() => removeItem(index)}
              className="ml-1 rounded-full hover:bg-muted"
              aria-label={`Remove ${item}`}
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
      </div>
      <div className="flex gap-2">
        <Input
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          placeholder={placeholder ?? 'Add item'}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              addItem();
            }
          }}
        />
        <Button type="button" variant="outline" size="icon" onClick={addItem}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

export function ValueCaseGenerationPanel({
  accountId,
  accountName,
  caseId,
  isOpen,
  onClose,
  onGenerate,
  isGenerating,
}: ValueCaseGenerationPanelProps) {
  const { draft, isLoading, isError, error, isReady } = useValueCaseGenerationInputs(
    accountId,
    accountName,
    caseId
  );
  const [input, setInput] = useState<ValueCaseArtifactsInput>(draft);

  useEffect(() => {
    setInput(draft);
  }, [draft]);

  const handleGenerate = () => {
    onGenerate(input);
  };

  const hasMinimumData =
    input.stakeholders.length > 0 ||
    input.accepted_evidence.length > 0 ||
    input.roi_metrics.three_year_value !== '';

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full sm:max-w-md flex flex-col">
        <SheetHeader>
          <SheetTitle>Generate Value Case</SheetTitle>
          <SheetDescription>
            Review and edit the inputs that will be used to generate the value case for {accountName}.
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto py-4 space-y-6">
          {isLoading && (
            <div className="text-sm text-muted-foreground flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading workspace data…
            </div>
          )}

          {isError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {error?.message ?? 'Failed to load some workspace data.'}
              </AlertDescription>
            </Alert>
          )}

          {!isLoading && !hasMinimumData && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                No workspace data found. Add stakeholders, evidence, or run the ROI calculator before generating.
              </AlertDescription>
            </Alert>
          )}

          <EditableStringList
            label="Stakeholders"
            items={input.stakeholders}
            onChange={(stakeholders) => setInput((prev) => ({ ...prev, stakeholders }))}
            placeholder="Add stakeholder"
          />

          <EditableStringList
            label="Accepted Evidence"
            items={input.accepted_evidence}
            onChange={(accepted_evidence) => setInput((prev) => ({ ...prev, accepted_evidence }))}
            placeholder="Add evidence claim"
          />

          <EditableStringList
            label="Scenario Assumptions"
            items={input.scenario_assumptions}
            onChange={(scenario_assumptions) =>
              setInput((prev) => ({ ...prev, scenario_assumptions }))
            }
            placeholder="Add assumption"
          />

          <div className="space-y-2">
            <h4 className="text-sm font-medium">ROI Metrics</h4>
            <div className="grid grid-cols-3 gap-2">
              <Input
                value={input.roi_metrics.three_year_value}
                onChange={(e) =>
                  setInput((prev) => ({
                    ...prev,
                    roi_metrics: { ...prev.roi_metrics, three_year_value: e.target.value },
                  }))
                }
                placeholder="3-Year Value"
              />
              <Input
                value={input.roi_metrics.roi}
                onChange={(e) =>
                  setInput((prev) => ({
                    ...prev,
                    roi_metrics: { ...prev.roi_metrics, roi: e.target.value },
                  }))
                }
                placeholder="ROI"
              />
              <Input
                value={input.roi_metrics.payback}
                onChange={(e) =>
                  setInput((prev) => ({
                    ...prev,
                    roi_metrics: { ...prev.roi_metrics, payback: e.target.value },
                  }))
                }
                placeholder="Payback"
              />
            </div>
          </div>

          <EditableStringList
            label="Risk Notes"
            items={input.risk_notes}
            onChange={(risk_notes) => setInput((prev) => ({ ...prev, risk_notes }))}
            placeholder="Add risk note"
          />
        </div>

        <div className="border-t pt-4 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose} disabled={isGenerating}>
            Cancel
          </Button>
          <Button onClick={handleGenerate} disabled={!isReady || isGenerating || !hasMinimumData}>
            {isGenerating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Generate Value Case
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
```

- [ ] **Step 4: Run the test**

```bash
pnpm --dir apps/web exec vitest run src/components/value-case/ValueCaseGenerationPanel.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/value-case/ValueCaseGenerationPanel.tsx apps/web/src/components/value-case/ValueCaseGenerationPanel.test.tsx
git commit -m "feat(web): add ValueCaseGenerationPanel for reviewing live inputs

Co-authored-by: Ona <no-reply@ona.com>"
```

---

### Task 3: Wire panel into `ValueCasePage`

**Files:**
- Modify: `apps/web/src/pages/value-case/ValueCasePage.tsx`
- Test: `apps/web/src/pages/value-case/ValueCasePage.test.tsx`

**Interfaces:**
- Consumes: `ValueCaseGenerationPanel`, `useValueCaseArtifacts().generateArtifact`.
- Produces: `ValueCasePage` opens the panel on Generate/Regenerate and passes the edited draft to `generateArtifact.mutate()`.

- [ ] **Step 1: Write the failing test**

Create `apps/web/src/pages/value-case/ValueCasePage.test.tsx`:

```tsx
import { describe, it, expect, vi, type Mock } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { createWrapper } from '@/test-utils';
import ValueCasePage from './ValueCasePage';

vi.mock('@/hooks/useAccounts', () => ({
  useAccount: vi.fn(),
}));

vi.mock('@/hooks/useWorkspaceCase', () => ({
  useCanonicalCaseId: vi.fn(),
}));

vi.mock('@/hooks/useValueCaseArtifacts', () => ({
  useValueCaseArtifacts: vi.fn(),
}));

vi.mock('@/components/value-case/ValueCaseGenerationPanel', () => ({
  ValueCaseGenerationPanel: vi.fn(() => <div data-testid="generation-panel" />),
}));

import { useAccount } from '@/hooks/useAccounts';
import { useCanonicalCaseId } from '@/hooks/useWorkspaceCase';
import { useValueCaseArtifacts } from '@/hooks/useValueCaseArtifacts';

describe('ValueCasePage', () => {
  it('opens the generation panel instead of using hardcoded inputs', async () => {
    (useAccount as Mock).mockReturnValue({
      data: { id: 'acct-1', name: 'Acme' },
      isLoading: false,
    });
    (useCanonicalCaseId as Mock).mockReturnValue({
      data: 'case-1',
      isLoading: false,
    });
    (useValueCaseArtifacts as Mock).mockReturnValue({
      versions: [],
      isLoadingVersions: false,
      versionsError: null,
      refetch: vi.fn(),
      selectedVersion: null,
      setSelectedVersionId: vi.fn(),
      generateArtifact: { mutate: vi.fn(), isPending: false, isError: false, error: null },
      publishArtifact: { mutate: vi.fn(), isPending: false, isError: false, error: null },
    });

    const wrapper = createWrapper();
    render(<ValueCasePage accountId="acct-1" />, { wrapper });

    fireEvent.click(screen.getByRole('button', { name: /generate/i }));

    await waitFor(() => {
      expect(screen.getByTestId('generation-panel')).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Run the failing test**

```bash
pnpm --dir apps/web exec vitest run src/pages/value-case/ValueCasePage.test.tsx
```

Expected: FAIL — test file and component wiring do not exist.

- [ ] **Step 3: Modify `ValueCasePage.tsx`**

Replace the hardcoded `handleGenerate` with panel state. Edit `apps/web/src/pages/value-case/ValueCasePage.tsx`:

1. Add imports at the top:

```tsx
import { useState } from 'react';
import { useCanonicalCaseId } from '@/hooks/useWorkspaceCase';
import { ValueCaseGenerationPanel } from '@/components/value-case/ValueCaseGenerationPanel';
import type { ValueCaseArtifactsInput } from '@/hooks/useValueCaseArtifacts';
```

2. Remove the hardcoded `handleGenerate` function (lines 86-110) and replace with:

```tsx
const [isPanelOpen, setIsPanelOpen] = useState(false);

const handleGenerate = () => {
  setIsPanelOpen(true);
};

const handleConfirmGenerate = (input: ValueCaseArtifactsInput) => {
  generateArtifact.mutate(input);
  setIsPanelOpen(false);
};
```

3. Add a local wrapper component above the default export that resolves the canonical workspace case only when the panel is mounted:

```tsx
function GenerationPanelWithCase({
  accountId,
  accountName,
  isOpen,
  onClose,
  onGenerate,
  isGenerating,
}: {
  accountId: string;
  accountName: string;
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (input: ValueCaseArtifactsInput) => void;
  isGenerating: boolean;
}) {
  const { data: caseId } = useCanonicalCaseId(accountId);
  return (
    <ValueCaseGenerationPanel
      accountId={accountId}
      accountName={accountName}
      caseId={caseId ?? null}
      isOpen={isOpen}
      onClose={onClose}
      onGenerate={onGenerate}
      isGenerating={isGenerating}
    />
  );
}
```

4. Add the wrapper just before the closing `</div>`:

```tsx
<GenerationPanelWithCase
  accountId={account.id}
  accountName={account.name}
  isOpen={isPanelOpen}
  onClose={() => setIsPanelOpen(false)}
  onGenerate={handleConfirmGenerate}
  isGenerating={generateArtifact.isPending}
/>
```

- [ ] **Step 4: Run the test**

```bash
pnpm --dir apps/web exec vitest run src/pages/value-case/ValueCasePage.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/pages/value-case/ValueCasePage.tsx apps/web/src/pages/value-case/ValueCasePage.test.tsx
git commit -m "feat(web): wire ValueCaseGenerationPanel into ValueCasePage

Removes hardcoded value-case generation inputs.
Co-authored-by: Ona <no-reply@ona.com>"
```

---

### Task 4: Add hardcoded-string regression guard

**Files:**
- Create: `apps/web/src/pages/value-case/hardcoded-value-case-strings.test.ts`

**Interfaces:**
- Consumes: `ValueCasePage.tsx` source as a string.
- Produces: A failing test if any legacy hardcoded value-case string is found in the page source.

- [ ] **Step 1: Write the test**

Create `apps/web/src/pages/value-case/hardcoded-value-case-strings.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const pagePath = path.resolve(__dirname, 'ValueCasePage.tsx');
const source = fs.readFileSync(pagePath, 'utf-8');

const LEGACY_HARDCODED_STRINGS = [
  'Economic buyer',
  'Business champion',
  'Technical evaluator',
  'Validated calculator assumptions',
  'Accepted business pains from discovery',
  'Conservative ramp in Q1',
  'Expected adoption by Q2',
  '$1.8M',
  '214%',
  '9 months',
  'Change management capacity',
  'Competing budget priorities',
];

describe('ValueCasePage hardcoded input regression guard', () => {
  it.each(LEGACY_HARDCODED_STRINGS)('does not contain %s', (legacyString) => {
    expect(source).not.toContain(legacyString);
  });
});
```

- [ ] **Step 2: Run the test**

```bash
pnpm --dir apps/web exec vitest run src/pages/value-case/hardcoded-value-case-strings.test.ts
```

Expected: PASS after Task 3 is complete.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/pages/value-case/hardcoded-value-case-strings.test.ts
git commit -m "test(web): add regression guard for hardcoded value-case strings

Co-authored-by: Ona <no-reply@ona.com>"
```

---

### Task 5: Verify typecheck and tests

**Files:**
- None new.

**Interfaces:**
- Consumes: All files changed above.
- Produces: Green typecheck and test suite.

- [ ] **Step 1: Run frontend typecheck**

```bash
pnpm --dir apps/web run typecheck
```

Expected: no errors.

- [ ] **Step 2: Run frontend tests**

```bash
pnpm --dir apps/web test
```

Expected: all tests pass.

- [ ] **Step 3: Commit any final fixes**

```bash
git add -A
git commit -m "chore(web): typecheck and test fixes for value-case live inputs

Co-authored-by: Ona <no-reply@ona.com>"
```

---

## Self-Review

**Spec coverage:**
- ✅ Hardcoded inputs replaced — Tasks 1, 2, 3.
- ✅ Live data from workspace stakeholders — Task 1 (`useStakeholdersData`).
- ✅ Live data from L5 Ground Truth — Task 1 (`useTruths`).
- ✅ Live ROI metrics — Task 1 (`useROICalculations`).
- ✅ Pre-generation review panel — Task 2.
- ✅ Regression test preventing hardcoded strings — Task 4.
- ✅ Existing publish/update flows unchanged — Task 3 only modifies `handleGenerate` and adds panel.

**Placeholder scan:**
- ✅ No TBD/TODO/fill-in-details.
- ✅ Every code step includes actual code.
- ✅ Every test step includes actual test code.
- ✅ Commands include expected outputs.

**Type consistency:**
- ✅ `ValueCaseArtifactsInput` is reused across hook, panel, and page.
- ✅ `useValueCaseGenerationInputs` returns consistent `draft` / `provenance` shapes.
- ✅ Panel props match usage in `ValueCasePage`.

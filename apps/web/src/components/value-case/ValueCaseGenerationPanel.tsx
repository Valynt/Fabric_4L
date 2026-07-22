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

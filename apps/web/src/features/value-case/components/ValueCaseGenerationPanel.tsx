import { useState, useEffect, memo } from "react";
import { Loader2, Plus, X, AlertCircle, RefreshCw, Info } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import type {
  ValueCaseGenerationInputsDraft,
  ValueCaseInputProvenance,
  ValueCaseInputProvenanceMap,
  ValueCaseInputAvailability,
} from "../domain/valueCaseModels";
import type { ValueCaseBoundaryError } from "../api/valueCaseSchemas";

export interface ValueCaseGenerationPanelProps {
  accountName: string;
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (inputs: ValueCaseGenerationInputsDraft) => void;
  isGenerating: boolean;
  draft: ValueCaseGenerationInputsDraft;
  provenance: ValueCaseInputProvenanceMap;
  availability: ValueCaseInputAvailability;
  isLoadingInputs: boolean;
  inputsError: ValueCaseBoundaryError | null;
}

function getSourceLabel(source: ValueCaseInputProvenance["source"]): string {
  switch (source) {
    case "workspace_stakeholder":
    case "workspace_tab":
      return "Workspace";
    case "l5_truth":
      return "Ground Truth";
    case "roi_calculation":
      return "ROI Calculator";
    case "manual":
      return "Manual";
    default:
      return source;
  }
}

function SourceBadge({
  provenance,
}: {
  provenance: readonly ValueCaseInputProvenance[] | undefined;
}) {
  if (!provenance || provenance.length === 0) return null;
  const firstSource = provenance[0].source;
  const allSame = provenance.every(p => p.source === firstSource);
  const label = allSame ? getSourceLabel(firstSource) : "Mixed";
  return (
    <span className="text-xs text-muted-foreground" data-testid="source-badge">
      from {label}
    </span>
  );
}

function EditableStringList({
  label,
  items,
  onChange,
  placeholder,
  source,
}: {
  label: string;
  items: string[];
  onChange: (items: string[]) => void;
  placeholder?: string;
  source?: readonly ValueCaseInputProvenance[];
}) {
  const [newItem, setNewItem] = useState("");

  const addItem = () => {
    if (!newItem.trim()) return;
    onChange([...items, newItem.trim()]);
    setNewItem("");
  };

  const removeItem = (index: number) => {
    onChange(items.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <h4 className="text-sm font-medium text-foreground">{label}</h4>
        <SourceBadge provenance={source} />
      </div>
      <div className="flex flex-wrap gap-2">
        {items.map((item, index) => (
          <Badge key={index} variant="secondary" className="gap-1 text-xs">
            {item}
            <button
              type="button"
              onClick={() => removeItem(index)}
              className="ml-1 rounded-full hover:bg-muted focus:outline-none focus:ring-1 focus:ring-ring"
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
          onChange={e => setNewItem(e.target.value)}
          placeholder={placeholder ?? `Add ${label.toLowerCase()}`}
          onKeyDown={e => {
            if (e.key === "Enter") {
              e.preventDefault();
              addItem();
            }
          }}
        />
        <Button
          type="button"
          variant="outline"
          size="icon"
          onClick={addItem}
          aria-label={`Add ${label}`}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

export const ValueCaseGenerationPanel = memo(function ValueCaseGenerationPanel({
  accountName,
  isOpen,
  onClose,
  onGenerate,
  isGenerating,
  draft,
  provenance,
  availability,
  isLoadingInputs,
  inputsError,
}: ValueCaseGenerationPanelProps) {
  const [localDraft, setLocalDraft] = useState<ValueCaseGenerationInputsDraft>(draft);
  const [isDirty, setIsDirty] = useState(false);
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);

  useEffect(() => {
    if (isOpen && !isDirty) {
      setLocalDraft(draft);
    }
  }, [isOpen, draft, isDirty]);

  const updateDraft = (
    updater: (prev: ValueCaseGenerationInputsDraft) => ValueCaseGenerationInputsDraft
  ) => {
    setLocalDraft(updater);
    setIsDirty(true);
  };

  const handleReload = () => {
    setIsDirty(false);
    setLocalDraft(draft);
  };

  const handleGenerate = () => {
    setIsDirty(false);
    onGenerate(localDraft);
  };

  const requestClose = () => {
    if (isDirty) {
      setShowCloseConfirm(true);
    } else {
      onClose();
    }
  };

  const confirmDiscard = () => {
    setShowCloseConfirm(false);
    setIsDirty(false);
    onClose();
  };

  const hasMinimumData =
    localDraft.stakeholders.length > 0 ||
    localDraft.acceptedEvidence.length > 0 ||
    localDraft.roiMetrics.threeYearValue !== "";

  return (
    <Sheet open={isOpen} onOpenChange={open => !open && requestClose()}>
      <SheetContent className="w-full sm:max-w-lg flex flex-col">
        <SheetHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <SheetTitle>Generate Value Case</SheetTitle>
              <SheetDescription>
                Review and edit the deterministic inputs that will be used to generate the
                value narrative and business case for {accountName}.
              </SheetDescription>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleReload}
              disabled={isLoadingInputs || isGenerating}
              aria-label="Reload from workspace"
            >
              <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
              Reload
            </Button>
          </div>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto py-4 space-y-6">
          {isLoadingInputs && (
            <div className="text-sm text-muted-foreground flex items-center gap-2 p-2 rounded-md bg-muted/40">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span>Loading workspace inputs…</span>
            </div>
          )}

          {inputsError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {inputsError.message ?? "Failed to load some workspace data."}
              </AlertDescription>
            </Alert>
          )}

          {availability.hasPartialFailures && (
            <Alert variant="default" className="border-amber-300 bg-amber-50 dark:bg-amber-950/20 text-amber-800 dark:text-amber-200">
              <Info className="h-4 w-4 text-amber-600 dark:text-amber-400" />
              <AlertDescription>
                {availability.statusMessage}
              </AlertDescription>
            </Alert>
          )}

          {!isLoadingInputs && !hasMinimumData && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                No workspace data found. Add stakeholders, accepted evidence, or run the
                ROI calculator before generating.
              </AlertDescription>
            </Alert>
          )}

          <EditableStringList
            label="Stakeholders"
            items={localDraft.stakeholders}
            onChange={stakeholders =>
              updateDraft(prev => ({ ...prev, stakeholders }))
            }
            placeholder="Add stakeholder"
            source={provenance.stakeholders}
          />

          <EditableStringList
            label="Accepted Evidence"
            items={localDraft.acceptedEvidence}
            onChange={acceptedEvidence =>
              updateDraft(prev => ({ ...prev, acceptedEvidence }))
            }
            placeholder="Add evidence claim"
            source={provenance.acceptedEvidence}
          />

          <EditableStringList
            label="Scenario Assumptions"
            items={localDraft.scenarioAssumptions}
            onChange={scenarioAssumptions =>
              updateDraft(prev => ({ ...prev, scenarioAssumptions }))
            }
            placeholder="Add assumption"
            source={provenance.scenarioAssumptions}
          />

          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-medium text-foreground">ROI Metrics</h4>
              <SourceBadge provenance={provenance.roiMetrics} />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div className="space-y-1">
                <label className="text-[11px] text-muted-foreground font-medium">3-Year Value</label>
                <Input
                  value={localDraft.roiMetrics.threeYearValue}
                  onChange={e =>
                    updateDraft(prev => ({
                      ...prev,
                      roiMetrics: {
                        ...prev.roiMetrics,
                        threeYearValue: e.target.value,
                      },
                    }))
                  }
                  placeholder="$0M"
                  aria-label="3-Year Value"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[11px] text-muted-foreground font-medium">ROI</label>
                <Input
                  value={localDraft.roiMetrics.roi}
                  onChange={e =>
                    updateDraft(prev => ({
                      ...prev,
                      roiMetrics: { ...prev.roiMetrics, roi: e.target.value },
                    }))
                  }
                  placeholder="0%"
                  aria-label="ROI"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[11px] text-muted-foreground font-medium">Payback</label>
                <Input
                  value={localDraft.roiMetrics.payback}
                  onChange={e =>
                    updateDraft(prev => ({
                      ...prev,
                      roiMetrics: {
                        ...prev.roiMetrics,
                        payback: e.target.value,
                      },
                    }))
                  }
                  placeholder="0 mo"
                  aria-label="Payback"
                />
              </div>
            </div>
          </div>

          <EditableStringList
            label="Risk Notes"
            items={localDraft.riskNotes}
            onChange={riskNotes =>
              updateDraft(prev => ({ ...prev, riskNotes }))
            }
            placeholder="Add risk note"
            source={provenance.riskNotes}
          />
        </div>

        <div className="border-t border-border pt-4 flex justify-end gap-2">
          <Button
            variant="outline"
            onClick={requestClose}
            disabled={isGenerating}
          >
            Cancel
          </Button>
          <Button
            onClick={handleGenerate}
            disabled={isGenerating || !hasMinimumData}
          >
            {isGenerating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Generate Value Case
          </Button>
        </div>
      </SheetContent>

      <AlertDialog open={showCloseConfirm} onOpenChange={setShowCloseConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Discard unsaved changes?</AlertDialogTitle>
            <AlertDialogDescription>
              You have unsaved edits in your generation inputs. Closing now will discard your changes.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setShowCloseConfirm(false)}>
              Keep editing
            </AlertDialogCancel>
            <AlertDialogAction onClick={confirmDiscard}>
              Discard changes
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Sheet>
  );
});

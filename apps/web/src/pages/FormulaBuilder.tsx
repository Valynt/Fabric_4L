/**
 * Formula Builder — Create and edit value driver formulas
 *
 * Clean, focused interface for formula authoring with:
 * - Formula definition (name, description, value driver)
 * - Expression editor with syntax highlighting
 * - Variable palette for quick insertion
 * - Live evaluation with backend POST /v1/formulas/evaluate
 * - Version history panel (useFormulaVersions)
 * - Dependency graph panel (useFormulaDependents / useFormulaDependencies)
 * - What-if scenario panel (useFormulaScenario)
 * - Governance metadata (useFormulaGovernance)
 *
 * Route: /context/formulas/new  (isNew = true)
 *        /context/formulas/:formulaId
 */
import { useState, useMemo, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { z } from "zod";
import { useNavigation } from "@/hooks/useNavigation";
import {
  Save, CheckCircle2, AlertCircle, ChevronRight, Loader2,
  Target, GitBranch, Network, Beaker, Shield, Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PageShell } from "@/components";
import { ErrorState } from "@/components/states/ErrorState";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useVariables, type Variable, type VariableType, type SourceType } from "@/hooks/useVariables";
import {
  useFormula,
  useCreateFormula,
  useUpdateFormula,
  useEvaluateFormula,
  type FormulaEvaluationInput,
} from "@/hooks/useFormulas";
import { useFormulaVersions, useFormulaGovernance, type FormulaVersion } from "@/hooks/useFormulaVersions";
import { useFormulaDependents, useFormulaDependencies, type DependentAsset } from "@/hooks/useFormulaDependents";
import { useFormulaScenario, type VariableAdjustment, type ScenarioResponse } from "@/hooks/useFormulaScenario";
import { formatRelativeTime } from "@/lib/formatters";
import { VersionHistoryPanel, DependencyPanel, ScenarioPanel } from "./FormulaBuilder/components";
import { createFeatureLogger } from "@/lib/telemetry";
import { Tabs } from "@/components/ui/fabric";
import { SectionCard } from "@/components/blocks/SectionCard";
import { Btn } from "@/components/ui/fabric";

const log = createFeatureLogger('FormulaBuilder');

// ── Zod Validation Schema ────────────────────────────────────────────────────

const FormulaSchema = z.object({
  name: z.string().min(1, 'Formula name is required').max(120, 'Name must be under 120 characters'),
  description: z.string().max(500, 'Description must be under 500 characters').optional(),
  expression: z.string().min(1, 'Formula expression is required'),
  valueDriver: z.string().optional(),
});

type FormulaDraft = {
  name: string;
  description: string;
  expression: string;
  testInputs: TestInput[];
  valueDriver: string;
  savedAt: string;
};

function getDraftKey(formulaId: string | undefined) {
  return formulaId ? `formula-draft-${formulaId}` : 'formula-draft-new';
}

function loadDraft(formulaId: string | undefined): FormulaDraft | null {
  try {
    const raw = localStorage.getItem(getDraftKey(formulaId));
    if (!raw) return null;
    return JSON.parse(raw) as FormulaDraft;
  } catch {
    return null;
  }
}

function saveDraft(formulaId: string | undefined, draft: Omit<FormulaDraft, 'savedAt'>) {
  try {
    const payload: FormulaDraft = { ...draft, savedAt: new Date().toISOString() };
    localStorage.setItem(getDraftKey(formulaId), JSON.stringify(payload));
  } catch (err) {
    log.warn('Failed to save formula draft to localStorage', { error: err });
  }
}

function clearDraft(formulaId: string | undefined) {
  try {
    localStorage.removeItem(getDraftKey(formulaId));
  } catch {
    // ignore
  }
}

// ============================================================================
// Type Definitions
// ============================================================================
type FormulaVariableType = "rate" | "currency" | "integer";
type VariableSource = "CRM" | "Billing" | "Model" | "Manual";

interface FormulaVariable {
  name: string;
  type: FormulaVariableType;
  source: VariableSource;
}

interface TestInput {
  label: string;
  value: string;
}

// ============================================================================
// Constants
// ============================================================================
const SOURCE_TYPE_COLOR: Record<VariableSource, string> = {
  CRM: "bg-primary/10 text-primary",
  Billing: "bg-success/10 text-success",
  Model: "bg-primary/10 text-primary",
  Manual: "bg-warning/10 text-warning",
};

const DEFAULT_FORMULA_EXPRESSION = `({Customer_Count} *
{Current_Churn_Rate} -
{Projected_Retention_Lift}) *
{Average_Contract_Value} -
{Implementation_Cost}`;

const DEFAULT_TEST_INPUTS: TestInput[] = [
  { label: "Customer_Count", value: "1,000" },
  { label: "Current_Churn_Rate", value: "5%" },
  { label: "Projected_Retention_Lift", value: "2%" },
  { label: "Average_Contract_Value", value: "$50,000" },
  { label: "Implementation_Cost", value: "$100,000" },
];



/** Map API Variable to FormulaVariable format */
function mapVariableToFormulaVariable(variable: Variable): FormulaVariable {
  const typeMap: Record<string, FormulaVariableType> = {
    rate: "rate", currency: "currency", integer: "integer",
    float: "rate", boolean: "rate", string: "integer",
  };
  const sourceMap: Record<SourceType, VariableSource> = {
    CRM: "CRM", Billing: "Billing", ERP: "CRM",
    Manual: "Manual", Model: "Model", API: "CRM", Database: "Billing",
  };
  return {
    name: variable.name,
    type: typeMap[variable.type] || "integer",
    source: sourceMap[variable.source] || "Manual",
  };
}

// ============================================================================
// Main Component
// ============================================================================
interface FormulaBuilderProps {
  isNew?: boolean;
}

export default function FormulaBuilder({ isNew = false }: FormulaBuilderProps) {
  const params = useParams();
  const formulaId = params.formulaId;
  const { navigateTo } = useNavigation();
  const [tested, setTested] = useState(false);
  const [formulaExpression, setFormulaExpression] = useState(DEFAULT_FORMULA_EXPRESSION);
  const [formulaName, setFormulaName] = useState("Customer Churn Reduction ROI");
  const [formulaDescription, setFormulaDescription] = useState(
    "Calculate ROI from reducing customer churn through predictive analytics"
  );
  const [testInputs, setTestInputs] = useState(DEFAULT_TEST_INPUTS);
  const [evaluationResult, setEvaluationResult] = useState<{
    result: number;
    roi: number;
    roiPercent: number;
    confidence: number;
  } | null>(null);
  const [rightTab, setRightTab] = useState("Variables");
  const [valueDriver, setValueDriver] = useState("");
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [draftSavedAt, setDraftSavedAt] = useState<string | null>(null);
  const isDirtyRef = useRef(false);

  // Load draft from localStorage on mount
  useEffect(() => {
    const draft = loadDraft(formulaId);
    if (draft) {
      setFormulaName(draft.name);
      setFormulaDescription(draft.description);
      setFormulaExpression(draft.expression);
      setTestInputs(draft.testInputs);
      setValueDriver(draft.valueDriver);
      setDraftSavedAt(draft.savedAt);
    }
  }, [formulaId]);

  // Auto-save draft to localStorage every 5 seconds when dirty
  useEffect(() => {
    const timer = setInterval(() => {
      if (isDirtyRef.current) {
        saveDraft(formulaId, {
          name: formulaName,
          description: formulaDescription,
          expression: formulaExpression,
          testInputs,
          valueDriver,
        });
        setDraftSavedAt(new Date().toISOString());
        isDirtyRef.current = false;
      }
    }, 5000);
    return () => clearInterval(timer);
  }, [formulaId, formulaName, formulaDescription, formulaExpression, testInputs, valueDriver]);

  // Mark as dirty when form state changes
  useEffect(() => {
    isDirtyRef.current = true;
  }, [formulaName, formulaDescription, formulaExpression, testInputs, valueDriver]);

  // Fetch existing formula if editing
  const { data: existingFormula, isLoading: isLoadingFormula } = useFormula(
    !isNew && formulaId ? formulaId : null
  );

  // Mutations
  const { mutate: createFormula, isPending: isCreating, error: createError } = useCreateFormula();
  const { mutate: updateFormula, isPending: isUpdating, error: updateError } = useUpdateFormula();
  const { mutate: evaluateFormula, isPending: isEvaluatingPending } = useEvaluateFormula();

  // Load existing formula data
  useEffect(() => {
    if (existingFormula && !isNew) {
      setFormulaName(existingFormula.name);
      setFormulaDescription(existingFormula.description || "");
      setFormulaExpression(existingFormula.expression || DEFAULT_FORMULA_EXPRESSION);
    }
  }, [existingFormula, isNew]);

  // Fetch real variables from API
  const {
    data: apiVariables,
    isLoading: variablesLoading,
    isError: variablesIsError,
    error: variablesError,
  } = useVariables({ status: "validated" });

  const availableVariables = useMemo(() => {
    if (!apiVariables) return [];
    return apiVariables.map(mapVariableToFormulaVariable);
  }, [apiVariables]);

  const isSaving = isCreating || isUpdating;
  // Derive error from whichever mutation was last called
  const saveError = isNew ? createError : updateError;

  const handleSave = () => {
    const result = FormulaSchema.safeParse({
      name: formulaName,
      description: formulaDescription,
      expression: formulaExpression,
      valueDriver,
    });

    if (!result.success) {
      const errors: Record<string, string> = {};
      result.error.issues.forEach((issue) => {
        const path = issue.path[0] as string;
        errors[path] = issue.message;
      });
      setValidationErrors(errors);
      return;
    }

    setValidationErrors({});

    if (isNew) {
      createFormula(
        {
          name: formulaName,
          description: formulaDescription,
          expression: formulaExpression,
          variables: availableVariables.map((v) => v.name),
        },
        {
          onSuccess: (data) => {
            clearDraft(formulaId);
            navigateTo('formula-builder', { formulaId: data.id ?? data.formula_id });
          },
        }
      );
    } else if (formulaId) {
      updateFormula(
        {
          formulaId,
          name: formulaName,
          description: formulaDescription,
          expression: formulaExpression,
          variables: availableVariables.map((v) => v.name),
        },
        {
          onSuccess: () => {
            clearDraft(formulaId);
          },
        }
      );
    }
  };

  const handleTest = () => {
    const inputs = testInputs.map((input) => {
      const parsed = parseFloat(input.value.replace(/[$,%]/g, ""));
      const value = isNaN(parsed) ? 0 : parsed;
      return {
        name: input.label,
        value,
        unit: input.value.includes("$") ? "USD" : input.value.includes("%") ? "percent" : undefined,
      };
    });
    evaluateFormula(
      {
        formulaId: isNew ? undefined : formulaId,
        expression: formulaExpression,
        inputs,
      },
      {
        onSuccess: (result) => {
          const costInput = inputs.find((i) => i.name.includes("Cost"));
          const costValue = costInput?.value ?? 0;
          setEvaluationResult({
            result: result.result,
            roi: result.result - costValue,
            roiPercent: ((result.result - costValue) / (costValue || 1)) * 100,
            confidence: result.confidence,
          });
          setTested(true);
        },
        onError: (err) => {
          log.error('Formula evaluation error', { errorCode: err.message });
        },
      }
    );
  };

  // Right panel tabs (edit mode only)
  const rightTabs = isNew
    ? ["Variables"]
    : ["Variables", "Versions", "Dependencies", "Scenario"];

  if (isLoadingFormula) {
    return (
      <PageShell>
        <div className="flex items-center justify-center h-64">
          <Loader2 size={32} className="animate-spin text-muted-foreground/60" />
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 vf-text-caption text-muted-foreground mb-2">
        <span>Value Trees</span>
        <ChevronRight size={12} />
        <span>Formulas</span>
        <ChevronRight size={12} />
        <span className="text-foreground">{isNew ? "New Formula" : "Edit Formula"}</span>
      </div>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground mb-1">Formula Builder</h1>
        <p className="vf-text-body-l text-muted-foreground">
          Create mathematical formulas for value driver calculations.
        </p>
      </div>

      {saveError && (
        <ErrorState
          title="Failed to save formula"
          error={saveError}
          className="mb-4 py-4"
        />
      )}

      {/* Navigation Tabs */}
      <div className="flex items-center gap-6 border-b border-border mb-6" role="tablist" aria-label="Formula builder navigation">
        {["Tree Explorer", "Normalization", "Formulas"].map((tab) => (
          <button type="button"
            key={tab}
            role="tab"
            aria-selected={tab === "Formulas"}
            aria-label={`Navigate to ${tab}`}
            onClick={() => {
              if (tab === "Tree Explorer") navigateTo('value-trees');
              if (tab === "Normalization") navigateTo('normalization');
            }}
            className={`pb-3 vf-text-body-l font-medium transition-colors relative ${
              tab === "Formulas"
                ? "text-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab}
            {tab === "Formulas" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
            )}
          </button>
        ))}
      </div>

      <div className="flex gap-6">
        {/* Left main panel */}
        <div className="flex-1 space-y-4 max-w-2xl">
          {/* Formula Definition */}
          <SectionCard title="Formula Definition">
            <div className="space-y-4">
              <div>
                <label htmlFor="formula-name" className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground/60 block mb-1.5">
                  Name
                </label>
                <Input
                  id="formula-name"
                  value={formulaName}
                  onChange={(e) => setFormulaName(e.target.value)}
                  placeholder="Enter formula name..."
                  className={cn(
                    "w-full vf-text-body-m",
                    validationErrors.name ? "border-destructive/30 focus:border-destructive" : ""
                  )}
                  aria-invalid={!!validationErrors.name}
                  aria-describedby={validationErrors.name ? "name-error" : undefined}
                />
                {validationErrors.name && (
                  <p id="name-error" className="vf-text-caption text-destructive mt-1">{validationErrors.name}</p>
                )}
              </div>
              <div>
                <label htmlFor="formula-description" className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground/60 block mb-1.5">
                  Description
                </label>
                <Textarea
                  id="formula-description"
                  value={formulaDescription}
                  onChange={(e) => setFormulaDescription(e.target.value)}
                  placeholder="Describe what this formula calculates..."
                  rows={2}
                  className={cn(
                    "w-full vf-text-body-s resize-none",
                    validationErrors.description ? "border-destructive/30 focus:border-destructive" : ""
                  )}
                  aria-invalid={!!validationErrors.description}
                  aria-describedby={validationErrors.description ? "description-error" : undefined}
                />
                {validationErrors.description && (
                  <p id="description-error" className="vf-text-caption text-destructive mt-1">{validationErrors.description}</p>
                )}
              </div>
              <div>
                <label htmlFor="value-driver" className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground/60 block mb-1.5">
                  Associated Value Driver
                </label>
                <Select value={valueDriver} onValueChange={setValueDriver}>
                  <SelectTrigger id="value-driver" className="w-full vf-text-body-m h-9">
                    <SelectValue placeholder="Select a value driver..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="revenue_retention">Revenue Retention</SelectItem>
                    <SelectItem value="cost_reduction">Cost Reduction</SelectItem>
                    <SelectItem value="efficiency_gain">Efficiency Gain</SelectItem>
                    <SelectItem value="risk_mitigation">Risk Mitigation</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </SectionCard>

          {/* Formula Expression */}
          <SectionCard title="Formula Expression">
            <div className="relative">
              <Textarea
                id="formula-expression"
                value={formulaExpression}
                onChange={(e) => setFormulaExpression(e.target.value)}
                placeholder="Enter formula expression using {variable_name} syntax..."
                className={cn(
                  "w-full h-40 font-mono vf-text-body-m leading-relaxed resize-none",
                  validationErrors.expression
                    ? "bg-destructive/10 text-destructive border-destructive/20"
                    : "bg-foreground text-background"
                )}
                spellCheck={false}
                aria-label="Formula expression"
                aria-invalid={!!validationErrors.expression}
                aria-describedby={validationErrors.expression ? "expression-error" : undefined}
              />
              {validationErrors.expression && (
                <p id="expression-error" className="vf-text-caption text-destructive mt-1">{validationErrors.expression}</p>
              )}
              <div className="absolute bottom-3 left-4 flex gap-2">
                <Btn
                  variant="primary"
                  onClick={handleTest}
                  disabled={isEvaluatingPending || !formulaExpression.trim()}
                >
                  {isEvaluatingPending ? (
                    <Loader2 size={11} className="animate-spin" />
                  ) : (
                    <Target size={11} />
                  )}
                  {isEvaluatingPending ? " Testing..." : " Test with Sample Data"}
                </Btn>
              </div>
            </div>
          </SectionCard>

          {/* Test Results */}
          {tested && evaluationResult && (
            <SectionCard title="Test Results">
              <div className="space-y-1.5 mb-3">
                {testInputs.map((input, idx) => (
                  <div key={input.label} className="flex justify-between vf-text-body-s">
                    <span className="text-muted-foreground font-mono">{input.label}:</span>
                    <Input
                      type="text"
                      value={input.value}
                      onChange={(e) => {
                        const newInputs = [...testInputs];
                        newInputs[idx].value = e.target.value;
                        setTestInputs(newInputs);
                      }}
                      aria-label={`${input.label} test value`}
                      className="font-semibold text-foreground bg-transparent border-b border-border text-right w-32"
                    />
                  </div>
                ))}
              </div>
              <div className="border-t border-border/50 pt-3 flex items-center gap-6">
                <div>
                  <span className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground/60">
                    Result
                  </span>
                  <div className="text-xl font-extrabold text-success">
                    ${evaluationResult.result.toLocaleString()}
                  </div>
                </div>
                <div>
                  <span className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground/60">
                    ROI
                  </span>
                  <div className="text-xl font-extrabold text-success">
                    {evaluationResult.roiPercent.toFixed(0)}%
                  </div>
                </div>
                <div className="ml-auto">
                  <span className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground/60">
                    Confidence
                  </span>
                  <div className="vf-text-body-l font-bold text-foreground">
                    High ({evaluationResult.confidence.toFixed(2)})
                  </div>
                </div>
              </div>
            </SectionCard>
          )}
        </div>

        {/* Right panel */}
        <div className="w-[300px] shrink-0 space-y-4">
          {/* Tab selector */}
          <Tabs tabs={rightTabs} active={rightTab} onChange={setRightTab} />

          {/* Variables tab */}
          {rightTab === "Variables" && (
            <SectionCard title="Available Variables">
              {variablesLoading && (
                <div className="flex items-center gap-2 p-3 text-muted-foreground vf-text-caption">
                  <Loader2 size={12} className="animate-spin" />
                  <span>Loading variables...</span>
                </div>
              )}
              {variablesIsError && (
                <ErrorState
                  title="Failed to load variables"
                  error={variablesError}
                  className="py-4"
                />
              )}
              <div className="space-y-1">
                {availableVariables.map((variable) => (
                  <div
                    key={variable.name}
                    className="flex items-center gap-2 p-2.5 bg-secondary/30 rounded-md vf-text-body-s font-mono text-foreground hover:bg-secondary/50 cursor-pointer transition-colors group"
                    onClick={() => {
                      setFormulaExpression(formulaExpression + `{${variable.name}}`);
                    }}
                    title={`Insert ${variable.name} into formula`}
                    aria-label={`Insert variable ${variable.name}`}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        setFormulaExpression(formulaExpression + `{${variable.name}}`);
                      }
                    }}
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-primary/60 shrink-0 group-hover:bg-primary" />
                    <span className="truncate">{variable.name}</span>
                    <span className={`ml-auto vf-text-micro px-1.5 py-0.5 rounded-full ${SOURCE_TYPE_COLOR[variable.source]}`}>
                      {variable.source}
                    </span>
                  </div>
                ))}
              </div>
              <button type="button" className="w-full mt-3 py-2 vf-text-caption text-muted-foreground hover:text-foreground border border-dashed border-border rounded-md hover:border-muted-foreground/50 transition-colors">
                + Add Custom Variable
              </button>
            </SectionCard>
          )}

          {/* Versions tab */}
          {rightTab === "Versions" && formulaId && (
            <SectionCard title="Version History">
              <VersionHistoryPanel formulaId={formulaId} />
            </SectionCard>
          )}

          {/* Dependencies tab */}
          {rightTab === "Dependencies" && formulaId && (
            <SectionCard title="Dependencies">
              <DependencyPanel formulaId={formulaId} />
            </SectionCard>
          )}

          {/* Scenario tab */}
          {rightTab === "Scenario" && formulaId && (
            <SectionCard title="What-If Scenario">
              <ScenarioPanel formulaId={formulaId} />
            </SectionCard>
          )}

          {/* Draft Indicator */}
          {draftSavedAt && (
            <p className="vf-text-micro text-muted-foreground/70 text-center">
              Draft saved {formatRelativeTime(draftSavedAt)}
            </p>
          )}

          {/* Save Button */}
          <Btn
            variant="primary"
            onClick={handleSave}
            disabled={isSaving || !formulaName.trim()}
            className="w-full"
          >
            {isSaving ? (
              <>
                <Loader2 size={11} className="animate-spin mr-2" />
                Saving...
              </>
            ) : (
              <>
                <Save size={11} className="mr-2" />
                Save Formula
              </>
            )}
          </Btn>
        </div>
      </div>
    </PageShell>
  );
}

/**
 * Interactive Business Case Explorer
 * C1-powered conversational what-if analysis with sliders and scenario saving
 */

import { useState, useCallback, useMemo, useEffect, useRef } from "react";
import { Send, RotateCcw, Save, GitCompare, AlertCircle, Loader2 } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { useNavigation } from "@/hooks/useNavigation";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { useBusinessCase } from "@/hooks/useDocuments";
import { useC1Stream } from "@/hooks/useC1Stream";
import { isC1Enabled, C1Component, getScenarios } from "@/api/thesysClient";
import { createFeatureLogger } from "@/lib/telemetry";
import { PageShell } from "@/components";
import { ErrorState } from "@/components/states/ErrorState";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, Btn } from "@/components/ui/fabric";

const log = createFeatureLogger('InteractiveBusinessCase');

// Types for C1-generated components
interface MetricCardProps {
  label: string;
  value: number;
  delta?: number;
  unit?: string;
  trend?: 'up' | 'down' | 'neutral';
}

interface SliderControlProps {
  label: string;
  name: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  originalValue: number;
}

interface ScenarioButtonProps {
  name: string;
  onClick: () => void;
}

/**
 * Renders a metric card component from C1 stream
 */
function MetricCard({ label, value, delta, unit = '', trend = 'neutral' }: MetricCardProps) {
  const trendColor = trend === 'up' ? 'text-success' : trend === 'down' ? 'text-destructive' : 'text-muted-foreground';
  const deltaText = delta ? (delta > 0 ? `+${delta}%` : `${delta}%`) : '';

  return (
    <div className="bg-card border border-border rounded-lg p-4 shadow-sm">
      <div className="vf-text-caption font-medium uppercase tracking-wider text-muted-foreground mb-1">{label}</div>
      <div className="text-2xl font-bold text-foreground">
        {unit === '$' ? '$' : ''}{value.toLocaleString()}{unit === '%' ? '%' : ''}
      </div>
      {delta !== undefined && (
        <div className={`text-sm font-medium mt-1 ${trendColor}`}>
          {deltaText} vs original
        </div>
      )}
    </div>
  );
}

/**
 * Renders a slider control component with live recalculation
 */
function SliderControl({
  label,
  name,
  value: initialValue,
  min,
  max,
  step = 1,
  unit = '',
  originalValue,
  onChange,
}: SliderControlProps & { onChange: (val: number) => void }) {
  const [value, setValue] = useState(initialValue);
  const [isCalculating, setIsCalculating] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const handleChange = useCallback((newValue: number[]) => {
    const val = newValue[0];
    setValue(val);
    setIsCalculating(true);
    onChange(val);
    // Reset calculating state after a brief delay for UX
    timeoutRef.current = setTimeout(() => setIsCalculating(false), 300);
  }, [onChange]);

  const percentChange = ((value - originalValue) / originalValue) * 100;

  return (
    <div className="bg-card border border-border rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <label className="text-sm font-medium text-foreground">{label}</label>
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground">
            {unit === '$' ? '$' : ''}{value.toLocaleString()}{unit === '%' ? '%' : unit}
          </span>
          {isCalculating && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
        </div>
      </div>

      <Slider
        value={[value]}
        min={min}
        max={max}
        step={step}
        onValueChange={handleChange}
        className="w-full"
      />

      <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
        <span>Original: {unit === '$' ? '$' : ''}{originalValue.toLocaleString()}</span>
        <span className={percentChange >= 0 ? 'text-success' : 'text-destructive'}>
          {percentChange >= 0 ? '+' : ''}{percentChange.toFixed(1)}%
        </span>
      </div>
    </div>
  );
}

/**
 * Component renderer for C1-streamed components
 */
function C1ComponentRenderer({
  components,
  onSliderChange,
  onSaveScenario,
  onLoadScenario,
  savedScenarios,
}: {
  components: C1Component[];
  onSliderChange: (name: string, value: number, original: number) => void;
  onSaveScenario: (name: string) => void;
  onLoadScenario: (scenarioId: string) => void;
  savedScenarios: Array<{ id: string; name: string }>;
}) {
  const [newScenarioName, setNewScenarioName] = useState('');

  return (
    <div className="space-y-4">
      {components.map((comp, idx) => {
        switch (comp.type) {
          case 'MetricCard':
            return (
              <MetricCard
                key={idx}
                label={comp.props.label as string}
                value={comp.props.value as number}
                delta={comp.props.delta as number | undefined}
                unit={comp.props.unit as string | undefined}
                trend={comp.props.trend as 'up' | 'down' | 'neutral' | undefined}
              />
            );

          case 'Slider':
            return (
              <SliderControl
                key={idx}
                label={comp.props.label as string}
                name={comp.props.name as string}
                value={comp.props.value as number}
                min={comp.props.min as number}
                max={comp.props.max as number}
                step={comp.props.step as number | undefined}
                unit={comp.props.unit as string | undefined}
                originalValue={comp.props.originalValue as number}
                onChange={(val) => onSliderChange(comp.props.name as string, val, comp.props.originalValue as number)}
              />
            );

          case 'SaveScenarioButton':
            return (
              <div key={idx} className="flex items-center gap-2">
                <Input
                  placeholder="Scenario name..."
                  value={newScenarioName}
                  onChange={(e) => setNewScenarioName(e.target.value)}
                  className="flex-1"
                />
                <Btn
                  onClick={() => {
                    if (newScenarioName.trim()) {
                      onSaveScenario(newScenarioName.trim());
                      setNewScenarioName('');
                    }
                  }}
                  disabled={!newScenarioName.trim()}
                >
                  <Save size={14} className="mr-1" />
                  Save Scenario
                </Btn>
              </div>
            );

          case 'ScenarioSelector':
            return savedScenarios.length > 0 ? (
              <div key={idx} className="bg-muted rounded-lg p-3">
                <div className="text-sm font-medium text-foreground mb-2">Saved Scenarios</div>
                <div className="flex flex-wrap gap-2">
                  {savedScenarios.map((scenario) => (
                    <Btn
                      key={scenario.id}
                      variant="ghost"
                      className="text-xs"
                      onClick={() => onLoadScenario(scenario.id)}
                    >
                      {scenario.name}
                    </Btn>
                  ))}
                </div>
              </div>
            ) : null;

          default:
            return (
              <div key={idx} className="text-sm text-muted-foreground italic">
                Unknown component: {comp.type}
              </div>
            );
        }
      })}
    </div>
  );
}

export default function InteractiveBusinessCase() {
  const [searchParams] = useSearchParams();
  const { navigateTo } = useNavigation();
  const businessCaseId = searchParams.get("id");

  const [query, setQuery] = useState('');
  const [savedScenarios, setSavedScenarios] = useState<Array<{ id: string; name: string }>>([]);

  const { data: businessCase, isLoading, error } = useBusinessCase(businessCaseId);

  const businessCaseData = useMemo(() => {
    if (!businessCase) return undefined;
    return {
      total_value: businessCase.total_value,
      implementation_cost: businessCase.implementation_cost,
      roi_ratio: businessCase.roi_ratio,
      payback_months: businessCase.payback_months,
      confidence_score: businessCase.confidence_score,
      title: businessCase.title,
    };
  }, [businessCase]);

  const {
    state: c1State,
    sendQuery,
    reset,
    handleSliderChange,
    saveCurrentScenario,
    getSavedScenarios,
    isEnabled,
  } = useC1Stream({
    businessCaseId: businessCaseId || '',
    businessCaseData,
  });

  // Load saved scenarios on mount
  useEffect(() => {
    if (businessCaseId) {
      const scenarios = getSavedScenarios();
      setSavedScenarios(scenarios.map(s => ({ id: s.id, name: s.name })));
    }
  }, [businessCaseId, getSavedScenarios]);

  const handleSendQuery = useCallback(() => {
    if (query.trim()) {
      sendQuery(query.trim());
      setQuery('');
    }
  }, [query, sendQuery]);

  const handleSliderUpdate = useCallback((name: string, value: number, original: number) => {
    handleSliderChange({ name, value, original_value: original });
  }, [handleSliderChange]);

  const handleSaveScenario = useCallback((name: string) => {
    // Get current slider values from C1 components
    const adjustments = c1State.components
      .filter(c => c.type === 'Slider')
      .map(c => ({
        name: c.props.name as string,
        value: c.props.value as number,
      }));

    const id = saveCurrentScenario(name, adjustments);
    setSavedScenarios(prev => [...prev, { id, name }]);
  }, [c1State.components, saveCurrentScenario]);

  const handleLoadScenario = useCallback((scenarioId: string) => {
    if (!businessCaseId) return;
    const allScenarios = getScenarios(businessCaseId);
    const scenario = allScenarios.find(s => s.id === scenarioId);
    if (!scenario) {
      log.warn(`Scenario ${scenarioId} not found`);
      return;
    }

    // Apply each adjustment from the saved scenario to the matching slider
    for (const adj of scenario.adjustments) {
      const slider = c1State.components.find(
        c => c.type === 'Slider' && c.props.name === adj.name
      );
      if (slider) {
        handleSliderChange({
          name: adj.name,
          value: adj.value,
          original_value: slider.props.originalValue as number,
        });
      }
    }
  }, [businessCaseId, c1State.components, handleSliderChange]);

  // Handle missing ID
  if (!businessCaseId) {
    return (
      <PageShell className="max-w-5xl">
        <div className="bg-warning/10 border border-warning/20 rounded-lg p-4 text-warning">
          No business case ID provided. Please select a business case to explore.
        </div>
      </PageShell>
    );
  }

  // C1 not enabled fallback
  if (!isEnabled && !isLoading) {
    return (
      <PageShell className="max-w-5xl">
        <PageHeader
          breadcrumbs={[{ label: "Agent Workflows" }, { label: "Business Cases" }, { label: "Interactive Explorer" }]}
          title="Interactive Explorer"
          subtitle="AI-powered what-if analysis"
        />
        <div className="bg-warning/10 border border-warning/20 rounded-lg p-6 text-warning">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 mt-0.5" />
            <div>
              <div className="font-semibold mb-1">C1 Integration Not Enabled</div>
              <p className="text-sm mb-3">
                Interactive business case exploration requires Thesys C1. To enable:
              </p>
              <ol className="text-sm list-decimal list-inside space-y-1">
                <li>Get an API key from <a href="https://thesys.dev" className="underline">thesys.dev</a></li>
                <li>Add <code className="bg-amber-100 px-1 rounded">VITE_THESYS_API_KEY</code> to your environment</li>
                <li>Set <code className="bg-amber-100 px-1 rounded">VITE_ENABLE_C1_REPORTS=true</code></li>
              </ol>
            </div>
          </div>
        </div>
      </PageShell>
    );
  }

  if (isLoading) {
    return (
      <PageShell className="max-w-5xl">
        <PageHeader
          breadcrumbs={[{ label: "Agent Workflows" }, { label: "Business Cases" }, { label: "Interactive Explorer" }]}
          title="Loading..."
          subtitle=""
        />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
          </div>
          <div className="space-y-4">
            <Skeleton className="h-20" />
            <Skeleton className="h-20" />
            <Skeleton className="h-20" />
          </div>
        </div>
      </PageShell>
    );
  }

  if (error || !businessCase) {
    return (
      <PageShell className="max-w-5xl">
        <ErrorState
          title="Failed to load business case"
          description="We couldn't load the business case data. Please try again."
          error={error}
        />
      </PageShell>
    );
  }

  return (
    <PageShell className="max-w-5xl">
      <PageHeader
        breadcrumbs={[{ label: "Agent Workflows" }, { label: "Business Cases" }, { label: "Interactive Explorer" }]}
        title={businessCase.title || "Interactive Business Case"}
        subtitle={`Explore "what-if" scenarios with AI-generated controls · ${new Date(businessCase.created_at || '').toLocaleDateString()}`}
        actions={
          <>
            <Btn variant="ghost" onClick={() => navigateTo('business-case-interactive', undefined, { query: { id: businessCaseId } })}>
              View Static Report
            </Btn>
            <Btn variant="ghost" onClick={reset}>
              <RotateCcw size={14} className="mr-1" />
              Reset
            </Btn>
          </>
        }
      />

      {/* Error display */}
      {c1State.error && (
        <div
          className="bg-destructive/10 border border-destructive/20 rounded-lg p-3 mb-4 flex items-center gap-2 text-destructive text-sm"
          role="alert"
          aria-live="assertive"
          aria-atomic="true"
        >
          <AlertCircle className="w-4 h-4" />
          <span>{c1State.error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left column: Chat input and streamed components */}
        <div className="space-y-4">
          <SectionCard title='Ask "What If..."' className="mb-4">
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Input
                  placeholder="e.g., What if implementation cost doubles?"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendQuery()}
                  disabled={c1State.isStreaming}
                  className="flex-1"
                />
                <Btn
                  onClick={handleSendQuery}
                  disabled={!query.trim() || c1State.isStreaming}
                >
                  {c1State.isStreaming ? (
                    <Loader2 size={14} className="animate-spin mr-1" />
                  ) : (
                    <Send size={14} className="mr-1" />
                  )}
                  Send
                </Btn>
              </div>
              <div className="text-xs text-muted-foreground">
                Try: "Reduce timeline by 3 months", "Double the confidence score", "What if costs increase 20%?"
              </div>
            </div>
          </SectionCard>

          {/* Streamed C1 components */}
          {c1State.components.length > 0 && (
            <SectionCard title="Interactive Controls">
              <div
                aria-live="polite"
                aria-atomic="true"
                className="sr-only"
                role="status"
              >
                {c1State.components.length} interactive control{c1State.components.length !== 1 ? 's' : ''} generated{c1State.isComplete ? '. Generation complete.' : '. More controls may appear.'}
              </div>
              <C1ComponentRenderer
                components={c1State.components}
                onSliderChange={handleSliderUpdate}
                onSaveScenario={handleSaveScenario}
                onLoadScenario={handleLoadScenario}
                savedScenarios={savedScenarios}
              />
            </SectionCard>
          )}

          {c1State.isStreaming && c1State.components.length === 0 && (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 className="w-6 h-6 animate-spin mr-2" aria-hidden="true" />
              <span aria-live="polite" aria-atomic="true">
                Generating interactive controls...
              </span>
            </div>
          )}
        </div>

        {/* Right column: Base case summary */}
        <div>
          <SectionCard title="Base Case Summary">
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-primary/10 rounded-lg p-4">
                <div className="vf-text-caption font-medium uppercase tracking-wider text-primary mb-1">
                  Total Value
                </div>
                <div className="text-2xl font-bold text-foreground">
                  ${businessCase.total_value.toLocaleString()}
                </div>
              </div>

              <div className="bg-success/10 rounded-lg p-4">
                <div className="vf-text-caption font-medium uppercase tracking-wider text-success mb-1">
                  ROI Ratio
                </div>
                <div className="text-2xl font-bold text-foreground">
                  {businessCase.roi_ratio.toFixed(2)}x
                </div>
              </div>

              <div className="bg-purple-50 rounded-lg p-4">
                <div className="vf-text-caption font-medium uppercase tracking-wider text-primary mb-1">
                  Payback Period
                </div>
                <div className="text-2xl font-bold text-foreground">
                  {businessCase.payback_months} months
                </div>
              </div>

              <div className="bg-warning/10 rounded-lg p-4">
                <div className="vf-text-caption font-medium uppercase tracking-wider text-warning mb-1">
                  Confidence
                </div>
                <div className="text-2xl font-bold text-foreground">
                  {Math.round(businessCase.confidence_score * 100)}%
                </div>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-border">
              <div className="text-sm font-medium text-foreground mb-2">Implementation Cost</div>
              <div className="text-lg font-semibold text-foreground">
                ${businessCase.implementation_cost.toLocaleString()}
              </div>
            </div>
          </SectionCard>

          {/* Saved scenarios */}
          {savedScenarios.length > 0 && (
            <SectionCard title={`Saved Scenarios (${savedScenarios.length})`} className="mt-4">
              <div className="space-y-2">
                {savedScenarios.map((scenario) => (
                  <div
                    key={scenario.id}
                    className="flex items-center justify-between p-3 bg-muted rounded-lg"
                  >
                    <span className="text-sm font-medium text-foreground">{scenario.name}</span>
                    <Btn variant="ghost" className="h-8 px-2">
                      <GitCompare size={14} />
                    </Btn>
                  </div>
                ))}
              </div>
            </SectionCard>
          )}
        </div>
      </div>
    </PageShell>
  );
}

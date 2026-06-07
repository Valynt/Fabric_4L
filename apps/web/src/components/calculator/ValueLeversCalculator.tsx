import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Save, RotateCcw } from "lucide-react";
import { ProgressBar, SectionCard } from "@/components/blocks";
import { useCreateValueCase, useUpdateValueCase, useValueCase, useValueLevers, type ValueCaseResponse } from "@/hooks/useCalculators";

export interface ValueLeversCalculatorProps {
  accountId: string;
  industry?: string;
  companySize?: string;
  initialCaseId?: string | null;
  onSaved?: (valueCase: ValueCaseResponse) => void;
}

export function ValueLeversCalculator({ accountId, industry, companySize, initialCaseId = null, onSaved }: ValueLeversCalculatorProps) {
  const { data: leverConfig, isLoading, error } = useValueLevers({ industry, company_size: companySize });
  const { data: existingCase } = useValueCase(initialCaseId);
  const createCase = useCreateValueCase();
  const updateCase = useUpdateValueCase();
  const [leverValues, setLeverValues] = useState<Record<string, { valA: number; valB: number }>>({});
  const initializedConfigRef = useRef<string | null>(null);

  useEffect(() => {
    if (leverConfig && initializedConfigRef.current !== leverConfig.metadata.version) {
      initializedConfigRef.current = leverConfig.metadata.version;
      setLeverValues(leverConfig.levers.reduce((acc, l) => ({ ...acc, [l.id]: { valA: l.min_value, valB: l.base_value } }), {}));
    }
  }, [leverConfig]);

  useEffect(() => {
    if (!existingCase) return;
    const next: Record<string, { valA: number; valB: number }> = {};
    existingCase.levers.forEach((lever) => {
      next[lever.lever_id] = { valA: lever.scenario_a, valB: lever.scenario_b };
    });
    setLeverValues(next);
  }, [existingCase]);

  const totals = useMemo(() => {
    if (!leverConfig) return { A: 0, B: 0 };
    return {
      A: leverConfig.levers.reduce((s, l) => l.base_value === 0 ? s : s + l.annual_impact * ((leverValues[l.id]?.valA || l.min_value) / l.base_value), 0),
      B: leverConfig.levers.reduce((s, l) => l.base_value === 0 ? s : s + l.annual_impact * ((leverValues[l.id]?.valB || l.base_value) / l.base_value), 0),
    };
  }, [leverConfig, leverValues]);

  const handleSave = useCallback(async () => {
    if (!leverConfig) return;
    const payload = {
      account_id: accountId,
      levers: Object.entries(leverValues).map(([id, v]) => ({ lever_id: id, scenario_a: v.valA, scenario_b: v.valB })),
      scenarios: [
        { name: "Conservative" as const, total_value: totals.A, breakdown: [] },
        { name: "Expected" as const, total_value: totals.B, breakdown: [] },
      ],
      metadata: { generated_by: "shared-calculator", confidence_score: 85 },
    };
    const saved = initialCaseId
      ? await updateCase.mutateAsync({ caseId: initialCaseId, data: payload })
      : await createCase.mutateAsync(payload);
    onSaved?.(saved);
  }, [accountId, createCase, initialCaseId, leverConfig, leverValues, onSaved, totals.A, totals.B, updateCase]);

  if (!industry || !companySize) {
    return <div className="rounded border border-amber-400/40 bg-warning/10 p-3 text-sm text-warning">Select an account with industry and company size before loading value levers.</div>;
  }

  return <SectionCard title="Value Levers">
    {isLoading ? <div className="text-sm text-muted-foreground">Loading value levers...</div> : error ? <div className="text-sm text-destructive">Failed to load value levers.</div> : (
      <div className="space-y-3">
        {(leverConfig?.levers ?? []).map((lever) => (
          <div key={lever.id} className="rounded border border-border p-3">
            <div className="mb-2 flex items-center justify-between"><span className="text-xs font-semibold">{lever.name}</span><span className="text-xs text-muted-foreground">{lever.confidence}% confidence</span></div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <label>Conservative<input type="range" min={lever.min_value} max={lever.max_value} value={leverValues[lever.id]?.valA ?? lever.min_value} onChange={(e) => setLeverValues((p) => ({ ...p, [lever.id]: { valA: Number(e.target.value), valB: p[lever.id]?.valB ?? lever.base_value } }))} className="w-full" /></label>
              <label>Expected<input type="range" min={lever.min_value} max={lever.max_value} value={leverValues[lever.id]?.valB ?? lever.base_value} onChange={(e) => setLeverValues((p) => ({ ...p, [lever.id]: { valA: p[lever.id]?.valA ?? lever.min_value, valB: Number(e.target.value) } }))} className="w-full" /></label>
            </div>
            <ProgressBar value={lever.confidence} max={100} size="sm" />
          </div>
        ))}
        <div className="flex gap-2"><button onClick={() => leverConfig && setLeverValues(leverConfig.levers.reduce((acc, l) => ({ ...acc, [l.id]: { valA: l.min_value, valB: l.base_value } }), {}))} className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 text-xs"><RotateCcw className="h-3 w-3" />Reset</button><button onClick={handleSave} className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 text-xs"><Save className="h-3 w-3" />Save</button></div>
      </div>
    )}
  </SectionCard>;
}

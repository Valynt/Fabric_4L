/**
 * ValueNarrativeHero — Primary CTA for narrative creation
 *
 * Dark-themed hero section matching the "Create a value narrative" design.
 * Wires directly into:
 *   • Layer 4 workflows (narrative, ROI, template generation)
 *   • Layer 1 ingestion (URL / file / CRM import)
 *   • Layer 6 benchmarks (industry selection)
 *
 * Renders inside AppShell's scrollable main area.
 */

import { useState, useCallback } from "react";
import { ArrowRight, Loader2, Upload, Database, FileText, PenLine, BarChart3, LayoutTemplate } from "lucide-react";
import { useNarrativeStore, type OutputType, type InputMethod, FALLBACK_INDUSTRIES, looksLikeUrl } from "@/stores/narrativeStore";
import { useGenerateNarrative, useIndustries } from "@/hooks/useNarrativeGeneration";
import { useSubmitDomain } from "@/hooks/useIngestion";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

// ── Output type buttons ───────────────────────────────────────────────────────

const OUTPUT_TYPES: { id: OutputType; label: string; icon: typeof PenLine }[] = [
  { id: "narrative",      label: "Narrative",       icon: PenLine },
  { id: "roi_model",      label: "ROI Model",       icon: BarChart3 },
  { id: "value_template", label: "Value Template",  icon: LayoutTemplate },
];

// ── Input method buttons ──────────────────────────────────────────────────────

const INPUT_METHODS: { id: InputMethod; label: string; icon: typeof Upload }[] = [
  { id: "import", label: "Import Data",  icon: Upload },
  { id: "file",   label: "Attach File",  icon: FileText },
  { id: "crm",    label: "CRM",          icon: Database },
];

// ── Component ─────────────────────────────────────────────────────────────────

export default function ValueNarrativeHero() {
  const { prompt, setPrompt, outputType, setOutputType, industry, setIndustry } = useNarrativeStore();
  const generateNarrative = useGenerateNarrative();
  const submitDomain = useSubmitDomain();
  const { data: industries } = useIndustries();
  const [showIndustryPicker, setShowIndustryPicker] = useState(false);

  const industryList = industries && industries.length > 0 ? industries : FALLBACK_INDUSTRIES;
  const isGenerating = generateNarrative.isPending || submitDomain.isPending;

  const handleGenerate = useCallback(() => {
    if (!prompt.trim() || isGenerating) return;

    // If the input looks like a URL, run ingestion first
    const trimmed = prompt.trim();

    if (looksLikeUrl(trimmed)) {
      submitDomain.mutate({ domain: trimmed }, {
        onSuccess: () => {
          // After ingestion starts, also kick off the narrative workflow
          generateNarrative.mutate({ prompt: trimmed, outputType, industry });
        },
      });
    } else {
      generateNarrative.mutate({ prompt: trimmed, outputType, industry });
    }
  }, [prompt, outputType, industry, isGenerating, generateNarrative, submitDomain]);

  return (
    <section className="relative w-full bg-[#0a0f1e] overflow-hidden">
      {/* Subtle gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-blue-950/30 via-transparent to-transparent pointer-events-none" />

      <div className="relative max-w-3xl mx-auto px-6 pt-14 pb-10 text-center">
        {/* Badge */}
        <Badge variant="outline" className="mb-6 px-4 py-1.5 vf-text-caption font-semibold tracking-widest uppercase border-primary/30 bg-primary/10 text-primary">
          AI-Powered Value Intelligence
        </Badge>

        {/* Heading */}
        <h1 className="text-[clamp(28px,5vw,48px)] font-extrabold text-white tracking-tight leading-[1.1] mb-4">
          Create a value narrative
        </h1>

        {/* Subtitle */}
        <p className="vf-text-body-l leading-relaxed text-blue-200/70 max-w-xl mx-auto mb-8">
          Paste a company, CRM URL, earnings report, or describe the business case you want to build.
          Start with intent, then move directly into narrative, ROI, and evidence-backed strategy.
        </p>

        {/* ── Textarea ──────────────────────────────────────────────────────── */}
        <div className="bg-[#111827] border border-white/10 rounded-2xl shadow-2xl mb-0 text-left overflow-hidden">
          <textarea
            rows={4}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Paste company, CRM URL, or earnings report… or describe the value narrative you want to create"
            className="w-full bg-transparent vf-text-body-l text-blue-100/90 placeholder:text-blue-300/40 px-5 pt-5 pb-3 resize-none outline-none"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleGenerate();
              }
            }}
          />

          {/* ── Action bar ────────────────────────────────────────────────── */}
          <div className="flex items-end justify-between gap-4 px-5 pb-5 pt-2 flex-wrap">
            {/* Left: output types + input methods */}
            <div className="flex flex-wrap gap-2">
              {/* Output type pills */}
              {OUTPUT_TYPES.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setOutputType(id)}
                  className={cn(
                    "inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full vf-text-body-s font-semibold border transition-colors",
                    outputType === id
                      ? "bg-background text-foreground border-background"
                      : "bg-background/5 text-primary-foreground/80 border-background/10 hover:bg-background/10 hover:border-background/20"
                  )}
                >
                  <Icon size={13} />
                  {label}
                </button>
              ))}

              {/* Input method pills */}
              {INPUT_METHODS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full vf-text-body-s font-semibold border bg-background/5 text-primary-foreground/80 border-background/10 hover:bg-background/10 hover:border-background/20 transition-colors"
                >
                  <Icon size={13} />
                  {label}
                </button>
              ))}
            </div>

            {/* Right: industry picker + generate */}
            <div className="flex items-center gap-2 shrink-0">
              {/* Industry pill */}
              <div className="relative">
                <button
                  onClick={() => setShowIndustryPicker((v) => !v)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full vf-text-body-s font-semibold border bg-background/5 text-primary-foreground/80 border-background/10 hover:bg-background/10 hover:border-background/20 transition-colors"
                >
                  <span className="text-primary-foreground/60 vf-text-caption">Industry:</span>
                  <span>{industry}</span>
                </button>

                {/* Dropdown */}
                {showIndustryPicker && (
                  <div className="absolute bottom-full mb-2 right-0 w-48 bg-popover border border-border rounded-lg shadow-xl py-1 z-50 max-h-64 overflow-y-auto">
                    {industryList.map((ind) => (
                      <button
                        key={ind}
                        onClick={() => {
                          setIndustry(ind);
                          setShowIndustryPicker(false);
                        }}
                        className={cn(
                          "w-full text-left px-3 py-1.5 vf-text-body-s transition-colors",
                          industry === ind
                            ? "bg-primary/30 text-primary-foreground font-semibold"
                            : "text-muted-foreground hover:bg-muted/50"
                        )}
                      >
                        {ind}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Generate button */}
              <button
                onClick={handleGenerate}
                disabled={!prompt.trim() || isGenerating}
                className={cn(
                  "inline-flex items-center gap-2 px-5 py-2 rounded-full vf-text-body-m font-bold transition-all",
                  "bg-background text-foreground hover:bg-muted",
                  "disabled:opacity-40 disabled:cursor-not-allowed"
                )}
              >
                {isGenerating ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <>
                    Generate
                    <ArrowRight size={14} />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Success / error feedback */}
        {generateNarrative.isSuccess && (
          <p className="mt-4 vf-text-body-s text-emerald-400/80">
            ✓ Workflow started — ID: {generateNarrative.data.workflow_id}
          </p>
        )}
        {generateNarrative.isError && (
          <p className="mt-4 vf-text-body-s text-destructive">
            {generateNarrative.error.message}
          </p>
        )}
      </div>
    </section>
  );
}

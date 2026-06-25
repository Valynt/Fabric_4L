"use client";

import { FadeIn } from "./FadeIn";

const steps = [
  {
    num: "01",
    title: "Capture intelligence",
    desc: "Ingest signals from earnings calls, annual reports, analyst research, and your CRM. Every insight is source-tagged and confidence-scored.",
  },
  {
    num: "02",
    title: "Structure value drivers",
    desc: "Map account pain points to weighted value drivers. Connect signals to financial outcomes with reusable formulas.",
  },
  {
    num: "03",
    title: "Quantify and benchmark",
    desc: "Build interactive ROI models with real customer data. Validate assumptions against peer benchmarks and industry datasets.",
  },
  {
    num: "04",
    title: "Validate and govern",
    desc: "Approval gates, decision traces, and audit trails ensure every claim is defensible before it reaches the buyer.",
  },
  {
    num: "05",
    title: "Deliver the case",
    desc: "Generate CFO-grade financial views, executive summaries, and technical reviews — all exportable to PDF with one click.",
  },
];

export function WorkflowSection() {
  return (
    <section id="workflow" className="py-20 md:py-32 bg-muted/20">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-foreground text-center">
            From first signal to final deliverable.
          </h2>
          <p className="mt-4 text-center text-[15px] text-muted-foreground max-w-2xl mx-auto">
            A five-step workflow that takes account intelligence and turns it into
            executive-ready value cases.
          </p>
        </FadeIn>

        <div className="mt-16 md:mt-20">
          {/* Desktop: horizontal with connecting line */}
          <div className="hidden md:block relative">
            {/* Connecting line */}
            <div className="absolute top-[28px] left-[10%] right-[10%] h-px bg-border" aria-hidden="true" />

            <div className="grid grid-cols-5 gap-6 relative">
              {steps.map((step, i) => (
                <FadeIn key={step.num} delay={i * 0.12}>
                  <div className="flex flex-col items-center text-center">
                    <div className="flex h-14 w-14 items-center justify-center rounded-full bg-background border-2 border-primary/20 text-sm font-semibold text-primary shadow-sm z-10">
                      {step.num}
                    </div>
                    <span className="mt-4 text-4xl font-extrabold text-primary/20 leading-none">
                      {step.num}
                    </span>
                    <h3 className="mt-3 text-sm font-semibold text-foreground">
                      {step.title}
                    </h3>
                    <p className="mt-2 text-xs leading-relaxed text-muted-foreground max-w-[200px]">
                      {step.desc}
                    </p>
                  </div>
                </FadeIn>
              ))}
            </div>
          </div>

          {/* Mobile: vertical timeline */}
          <div className="md:hidden relative">
            <div className="absolute left-[19px] top-0 bottom-0 w-px bg-border" aria-hidden="true" />
            <div className="space-y-8">
              {steps.map((step, i) => (
                <FadeIn key={step.num} delay={i * 0.1}>
                  <div className="flex gap-4 relative">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-background border-2 border-primary/20 text-xs font-semibold text-primary shadow-sm z-10">
                      {step.num}
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-foreground">
                        {step.title}
                      </h3>
                      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                        {step.desc}
                      </p>
                    </div>
                  </div>
                </FadeIn>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

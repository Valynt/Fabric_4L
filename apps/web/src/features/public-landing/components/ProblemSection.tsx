"use client";

import { FadeIn } from "./FadeIn";
import { DemoCta } from "./DemoCta";

const painPoints = [
  "Research lives in documents no one reads",
  "Assumptions hide in spreadsheets no one validates",
  "Stakeholder knowledge is trapped in CRM notes",
  "ROI logic is disconnected from the evidence",
  "Sellers, executives, and technical buyers see different narratives",
];

export function ProblemSection() {
  return (
    <section className="py-20 md:py-32 bg-background">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
          {/* Left: text */}
          <div>
            <FadeIn>
              <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-foreground">
                The value case is broken.
              </h2>
            </FadeIn>
            <FadeIn delay={0.1}>
              <p className="mt-4 text-[15px] leading-relaxed text-muted-foreground">
                Revenue teams waste hours stitching together scattered research,
                stale spreadsheets, and disconnected narratives. The result? A
                value story that falls apart under scrutiny.
              </p>
            </FadeIn>

            <FadeIn delay={0.2}>
              <ul className="mt-8 space-y-4">
                {painPoints.map((point) => (
                  <li key={point} className="flex items-start gap-3">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-destructive/70" />
                    <span className="text-sm text-muted-foreground">
                      {point}
                    </span>
                  </li>
                ))}
              </ul>
            </FadeIn>
          </div>

          {/* Right: visual */}
          <FadeIn delay={0.3} direction="left">
            <div className="relative">
              {/* Before: scattered */}
              <div className="rounded-xl border border-dashed border-border bg-muted/30 p-6 space-y-3" aria-hidden="true">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-4">
                  Before
                </p>
                <div className="flex flex-wrap gap-2">
                  {["Spreadsheet v3.xlsx", "CRM notes", "Pitch deck", "Email thread", "Analyst report PDF"].map(
                    (label) => (
                      <span
                        key={label}
                        className="inline-flex items-center rounded-md border border-border bg-background px-2.5 py-1 text-xs text-muted-foreground shadow-sm"
                      >
                        {label}
                      </span>
                    )
                  )}
                </div>
                <div className="flex items-center gap-2 pt-2">
                  <span className="h-2 w-2 rounded-full bg-destructive/60" />
                  <span className="text-xs text-muted-foreground">
                    Disconnected, ungoverned, unconvincing
                  </span>
                </div>
              </div>

              {/* Arrow down */}
              <div className="flex justify-center py-4" aria-hidden="true">
                <div className="h-8 w-px bg-border" />
              </div>

              {/* After: unified */}
              <div className="rounded-xl border border-primary/20 bg-primary/5 p-6 space-y-3" aria-hidden="true">
                <p className="text-xs font-medium text-primary uppercase tracking-wider mb-4">
                  After
                </p>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center rounded-md bg-primary/10 border border-primary/20 px-3 py-1.5 text-xs font-medium text-primary">
                    Intelligence
                  </span>
                  <span className="text-muted-foreground">&rarr;</span>
                  <span className="inline-flex items-center rounded-md bg-primary/10 border border-primary/20 px-3 py-1.5 text-xs font-medium text-primary">
                    Value Studio
                  </span>
                  <span className="text-muted-foreground">&rarr;</span>
                  <span className="inline-flex items-center rounded-md bg-primary/10 border border-primary/20 px-3 py-1.5 text-xs font-medium text-primary">
                    Deliverables
                  </span>
                </div>
                <div className="flex items-center gap-2 pt-2">
                  <span className="h-2 w-2 rounded-full bg-primary" />
                  <span className="text-xs text-primary font-medium">
                    Connected, governed, defensible
                  </span>
                </div>
              </div>
            </div>
          </FadeIn>
        </div>

        <DemoCta />
      </div>
    </section>
  );
}

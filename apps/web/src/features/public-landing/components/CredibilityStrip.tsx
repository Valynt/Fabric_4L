"use client";

import { ShieldCheck, BarChart3, Lock, Building2 } from "lucide-react";
import { FadeIn } from "./FadeIn";

const items = [
  {
    icon: ShieldCheck,
    title: "Evidence-backed",
    desc: "Every claim traced to its source",
  },
  {
    icon: BarChart3,
    title: "Benchmark-aware",
    desc: "Validate against peer data",
  },
  {
    icon: Lock,
    title: "Governed and auditable",
    desc: "Approval gates and decision traces",
  },
  {
    icon: Building2,
    title: "Built for enterprise",
    desc: "Role-based access, tenant isolation",
  },
];

export function CredibilityStrip() {
  return (
    <section className="py-12 md:py-16 bg-muted/40 border-y border-border">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-8">
          {items.map((item, i) => {
            const Icon = item.icon;
            return (
              <FadeIn key={item.title} delay={i * 0.1}>
                <div className="flex items-start gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                    <Icon className="h-4 w-4 text-primary" aria-hidden="true" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      {item.title}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {item.desc}
                    </p>
                  </div>
                </div>
              </FadeIn>
            );
          })}
        </div>
      </div>
    </section>
  );
}

"use client";

import { Link2, ShieldCheck, CheckCircle2, Users, ScrollText } from "lucide-react";
import { FadeIn } from "./FadeIn";
import { DemoCta } from "./DemoCta";

const trustItems = [
  {
    icon: Link2,
    title: "Evidence attribution",
    desc: "Every insight links back to its original source",
  },
  {
    icon: ShieldCheck,
    title: "Confidence and provenance",
    desc: "Claims are scored by confidence and validated through decision traces",
  },
  {
    icon: CheckCircle2,
    title: "Approval workflows",
    desc: "No deliverable leaves draft without passing review gates",
  },
  {
    icon: Users,
    title: "Role-based access",
    desc: "Organization-scoped workspaces with fine-grained permissions",
  },
  {
    icon: ScrollText,
    title: "Auditable outputs",
    desc: "Complete audit trails from ingestion to export",
  },
];

export function TrustSection() {
  return (
    <section id="trust" className="py-20 md:py-32 bg-background">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-foreground text-center">
            Trust through transparency.
          </h2>
          <p className="mt-4 text-center text-[15px] text-muted-foreground max-w-2xl mx-auto">
            ValuePact does not just produce value cases. It proves how every
            conclusion was reached.
          </p>
        </FadeIn>

        <div className="mt-16 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {trustItems.map((item, i) => {
            const Icon = item.icon;
            return (
              <FadeIn key={item.title} delay={i * 0.1}>
                <div className="group rounded-xl border border-border bg-card p-6 hover:border-primary/30 hover:shadow-md transition-all duration-300 h-full">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                    <Icon className="h-5 w-5 text-primary" />
                  </div>
                  <h3 className="mt-4 text-sm font-semibold text-foreground">
                    {item.title}
                  </h3>
                  <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                    {item.desc}
                  </p>
                </div>
              </FadeIn>
            );
          })}
        </div>

        <DemoCta />
      </div>
    </section>
  );
}

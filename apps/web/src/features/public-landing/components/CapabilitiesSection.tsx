"use client";

import { Search, GitBranch, BarChart3, Bot, FileText, Target } from "lucide-react";
import { FadeIn } from "./FadeIn";
import { DemoCta } from "./DemoCta";

const capabilities = [
  {
    icon: Search,
    title: "Intelligence",
    desc: "Capture and organize account signals, stakeholders, evidence, and hypotheses — all with source attribution.",
    span: "md:col-span-2",
  },
  {
    icon: GitBranch,
    title: "Value Studio",
    desc: "Build driver trees, run ROI calculations, generate executive narratives, and track value realization.",
    span: "",
  },
  {
    icon: BarChart3,
    title: "Peer Benchmarking",
    desc: "Compare your value models against industry datasets across manufacturing, financial services, healthcare, AI, and public sector.",
    span: "",
  },
  {
    icon: Bot,
    title: "Governed AI",
    desc: "AI-assisted synthesis with full traceability. Every AI-generated claim links back to source evidence.",
    span: "",
  },
  {
    icon: FileText,
    title: "Executive Deliverables",
    desc: "CFO, executive, and technical views — each tailored to the reader's priorities and exportable to PDF.",
    span: "",
  },
  {
    icon: Target,
    title: "Value Realization",
    desc: "Track post-sale value delivery with milestone-based plans that close the loop between promise and outcome.",
    span: "",
  },
];

export function CapabilitiesSection() {
  return (
    <section id="product" className="py-20 md:py-32 bg-background">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-foreground text-center">
            Everything you need to sell on value.
          </h2>
          <p className="mt-4 text-center text-[15px] text-muted-foreground max-w-2xl mx-auto">
            Six integrated capabilities that connect intelligence to revenue.
          </p>
        </FadeIn>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-4">
          {capabilities.map((cap, i) => {
            const Icon = cap.icon;
            return (
              <FadeIn
                key={cap.title}
                delay={i * 0.08}
                className={`${cap.span}`}
              >
                <div
                  className={`group h-full rounded-xl border border-border bg-card p-6 hover:border-primary/30 hover:shadow-md transition-all duration-300 ${cap.span}`}
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                    <Icon className="h-5 w-5 text-primary" />
                  </div>
                  <h3 className="mt-4 text-base font-semibold text-foreground">
                    {cap.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                    {cap.desc}
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

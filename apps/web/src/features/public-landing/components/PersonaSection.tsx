"use client";

import { useState } from "react";
import {
  Lightbulb,
  User,
  Wrench,
  Settings,
  Eye,
} from "lucide-react";
import { FadeIn } from "./FadeIn";

const personas = [
  {
    id: "consultant",
    label: "Value Consultant",
    icon: Lightbulb,
    description:
      "Build defensible driver trees and business cases fast. Reuse formulas, validate with benchmarks, and deliver through approval gates.",
    illustration: "Driver tree with 5 connected nodes, benchmark comparison panel, and approval status badge.",
  },
  {
    id: "ae",
    label: "Account Executive",
    icon: User,
    description:
      "Walk into every meeting with a quantified value story. Share executive-ready deliverables that differentiate you from competitors quoting features.",
    illustration: "Executive summary PDF preview with ROI chart and stakeholder map.",
  },
  {
    id: "se",
    label: "Sales Engineer",
    icon: Wrench,
    description:
      "Validate technical assumptions, map stakeholder influence, and connect product capabilities to financial outcomes — all with evidence.",
    illustration: "Technical validation matrix with evidence links and confidence scores.",
  },
  {
    id: "revops",
    label: "RevOps Leader",
    icon: Settings,
    description:
      "Standardize value selling across your team with reusable templates, governed workflows, and consistent deliverables.",
    illustration: "Template library with usage analytics and team adoption metrics.",
  },
  {
    id: "exec",
    label: "Executive Reviewer",
    icon: Eye,
    description:
      "Review approved business cases with confidence. Every claim is traceable, every number is validated, every view is tailored to your priorities.",
    illustration: "Audit trail timeline showing review gates and approval signatures.",
  },
];

export function PersonaSection() {
  const [active, setActive] = useState(personas[0].id);
  const activePersona = personas.find((p) => p.id === active) || personas[0];

  return (
    <section id="use-cases" className="py-20 md:py-32 bg-muted/20">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-foreground text-center">
            Built for every role in the value process.
          </h2>
          <p className="mt-4 text-center text-[15px] text-muted-foreground max-w-2xl mx-auto">
            Each persona gets the tools and views they need to contribute to a
            defensible value case.
          </p>
        </FadeIn>

        {/* Desktop: Tabs */}
        <FadeIn delay={0.2} className="mt-12 hidden md:block">
          <div className="flex items-center justify-center gap-2" role="tablist" aria-label="Use cases by role">
            {personas.map((p) => {
              const Icon = p.icon;
              return (
                <button type="button"
                  key={p.id}
                  onClick={() => setActive(p.id)}
                  role="tab"
                  aria-selected={active === p.id}
                  aria-controls={`panel-${p.id}`}
                  className={`inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all ${
                    active === p.id
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground hover:bg-accent"
                  }`}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {p.label}
                </button>
              );
            })}
          </div>

          <div className="mt-8 rounded-xl border border-border bg-card p-8" id={`panel-${activePersona.id}`} role="tabpanel" tabIndex={0}>
            <div className="grid lg:grid-cols-2 gap-8 items-center">
              <div>
                <div className="flex items-center gap-3 mb-4">
                  {(() => {
                    const Icon = activePersona.icon;
                    return (
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <Icon className="h-5 w-5 text-primary" />
                      </div>
                    );
                  })()}
                  <h3 className="text-lg font-semibold text-foreground">
                    {activePersona.label}
                  </h3>
                </div>
                <p className="text-[15px] leading-relaxed text-muted-foreground">
                  {activePersona.description}
                </p>
              </div>
              <div className="rounded-lg border border-border bg-muted/30 p-6">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
                  Key view
                </p>
                <p className="text-sm text-muted-foreground">
                  {activePersona.illustration}
                </p>
              </div>
            </div>
          </div>
        </FadeIn>

        {/* Mobile: Accordion-style stacked */}
        <div className="md:hidden mt-10 space-y-4">
          {personas.map((p, i) => {
            const Icon = p.icon;
            return (
              <FadeIn key={p.id} delay={i * 0.08}>
                <button type="button"
                  onClick={() => setActive(active === p.id ? "" : p.id)}
                  aria-expanded={active === p.id}
                  className={`w-full text-left rounded-xl border p-5 transition-all ${
                    active === p.id
                      ? "border-primary/30 bg-primary/5"
                      : "border-border bg-card"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Icon className="h-5 w-5 text-primary" />
                      <span className="text-sm font-medium text-foreground">
                        {p.label}
                      </span>
                    </div>
                    <svg
                      className={`h-4 w-4 text-muted-foreground transition-transform ${
                        active === p.id ? "rotate-180" : ""
                      }`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </div>
                  {active === p.id && (
                    <div className="mt-4 pt-4 border-t border-border">
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        {p.description}
                      </p>
                    </div>
                  )}
                </button>
              </FadeIn>
            );
          })}
        </div>
      </div>
    </section>
  );
}

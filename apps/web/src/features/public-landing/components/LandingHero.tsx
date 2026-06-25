"use client";

import { Search, TrendingUp, FileText, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FadeIn } from "./FadeIn";
import { DEMO_URL } from "../config";

const workflowCards = [
  {
    title: "Intelligence",
    items: ["12 signals detected", "4 stakeholders mapped", "Evidence: High confidence"],
    icon: Search,
  },
  {
    title: "Value Studio",
    items: ["Driver tree: 5 nodes", "ROI: 247% over 3 years", "Benchmark: Top quartile"],
    icon: TrendingUp,
  },
  {
    title: "Deliverables",
    items: ["CFO view ready", "Executive summary", "Technical review"],
    icon: FileText,
  },
];

export function LandingHero() {
  const scrollToWorkflow = () => {
    const el = document.getElementById("workflow");
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <section
      id="hero"
      className="relative pt-32 pb-20 md:pt-44 md:pb-32 overflow-hidden"
    >
      {/* Subtle gradient background */}
      <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent pointer-events-none" aria-hidden="true" />

      <div className="relative mx-auto max-w-[1200px] px-4 sm:px-6 lg:px-8">
        {/* Text content — max-width for readability */}
        <div className="max-w-[800px] mx-auto text-center">
          <FadeIn>
            <h1 className="text-3xl sm:text-4xl lg:text-[2.8rem] font-extrabold leading-tight tracking-tight text-foreground">
              Turn account evidence into a business case your buyer can defend.
            </h1>
          </FadeIn>

          <FadeIn delay={0.1}>
            <p className="mt-5 text-[15px] leading-relaxed text-muted-foreground max-w-[640px] mx-auto">
              ValuePact brings account intelligence, financial modeling, peer
              benchmarks, and governed AI into one workflow — so revenue teams
              can build credible value cases and executive-ready deliverables.
            </p>
          </FadeIn>

          <FadeIn delay={0.2}>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
              <Button asChild size="lg">
                <a
                  href={DEMO_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Book a demo
                </a>
              </Button>
              <Button
                variant="outline"
                size="lg"
                onClick={scrollToWorkflow}
              >
                See how it works
              </Button>
            </div>
          </FadeIn>

          <FadeIn delay={0.3}>
            <div className="mt-6 flex items-center gap-2 text-sm text-muted-foreground">
              <Check className="h-4 w-4 text-primary" />
              <span>Built for enterprise value teams</span>
            </div>
          </FadeIn>
        </div>

        {/* Product composition cards */}
        <FadeIn delay={0.4} className="mt-16 lg:mt-20">
          <div className="grid sm:grid-cols-3 gap-4">
            {workflowCards.map((card) => {
              const Icon = card.icon;
              return (
                <div
                  key={card.title}
                  className="rounded-xl border border-border bg-card p-5 shadow-sm hover:shadow-md hover:border-primary/20 transition-all duration-300"
                >
                  <div className="flex items-center gap-2.5 mb-4">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                      <Icon className="h-4 w-4 text-primary" />
                    </div>
                    <h3 className="text-sm font-semibold text-foreground">
                      {card.title}
                    </h3>
                  </div>
                  <ul className="space-y-2">
                    {card.items.map((item) => (
                      <li
                        key={item}
                        className="flex items-center gap-2 text-xs text-muted-foreground"
                      >
                        <div className="h-1 w-1 rounded-full bg-primary/60" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        </FadeIn>
      </div>
    </section>
  );
}

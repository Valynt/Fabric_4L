"use client";

import { ArrowRight, TrendingUp, Users, FileText, Check } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { FadeIn } from "./FadeIn";
import { DemoCta } from "./DemoCta";

export function ProductProofSection() {
  return (
    <section className="py-20 md:py-32 bg-background">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-foreground text-center">
            See how the case comes together.
          </h2>
          <p className="mt-4 text-center text-[15px] text-muted-foreground max-w-2xl mx-auto">
            From raw signal to board-ready deliverable — every step visible,
            every claim traceable.
          </p>
        </FadeIn>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Evidence Chain */}
          <FadeIn delay={0.1}>
            <Card className="h-full">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Check className="h-4 w-4 text-primary" />
                  Evidence Chain
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">Signal</Badge>
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  <Badge variant="secondary">Driver</Badge>
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  <Badge>Evidence</Badge>
                </div>
                <div className="rounded-lg border border-border bg-muted/30 p-3">
                  <p className="text-xs text-muted-foreground italic">
                    &ldquo;Manual QA processes slowing release cycles by 3 weeks
                    on average...&rdquo;
                  </p>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-success" />
                    <span className="text-[10px] text-muted-foreground">
                      Source: Q3 Earnings Call · Confidence: 92%
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </FadeIn>

          {/* Value Driver Model */}
          <FadeIn delay={0.2}>
            <Card className="h-full">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  Value Driver Model
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {[
                    { label: "Cost Reduction", value: 65, color: "bg-primary" },
                    { label: "Revenue Uplift", value: 45, color: "bg-chart-2" },
                    { label: "Risk Mitigation", value: 30, color: "bg-chart-3" },
                    { label: "Time Savings", value: 55, color: "bg-chart-4" },
                  ].map((item) => (
                    <div key={item.label} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">
                          {item.label}
                        </span>
                        <span className="text-xs font-medium text-foreground">
                          {item.value}%
                        </span>
                      </div>
                      <Progress value={item.value} className="h-1.5" />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </FadeIn>

          {/* Benchmark Range */}
          <FadeIn delay={0.3}>
            <Card className="h-full">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Users className="h-4 w-4 text-primary" />
                  Benchmark Comparison
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
                    <span>Bottom quartile</span>
                    <span>Top quartile</span>
                  </div>
                  {/* Benchmark bar */}
                  <div className="relative h-8 rounded-lg bg-muted overflow-hidden">
                    <div className="absolute inset-y-0 left-[20%] right-[60%] bg-primary/20 rounded-l-lg" />
                    <div className="absolute inset-y-0 left-[40%] right-[40%] bg-primary/40" />
                    <div className="absolute inset-y-0 left-[60%] right-[20%] bg-primary/60" />
                    <div className="absolute inset-y-0 left-[80%] right-0 bg-primary/80 rounded-r-lg" />
                    {/* Your position marker */}
                    <div
                      className="absolute top-1/2 -translate-y-1/2 z-10"
                      style={{ left: "73%" }}
                    >
                      <div className="h-6 w-1 bg-foreground rounded-full shadow-sm" />
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">
                      Industry avg: 187%
                    </span>
                    <span className="text-xs font-semibold text-foreground">
                      Your ROI: 247% (Top quartile)
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </FadeIn>

          {/* Executive Deliverable Preview */}
          <FadeIn delay={0.4}>
            <Card className="h-full">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <FileText className="h-4 w-4 text-primary" />
                  Executive Summary Preview
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="rounded-lg border border-border bg-muted/20 p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-foreground uppercase tracking-wider">
                      Business Case: Acme Corp
                    </span>
                    <Badge variant="outline" className="text-[10px]">
                      CFO View
                    </Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-4 pt-2 border-t border-border">
                    <div>
                      <p className="text-[10px] text-muted-foreground uppercase">
                        3-Year NPV
                      </p>
                      <p className="text-sm font-semibold text-foreground">
                        $4.2M
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground uppercase">
                        ROI
                      </p>
                      <p className="text-sm font-semibold text-foreground">
                        247%
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground uppercase">
                        Payback
                      </p>
                      <p className="text-sm font-semibold text-foreground">
                        8.4 mo
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 pt-1">
                    <Check className="h-3 w-3 text-success" />
                    <span className="text-[10px] text-muted-foreground">
                      All figures validated · 5 sources · Approved by J. Smith
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </FadeIn>
        </div>

        <DemoCta />
      </div>
    </section>
  );
}

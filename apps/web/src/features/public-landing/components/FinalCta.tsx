"use client";

import { Button } from "@/components/ui/button";
import { FadeIn } from "./FadeIn";
import { DEMO_URL } from "../config";

export function FinalCta() {
  return (
    <section className="py-20 md:py-32 bg-background border-t border-border">
      <div className="mx-auto max-w-[768px] px-4 sm:px-6 lg:px-8 text-center">
        <FadeIn>
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-foreground">
            Turn account evidence into a business case your buyer can defend.
          </h2>
        </FadeIn>

        <FadeIn delay={0.15}>
          <p className="mt-4 text-[15px] text-muted-foreground">
            See how revenue teams use ValuePact to close more deals with
            defensible value cases.
          </p>
        </FadeIn>

        <FadeIn delay={0.3}>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Button asChild size="lg">
              <a
                href={DEMO_URL}
                target="_blank"
                rel="noopener noreferrer"
              >
                Book a demo
              </a>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <a href="/sign-in">Sign in</a>
            </Button>
          </div>
        </FadeIn>
      </div>
    </section>
  );
}

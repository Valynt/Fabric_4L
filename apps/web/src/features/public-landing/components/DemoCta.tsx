"use client";

import { Button } from "@/components/ui/button";
import { DEMO_URL } from "../config";

interface DemoCtaProps {
  label?: string;
  description?: string;
}

export function DemoCta({ 
  label = "See it in action", 
  description = "Book a demo to see how ValuePact works for your team." 
}: DemoCtaProps) {
  return (
    <div className="mt-12 text-center">
      <p className="text-sm text-muted-foreground mb-4">{description}</p>
      <Button asChild size="lg">
        <a href={DEMO_URL} target="_blank" rel="noopener noreferrer" aria-label={`${label} (opens in new tab)`}>
          {label}
        </a>
      </Button>
    </div>
  );
}

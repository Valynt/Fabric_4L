"use client";

import { Code2 } from "lucide-react";
import { FadeIn } from "./FadeIn";

const integrations = [
  {
    name: "Salesforce",
    desc: "Sync account data, opportunities, and contacts",
    icon: (
      <svg className="h-8 w-8" viewBox="0 0 24 24" fill="none">
        <path
          d="M10.006 14.324c-.267.295-.678.42-1.065.316l-2.27-.593a1.35 1.35 0 0 1-.964-1.175 1.33 1.33 0 0 1 .616-1.293l1.82-1.24a1.35 1.35 0 0 1 1.197-.183c.4.1.738.37.927.74l1.065 2.08c.228.446.127.988-.253 1.348zm-1.35-4.653c.388.104.8-.02 1.066-.316l1.53-1.69c.31-.342.397-.823.225-1.247l-.867-2.045a1.35 1.35 0 0 0-.928-.74 1.35 1.35 0 0 0-1.196.183l-1.82 1.24a1.33 1.33 0 0 0-.617 1.292c.08.518.44.95.965 1.176l2.602.047zm3.94 1.58c-.19.37-.528.64-.928.74l-2.27.593c-.387.104-.798-.02-1.065-.316a1.33 1.33 0 0 1-.253-1.348l1.065-2.08c.19-.37.528-.64.928-.74.4-.1.83-.02 1.196.183l1.82 1.24c.39.266.597.73.616 1.293 0 .518-.34.97-.828 1.175l.82.26zm1.35 4.654c-.387-.104-.8.02-1.065.316l-1.53 1.69c-.31.342-.397.823-.225 1.247l.867 2.045c.19.37.528.64.928.74.4.1.83.02 1.196-.183l1.82-1.24a1.33 1.33 0 0 0 .617-1.292 1.35 1.35 0 0 0-.965-1.176l-2.643-.147z"
          fill="#00A1E0"
        />
      </svg>
    ),
  },
  {
    name: "HubSpot",
    desc: "Connect contacts, companies, and deals",
    icon: (
      <svg className="h-8 w-8" viewBox="0 0 24 24" fill="none">
        <path
          d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"
          fill="#FF7A59"
        />
        <circle cx="12" cy="12" r="3" fill="#FF7A59" />
      </svg>
    ),
  },
  {
    name: "API Access",
    desc: "Extend ValuePact with your own integrations",
    icon: <Code2 className="h-8 w-8 text-primary" />,
  },
];

export function IntegrationsSection() {
  return (
    <section className="py-20 md:py-32 bg-muted/20">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-foreground text-center">
            Connects to your existing stack.
          </h2>
          <p className="mt-4 text-center text-[15px] text-muted-foreground max-w-2xl mx-auto">
            Sync data from the tools your team already uses.
          </p>
        </FadeIn>

        <div className="mt-16 grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-3xl mx-auto">
          {integrations.map((item, i) => (
            <FadeIn key={item.name} delay={i * 0.1}>
              <div className="flex flex-col items-center text-center rounded-xl border border-border bg-card p-6 hover:border-primary/30 hover:shadow-md transition-all duration-300 h-full">
                <div className="flex h-14 w-14 items-center justify-center rounded-lg bg-muted">
                  {item.icon}
                </div>
                <h3 className="mt-4 text-sm font-semibold text-foreground">
                  {item.name}
                </h3>
                <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                  {item.desc}
                </p>
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  );
}

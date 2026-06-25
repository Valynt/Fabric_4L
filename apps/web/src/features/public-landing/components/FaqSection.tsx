"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { FadeIn } from "./FadeIn";

const faqs = [
  {
    q: "How is ValuePact different from a spreadsheet or generic AI assistant?",
    a: "Spreadsheets can't trace claims to source evidence, enforce approval gates, or generate role-specific deliverables. Generic AI can't benchmark against peer data or maintain decision provenance. ValuePact connects intelligence gathering, financial modeling, governance, and delivery in one purpose-built workflow.",
  },
  {
    q: "Can users trace where a financial claim came from?",
    a: "Yes — every claim in a ValuePact business case links back to its source evidence, with confidence scores and decision traces showing how the conclusion was reached.",
  },
  {
    q: "Who is ValuePact designed for?",
    a: "ValuePact is built for enterprise revenue and value teams: value consultants, account executives, sales engineers, RevOps leaders, and the executives who review their deliverables.",
  },
  {
    q: "Can outputs support different executive audiences?",
    a: "Yes — ValuePact generates CFO views (financial metrics, cost-benefit analysis), executive views (strategic summaries, recommendations), and technical views (evidence provenance, implementation details), all from the same underlying value model.",
  },
  {
    q: "How does benchmarking work?",
    a: "ValuePact includes pre-loaded industry datasets across manufacturing, financial services, healthcare, AI/data, and public sector. Users can compare their value models against peer benchmarks to validate assumptions and sanity-check ranges.",
  },
  {
    q: "How does ValuePact fit into an existing revenue workflow?",
    a: "ValuePact integrates with Salesforce and HubSpot, imports existing research and CRM data, and exports deliverables as PDFs. Teams can use it alongside their existing sales methodology without replacing their CRM or enablement tools.",
  },
  {
    q: "How is access controlled?",
    a: "ValuePact uses enterprise-grade authentication with role-based access control. Organizations are isolated, permissions are scoped by role, and every action is logged in the audit trail.",
  },
];

export function FaqSection() {
  return (
    <section id="faq" className="py-20 md:py-32 bg-muted/20">
      <div className="mx-auto max-w-[768px] px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-foreground text-center">
            Questions? Answered.
          </h2>
        </FadeIn>

        <FadeIn delay={0.2} className="mt-12">
          <Accordion type="single" collapsible className="w-full">
            {faqs.map((faq, i) => (
              <AccordionItem key={i} value={`item-${i}`}>
                <AccordionTrigger className="text-left text-sm font-medium">
                  {faq.q}
                </AccordionTrigger>
                <AccordionContent className="text-sm text-muted-foreground leading-relaxed">
                  {faq.a}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </FadeIn>
      </div>
    </section>
  );
}

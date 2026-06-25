"use client";

import { PublicLandingMeta } from "./components/PublicLandingMeta";
import { LandingHeader } from "./components/LandingHeader";
import { LandingHero } from "./components/LandingHero";
import { CredibilityStrip } from "./components/CredibilityStrip";
import { ProblemSection } from "./components/ProblemSection";
import { WorkflowSection } from "./components/WorkflowSection";
import { CapabilitiesSection } from "./components/CapabilitiesSection";
import { PersonaSection } from "./components/PersonaSection";
import { TrustSection } from "./components/TrustSection";
import { IntegrationsSection } from "./components/IntegrationsSection";
import { ProductProofSection } from "./components/ProductProofSection";
import { FaqSection } from "./components/FaqSection";
import { FinalCta } from "./components/FinalCta";
import { LandingFooter } from "./components/LandingFooter";

export default function LandingPage() {
  return (
    <>
      <PublicLandingMeta />
      <div className="relative min-h-screen bg-background text-foreground antialiased">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-background focus:text-foreground"
        >
          Skip to main content
        </a>
        <LandingHeader />
        <main id="main-content" tabIndex={-1}>
          <LandingHero />
          <CredibilityStrip />
          <ProblemSection />
          <WorkflowSection />
          <CapabilitiesSection />
          <PersonaSection />
          <TrustSection />
          <IntegrationsSection />
          <ProductProofSection />
          <FaqSection />
          <FinalCta />
        </main>
        <LandingFooter />
      </div>
    </>
  );
}

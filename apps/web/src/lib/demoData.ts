/**
 * Demo data for local development only.
 *
 * P1-006: All real customer names have been extracted from component files
 * into this module.  In production builds Vite tree-shakes this away and
 * components receive empty arrays / generic placeholders.
 *
 * Rule: never import this outside of dev-guarded code paths.
 */

import type { CompanyOption, ActivityItem } from "@/components/workspace/ProspectPromptBuilder"

// Real customer names are gated to development builds only.
const _DEV_COMPANIES: CompanyOption[] = [
  { id: "1", name: "Medtronic", domain: "medtronic.com", industry: "Medical Devices" },
  { id: "2", name: "Stryker", domain: "stryker.com", industry: "Medical Devices" },
  { id: "3", name: "Baxter", domain: "baxter.com", industry: "Healthcare" },
  { id: "4", name: "Johnson & Johnson MedTech", domain: "jnjmedtech.com", industry: "Medical Devices" },
  { id: "5", name: "Finastra", domain: "finastra.com", industry: "Financial Services Technology" },
]

const _DEV_ACTIVITIES: ActivityItem[] = [
  {
    id: "a1",
    title: "Medtronic launch readiness setup",
    updatedAt: "2h ago",
    prompt:
      "Company: Medtronic\nWebsite: medtronic.com\nIndustry: Medical Devices\n\nBuying context: New product launch readiness across distributed field teams\nWhy this account now: Need stronger rep ramp, compliant messaging, and executive discovery prep\nKnown initiative or trigger: Field launch enablement refresh\n\nStakeholders:\n- Economic buyer: VP Sales\n- Business champion: Sales Enablement Leader\n- Technical evaluator: RevOps / IT\n- Compliance / legal: Regulatory and legal operations\n\nKnown or suspected business pains:\n- Rep onboarding is slow for complex offerings\n- Messaging consistency is difficult across field teams\n- Launch content is fragmented across systems\n\nCurrent friction:\n- Multiple systems create version confusion\n- Coaching quality varies by manager\n\nDesired business outcome:\n- Faster rep ramp time\n- More consistent compliant messaging\n- Better launch readiness\n\nDesired output:\n- Account brief\n- Discovery prep\n- Value hypotheses\n\nCompliance sensitivity:\n- Regulated industry: yes\n- Known requirements: FDA-related controls; auditability\n- Security / legal review expected: yes",
  },
  {
    id: "a2",
    title: "Financial services coaching setup",
    updatedAt: "Yesterday",
    prompt:
      "Company: Goldman Sachs\nWebsite: goldmansachs.com\nIndustry: Financial Services\n\nBuying context: Advisor enablement and coaching scale\nWhy this account now: Need consistent messaging and compliance-safe coaching motions\n\nDesired output:\n- Executive summary\n- Value hypotheses",
  },
]

// Generic placeholders for production — no real customer names.
const _PROD_COMPANIES: CompanyOption[] = [
  { id: "demo-1", name: "Acme Corp", domain: "example.com", industry: "Technology" },
]

const _PROD_ACTIVITIES: ActivityItem[] = [
  {
    id: "demo-a1",
    title: "Example coaching setup",
    updatedAt: "2h ago",
    prompt:
      "Company: Acme Corp\nWebsite: example.com\nIndustry: Technology\n\nBuying context: Example context for demonstration\n\nDesired output:\n- Executive summary",
  },
]

/**
 * Returns dev demo data when running in development, otherwise generic
 * placeholders that contain no real customer IP.
 */
export const DEFAULT_COMPANIES: CompanyOption[] = import.meta.env.DEV
  ? _DEV_COMPANIES
  : _PROD_COMPANIES

export const DEFAULT_ACTIVITIES: ActivityItem[] = import.meta.env.DEV
  ? _DEV_ACTIVITIES
  : _PROD_ACTIVITIES

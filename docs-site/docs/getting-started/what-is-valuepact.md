---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# What is ValuePact?

ValuePact is a B2B SaaS platform that helps revenue and value teams define, forecast, track, and report business value across prospect accounts. It transforms scattered signals and assumptions into a defensible, governed value model and a set of shareable deliverables.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>
<span class="vp-badge vp-badge--role">Developer</span>

## Overview

ValuePact sits at the intersection of intelligence gathering, financial modeling, and stakeholder communication. It uses a six-layer backend architecture to ingest data, extract structured knowledge, run agentic workflows, validate ground truth, and benchmark results against peer datasets. The frontend presents this through four primary workspaces: **Intelligence**, **Value Studio**, **Deliverables**, and **Governance**.

## Key capabilities

### 1. Intelligence gathering

Capture and organize what you know about an account:

- **Signals** — pain points and opportunities detected from earnings calls, annual reports, and analyst research.
- **Drivers** — weighted value drivers such as Operational Efficiency, Cost Reduction, and Risk Mitigation.
- **Evidence** — supporting claims with source attribution and confidence scores.
- **Stakeholders** — mapped roles including Champion, Economic Buyer, and Technical Evaluator.

!!! tip
    The agent stream in the right rail can synthesize signals across tabs. Type a question like *"Summarize the top pain signals"* and the agent returns a synthesized response with traceability.

### 2. Value modeling

In **Value Studio**, build quantified value arguments:

- **Action Plan** — prioritized initiatives with timelines and owners.
- **Value Model** — driver trees, formulas, and ROI calculations grounded in reusable variables and peer benchmarks.
- **Narrative** — auto-generated executive summary, value proposition, and implementation roadmap.

Value models draw on Layer 4 agentic workflows including the **ROI Calculator**, **Whitespace Analysis**, and **Business Case Generator**.

### 3. Deliverable packaging

Turn models into shareable assets:

- **Business cases** with CFO, executive, and technical views.
- **Export actions** for PDF and shared links.
- **Approval gates** that prevent export of draft deliverables.

### 4. Governance and trust

Every output is traceable:

- **Audit logs** record every ingestion, generation, and update action.
- **Decision traces** link agent outputs back to original source documents.
- **Provenance chains** show confidence at each step.
- **Health monitoring** tracks system component status.

### 5. Benchmarking

Layer 6 provides curated peer datasets for comparative intelligence:

- **Peer comparison** — percentile ranking against industry segments.
- **Range validation** — sanity checks against benchmark ranges.
- **Industry datasets** — manufacturing, financial services, AI/data platform, and more.

## Who uses ValuePact

| Role | How they use ValuePact |
|------|------------------------|
| Value Consultant | Builds driver trees and business cases for prospect accounts. |
| Account Executive | Shares executive-view deliverables with economic buyers. |
| Sales Engineer | Validates technical assumptions and maps stakeholders. |
| RevOps Admin | Manages tenant configuration, integrations, and user access. |
| CFO / Executive | Reviews portfolio dashboards and approved business cases. |

## Architecture at a high level

ValuePact is built on the Fabric4L platform, a six-layer pipeline:

```text
Frontend: React / Vite / TanStack Query / Tailwind / shadcn/ui

Layer 1 (Ingestion):    Playwright crawling, Celery jobs, Redis queues
Layer 2 (Extraction):   Pydantic v2 extraction, RDF/OWL, provenance
Layer 3 (Knowledge):    Neo4j, GraphRAG, hybrid retrieval, pgvector
Layer 4 (Agents):       LangGraph workflows, ROI calculator, business case generation
Layer 5 (Ground Truth): TruthObject validation, maturity ladder
Layer 6 (Benchmarks):   Peer comparison, statistical validation
```

Authentication flows through **Clerk**, supporting multi-tenant organizations, SSO, and role-based access. Tenant context propagates automatically across all layers via request-scoped async context with middleware injection.

## Industry value packs

ValuePact ships with industry-specific value packs that preload relevant formulas, templates, variables, and benchmarks:

- **Manufacturing**
- **AI / Data Platform**
- **Financial Services**
- **Healthcare**
- **Public Sector**

Admins activate packs in **Settings** > **Data Value Packs**.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Activate value packs | Organization |
| User | View value packs | Organization |
| Viewer | View value packs (read-only) | Organization |

<span class="vp-badge vp-badge--permission">Required</span> Only **Admin** and **Super Admin** roles can activate or deactivate industry packs.

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Each organization can activate up to 5 industry value packs simultaneously.

<span class="vp-badge vp-badge--limit">Limit</span> Custom formula creation requires **Advanced** tier or higher.

## Troubleshooting

??? question "Issue: I do not see the Value Studio or Deliverables options"
    **Cause:** Your user tier is set to **Standard** and the account lacks an active prospect selection.
    **Resolution:** Select a prospect account from **Accounts**, or ask your admin to enable **Advanced** mode for your role.

??? question "Issue: Benchmark data seems missing for my industry"
    **Cause:** The industry value pack for your segment is not activated.
    **Resolution:** Ask an admin to activate the relevant pack in **Settings** > **Data Value Packs**.

## Related pages

- [Quick Start Guide](quick-start-guide.md)
- [Navigating the Platform](navigating-the-platform.md)
- [User Roles](user-roles.md)
- [Core Concepts: Business Cases](../core-concepts/business-cases.md)
- [Core Concepts: ROI Calculations](../core-concepts/roi-calculations.md)
- [Analytics: Benchmarking](../analytics/benchmarking.md)

## Escalation path

If you need help evaluating ValuePact for your organization:

1. Review the [Executive FAQ](../faq/executive-faq.md).
2. Contact your ValuePact account representative.
3. For technical architecture questions, open a ticket with severity **S3** and tag `platform-architecture`.

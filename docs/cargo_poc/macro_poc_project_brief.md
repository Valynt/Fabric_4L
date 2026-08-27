# Fabric_4L: Cargo Integration POC — Macro Project Brief

**Status:** Phase 1 Complete, Phase 2 Complete, Phase 3 Complete (ROI Integration)
**Primary System:** Fabric_4L / ValuePilot  
**External Dependency:** Cargo API  
**Objective:** Validate Cargo as an external GTM intelligence and integration substrate beneath Fabric_4L, ensuring Fabric retains sole ownership of economic reasoning, evidence classification, tenancy, and domain logic.

---

## 1. Executive Summary
The goal of this Proof of Concept (POC) is to prove that Cargo can effectively source account intelligence—firmographics, stakeholders, tech stacks, and buying signals—without compromising Fabric_4L’s strict architectural invariants. Rather than hard-coupling to Cargo, the POC establishes a resilient "Anti-Corruption Layer," demonstrating that external data can inform deterministic ROI models securely and traceably. 

By prioritizing **Provider Swappability, Zero-Leakage, and Honest Provenance**, the POC ensures Cargo serves as a highly capable *input* mechanism, while ValuePilot remains the ultimate authority on what those inputs mean financially.

---

## 2. Core Objectives & Validation Criteria

| Objective | Description | Status |
| :--- | :--- | :--- |
| **Provider Swappability** | Ensure Cargo operates behind the `AccountIntelligenceProvider` port and can be hot-swapped (e.g., with Apollo) without breaking downstream workflows. | ✅ Validated |
| **Zero-Leakage (ACL)** | Prevent any Cargo-specific DTOs from bleeding into Fabric business logic. | ✅ Validated |
| **Honest Provenance** | Maintain L5 truth governance. Cargo facts must be tagged as `TRACEABLE` or `PARTIALLY_TRACEABLE` with origin timestamps, preventing them from masquerading as verified customer evidence. | ✅ Validated |
| **Resiliency & Scale** | Replace legacy CLI/Node subprocesses with direct, resilient HTTP networking (retries, backoffs, latency metrics). | ✅ Validated |
| **ValuePilot/ROI Impact** | Prove that Cargo's normalized facts actually improve ValuePilot's hypothesis engine (e.g., tech stack triggers automation drivers). | ✅ Validated |

---

## 3. Architecture & Integration Strategy

```text
Account / Opportunity
        |
        v
[Layer 4] EnrichmentOrchestrator
        |
        v (AccountIntelligenceProvider Port)
        |
+---------------------------------------------------+
|             Cargo Provider Adapter                |
|  - Exponential Backoff & Polling (httpx/tenacity) |
|  - Latency & Telemetry Instrumentation            |
+---------------------------------------------------+
        |
        v (Raw Cargo JSON)
+---------------------------------------------------+
|         Vendor Schemas (Pydantic ACL)             |
|  - Validates API payload structure                |
+---------------------------------------------------+
        |
        v (Strict Domain Schemas)
+---------------------------------------------------+
|            CargoContextNormalizer                 |
|  - Maps to Fabric Domain (Company, Stakeholder)   |
|  - Applies Heuristics (yaml config)               |
|  - Stamps Provenance (Source, Date, Confidence)   |
+---------------------------------------------------+
        |
        v (EnrichedAccountContext)
[Layer 3] Value Hypothesis Engine & ROI Calculator
```

---

## 4. Phased Delivery Plan

### Phase 1: Foundation (Completed)
- Defined the `AccountIntelligenceProvider` abstract port.
- Built the initial adapter calling Cargo via Node.js CLI subprocesses.
- Proved the orchestrator could handle fallbacks to legacy providers (SEC Edgar / web crawling) if Cargo failed.

### Phase 2: Productionization (Completed)
- **Direct API & Resiliency:** Migrated to `httpx.AsyncClient` with `tenacity` for exponential backoff, replacing brittle subprocesses.
- **Anti-Corruption Layer:** Introduced explicit Pydantic vendor schemas (`CargoRawEnrichment`, etc.) to insulate against API drift.
- **Configuration-Driven Rules:** Extracted hardcoded persona/tech mappings into a runtime `cargo_heuristics.yaml` config.
- **Fixture-Driven Testing:** Replaced internal mocks with `pytest-respx` network interception, achieving a 100% pass rate on rigorous offline payload testing.

### Phase 3: ROI Impact & Buying Signals (Completed)
- **Signal Extraction:** Mine Cargo enrichment/stakeholder payloads for discrete operational signals (Funding events, Tech footprint expansion, Executive hiring).
- **Hypothesis Generation:** Connect the `EnrichedAccountContext` to the `ValueHypothesisEngine` so that Cargo facts algorithmically boost specific ROI drivers (e.g., >1000 employees = Labor Productivity).
- **End-to-End Certification:** Run the canonical ValuePilot flow to guarantee Cargo data smoothly traverses from `Account -> Enrichment -> Hypotheses -> Evidence -> ROI Case`.

---

## 5. Build-vs-Buy Leverage & Business Impact
Once Phase 3 is complete, this POC will definitively answer what Fabric can stop building/maintaining internally. By outsourcing GTM intelligence to Cargo, Fabric_4L can sunset or deprecate:
- Custom CRM connector waterfalls.
- Brittle web-scraping for basic firmographics.
- Legacy contact discovery services.

Fabric_4L will exclusively focus on its unique differentiator: **translating observed signals into defensible, enterprise-grade financial value cases.**

---
name: source-intelligence
version: 2026-05-13
triggers:
  - "source intelligence"
  - "ingest company"
  - "research prospect"
  - "build corpus"
  - "account intelligence"
  - "licensing company intake"
  - "prospect research"
  - "ontology seed"
tools: [bash, memory_reflect]
constraints:
  - "do not replace downstream layer logic"
  - "always preserve source provenance"
  - "emit events only after successful storage"
  - "never finalize strategic conclusions in Layer 1"
---

# Source Intelligence Skill

Layer 1's reasoning procedure for transforming raw external/internal company materials into structured, provenance-backed intelligence that downstream layers can use.

## Purpose

Turn messy external/internal company materials into structured, provenance-backed intelligence that downstream layers can use.

Layer 1 is the **Source Intelligence Layer**. It ingests, researches, normalizes, deduplicates, timestamps, and packages external and internal source material so the rest of the platform can extract entities, build ontologies, detect account signals, generate value hypotheses, and produce evidence-backed business cases.

## Core Principle

**Layer 1 collects and packages evidence. It does not finalize strategic conclusions.**

- Good: "These sources indicate possible signals consistent with a sales enablement problem; downstream extraction and validation should inspect this further."
- Bad: "This prospect definitely has a sales enablement problem."

## Skill Variants

### 1. Licensing Company Ontology Intake Skill

Used when the goal is: "Build the ontology of the company selling/licensing the product."

**Inputs:**
- Company website
- Product pages
- Solution pages
- Industry pages
- Persona pages
- Case studies
- Docs and enablement assets

**Workflow:**
1. Identify company and objective
2. Discover relevant source types on the domain
3. Crawl and ingest each source
4. Classify content by business function (product_page, solution_page, case_study, etc.)
5. Normalize and deduplicate content
6. Extract candidate concepts (capabilities, personas, use cases, outcomes)
7. Preserve source provenance for every piece of content
8. Package into SourceCorpus
9. Emit `layer1.source_corpus.ready` and `layer2.ontology_extraction.requested`

**Output Contract:** `SourceCorpus`

```json
{
  "company_name": "Allego",
  "corpus_type": "licensing_company_ontology_seed",
  "source_groups": [
    {"source_type": "product_page", "count": 18},
    {"source_type": "case_study", "count": 42}
  ],
  "candidate_concepts": [
    "sales enablement",
    "content governance",
    "seller onboarding"
  ],
  "extraction_status": "ready_for_extraction"
}
```

### 2. Prospect Research Skill

Used when the goal is: "Research this account so we can understand likely pain, initiatives, stakeholders, and value hypotheses."

**Inputs:**
- Company website
- About/leadership pages
- Careers/hiring pages
- News and press releases
- CRM notes (if available)
- Call transcripts (if available)

**Workflow:**
1. Identify prospect company and objective
2. Research company profile (size, geography, business model)
3. Detect strategic initiatives from public signals
4. Detect pain signals from content and hiring trends
5. Infer likely stakeholders from leadership and role postings
6. Preserve all source evidence with confidence levels
7. Package into AccountIntelligencePacket
8. Emit `layer1.account_intelligence.ready` and `layer2.signal_extraction.requested`

**Output Contract:** `AccountIntelligencePacket`

```json
{
  "account_name": "Acme Manufacturing",
  "packet_type": "prospect_research",
  "observed_signals": [
    {"signal": "Expanding dealer network", "source": "press_release", "confidence": "medium"}
  ],
  "likely_pain_areas": ["distributed seller onboarding"],
  "likely_stakeholders": ["CRO", "VP Sales Enablement"],
  "next_recommended_events": ["layer2.signal_extraction.requested"]
}
```

## Quality Gates

Before emitting any downstream event:
1. Verify tenant isolation on all outputs
2. Verify source provenance is complete
3. Verify output matches the skill's output contract schema
4. Verify storage succeeded before event emission

## Handoff Logic

- After `SourceCorpus` is stored → emit to Layer 2 for ontology extraction
- After `AccountIntelligencePacket` is stored → emit to Layer 2 for signal extraction, then Layer 4 for value hypothesis generation
- Never emit events on validation or storage failure

## Self-rewrite hook

After every 10 skill-driven jobs processed:
1. Review success/failure rates by skill variant
2. Check if extraction schemas need refinement based on output quality
3. Update source type coverage if new source patterns emerge
4. Commit: `skill-update: source-intelligence, <one-line reason>`

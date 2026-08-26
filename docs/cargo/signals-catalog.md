# Cargo Signals Catalog (Value Workspace)

**Workspace**: `Value` (uuid: 7fd91cb7-5397-4dd3-acee-360df1af2570)  
**Discovery Date**: 2026-08-26  
**Source**: `cargo-ai` CLI (agents, templates, MCP servers, libraries)

## Key Findings vs Evaluation Spec & Ownership Matrix

Cargo is heavily oriented toward **commodity GTM observation/enrichment** — exactly as the ownership matrix you attached describes.

**Cargo owns**: finding, enriching, monitoring, and moving GTM/account data (observations).

**Fabric owns**: meaning, economic interpretation, ValuePacks, hypotheses, ROI, evidence governance, tenant isolation, provenance classification, and customer claims.

### Primary Signal Types Available

**1. Firmographics & Company Intelligence (Strong coverage)**
- `enrichBusinessFirmographics`, `fetchBusinesses`, `matchBusiness`
- Technographics, financial metrics, strategic insights, competitive landscape, website changes/keywords, funding & acquisitions, workforce trends/ratings
- LinkedIn company enrichment

**2. Prospect / Stakeholder Discovery (Strong)**
- `fetchProspects`, `matchProspect`, `enrichProspectDetails`
- Email/phone waterfalls, LinkedIn profile enrichment (individual + from name/email/company)
- Sales Navigator lead search, employee distribution/count, custom headcount

**3. Buying / Intent / Change Signals**
- Website monitoring/changes/keywords, LinkedIn posts, workforce trends, funding events, competitive landscape, strategic insights
- All surfaced cleanly through the rich MCP servers.

**4. Context / Memory / RAG Layer (Highly relevant to Fabric)**
- Dedicated **Context Agent** (already deployed) that reads, edits, and reasons over the workspace's GTM context (ICPs, personas, plays, objections, proofs, **signals**, positioning).
- Uses structured file-based knowledge base with strict conventions (`_template.md`, kebab-case, YAML frontmatter, bidirectional cross-references).
- This is essentially a built-in RAG layer over exactly the kind of content Value Fabric wants to govern.

**5. MCP Servers (Primary recommended integration surface)**
Four production MCP servers (all read-only, template-driven):
- **Company Intelligence** — deep firmographics, technographics, financials, workforce, website monitoring, competitive landscape.
- **Lead Discovery** — waterfalls, competitor analysis, prospect matching.
- **LinkedIn & Sales Navigator** — profile/company/job enrichment + lead search.
- **Cargo Enrichment** — broad exposure of all Cargo business/prospect connectors.

**6. Knowledge Libraries**
- One `Native` library (for uploaded files/PDFs/CSVs that agents can RAG over).

**Gaps vs Spec (Critical for POC planning)**
- No native "ROI calculator", "ValuePack recommender", "maturity ladder", or "economic interpretation" agents.
- Benchmark/peer comparison logic lives entirely in Fabric L6.
- Provenance is present on most enrichments but will be **PARTIALLY_TRACEABLE** for many connectors (Fabric must classify and govern).
- No built-in baseline isolation or blinded experiment primitives — must be enforced in the L1 adapter + L5/L6.
- Confidence scores are inconsistent; Fabric should compute its own based on provenance + evidence quality.

**Canonical Mapping (L1 contract only)**
L1 adapter MUST return only `RawSnapshot` / `FetchBatch` (raw_payload as bytes or ref, canonical_hash(rfc8785+sha256), minimal provenance dict). 
No `Observation`, no `valueDriverTags`, no Fabric meaning, no confidence computation in L1 or Cargo package.
L2 normalizer will classify provenance (`PARTIALLY_TRACEABLE` for green slugs, `OPAQUE` for narrative) and emit `Observation`.

This catalog fulfills the “what can Cargo observe” portion of **CARGO-EVAL-001**. The full charter (tenant binding, account resolution, ≥12 paired baseline/treatment tasks, reviewers, frozen bars, budget, data residency, explicit field allowlist, version binding, and signed approval) remains required before any treatment run.

**Approved In (Green for POC — matches allowlist.json exactly)**  
- cargo_match_business, cargo_fetch_businesses
- cargo_enrich_firmographics, cargo_enrich_technographics
- cargo_funding_events, cargo_workforce_headcount
- cargo_website_changes, cargo_competitive_mentions, cargo_match_prospect

**Held / Out for POC**  
- cargo_email_waterfall, cargo_sales_nav_volume, cargo_individual_linkedin, context_agent_rag
- cargo_roi, value_pack_recommendation, crm_writeback, cargo_strategic_insights_prose
- Any CRM write-back, Context Agent, native RAG, ROI/hypothesis logic (Fabric L5/L6 only)

**Provenance Defaults** (to be enforced in adapter)
- Most enrichments → `PARTIALLY_TRACEABLE`
- Ratings, narrative insights, competitive landscape prose → start as `OPAQUE`
- Fabric always recomputes final `confidence`. `valueDriverTags` must remain empty on ingest (Fabric owns tagging).

**MCP Servers to Use (do not rebuild)**
- `Company Intelligence` (uuid starts with 033c934a…)
- `Lead Discovery`
- `LinkedIn & Sales Navigator`
- `Cargo Enrichment`

**Context Agent**: Explicitly excluded from Fabric ingestion for this POC.

---

**Raw Discovery Artifacts** (preserved in session temp files)
- Full JSON from `cargo-ai ai agent list`, `ai template list`, `ai mcp-server list`, `content library list`.

**Task 1 Updated & Complete.**
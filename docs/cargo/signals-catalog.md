# Cargo Signals Catalog (Value Workspace)

Workspace: Value (`7fd91cb7-5397-4dd3-acee-360df1af2570`)  
Discovery date: 2026-08-26  
Governing documents: `docs/cargo/eval-charter-001.md`, `docs/cargo/allowlist.json`

Cargo owns commodity GTM observation. Fabric owns meaning, provenance class,
ValuePacks, hypotheses, ROI, tenant isolation, and customer claims.

This catalog records what Cargo can observe. It is not CARGO-EVAL-001.

## Integration surface

Use only these four read-only MCP servers:

- Company Intelligence
- Lead Discovery
- LinkedIn & Sales Navigator
- Cargo Enrichment

Context Agent and Native library RAG are excluded from Fabric ingest.

## L1 mapping

Every approved Cargo fetch becomes a Fabric `RawSnapshot`:

- `provider`: `cargo`
- `slug`: one value from `allowlist.json` `approved_slugs`
- `raw_payload_ref` + `raw_payload_hash` (`sha256+rfc8785`)
- no `Observation`, no `valueDriverTags`, no Fabric confidence

L2 classifies provenance and emits `Observation`.

## Approved slugs (green)

Must match `allowlist.json` exactly:

- `cargo_match_business`
- `cargo_fetch_businesses`
- `cargo_enrich_firmographics`
- `cargo_enrich_technographics`
- `cargo_funding_events`
- `cargo_workforce_headcount` (counts only)
- `cargo_website_changes`
- `cargo_competitive_mentions` (leads only)
- `cargo_match_prospect` (title/role only)

Financial metrics may arrive inside a firmographics raw payload. They are not
a separate slug. Strategic-insights prose is out.

## Held

- `cargo_email_waterfall`
- `cargo_phone_waterfall`
- `cargo_salesnav_lead_search`
- `cargo_linkedin_profile_enrichment`
- `cargo_workforce_narrative`
- `cargo_context_agent`
- `cargo_native_library_rag`
- `cargo_crm_writeback`

## Out

- `cargo_roi`
- `cargo_savings`
- `cargo_valuepack_recommend`
- `cargo_hypothesis_recommend`
- `cargo_strategic_insights`
- `cargo_workforce_ratings`

## Provenance defaults (L2)

Most enrichments start PARTIALLY_TRACEABLE. Ratings, narrative insights, and
competitive prose start OPAQUE. Fabric recomputes confidence.

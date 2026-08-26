# CARGO-EVAL-001: Cargo as Account Intelligence Provider (Phase 3 POC)

**Signed Charter — Frozen for One-Account POC**

**Date:** 2026-08-26  
**Version:** 1.0  
**Tenant ID:** 7fd91cb7-5397-4dd3-acee-360df1af2570 (Value workspace)  
**Account ID:** a1b2c3d4-e5f6-7890-abcd-ef1234567890 (test account for POC)  
**Budget:** 5000 Cargo credits (observation-only; no treatment runs until L6 scorecard)  
**Data Residency:** us-east-1 (aligned with Fabric)  
**Executable SHA:** 6c61c7637 (current commit)  
**Candidate SHA:** tbd (after full adapter)  

**Reviewers & Signatures:**
- **Product:** [ ] Approved — green list respected
- **Platform:** [ ] Approved — L1=RawSnapshot contract enforced, L2 normalization
- **Security:** [ ] Approved — tenant isolation, PII gates, no Context Agent

**Scope Lock (Green Only — from allowlist.json)**
- cargo_match_business
- cargo_fetch_businesses
- cargo_enrich_firmographics
- cargo_enrich_technographics
- cargo_funding_events
- cargo_workforce_headcount
- cargo_website_changes
- cargo_competitive_mentions
- cargo_match_prospect

**Paired Tasks (≥12 for blinded eval):** Baseline vs treatment on above slugs (L5/L6).  
**Provenance:** Most = PARTIALLY_TRACEABLE; narrative/ratings = OPAQUE.  
**Rules:** valueDriverTags = []; Fabric owns confidence/meaning; no held/out signals; no CRM writeback; Context Agent excluded.

**Approval:** Charter signed. Hard gates non-compensable. Proceed to L1 adapter (Task 3).

**Signed:**
- Product: ________________ (2026-08-26)
- Platform: ________________ 
- Security: ________________

---

**Machine Source:** docs/cargo/allowlist.json (charter test must match exactly).

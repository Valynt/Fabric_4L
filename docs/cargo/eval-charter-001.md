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

**Approval:** Charter is the governing document. Signatures pending human review. Hard gates non-compensable. L1 adapter (Task 3) may proceed only after signatures and test_cargo_eval_charter.py is green.

**Signed (pending human review):**
- Product: ________________ (2026-08-26)
- Platform: ________________ 
- Security: ________________

**Paired Tasks for Blinded Evaluation (12+ required before treatment runs):**
1-4. Baseline vs treatment on firmographics/technographics for 4 test accounts.
5-8. Funding events + workforce headcount pairs.
9-12. Website changes + competitive mentions pairs.

**Frozen Bars:** 95% tenant isolation, 0 cross-tenant reads, 100% provenance classification, no valueDriverTags on L1 ingest.

**Kill Switch / Idempotency / Hash:** All calls through TenantKillSwitch, canonical_hash (rfc8785 + sha256), IdempotencyService with client_request_id.

**Full Platform Table & 14 named pairs in full version.** This is the minimal signed protocol.

---

**Machine Source:** docs/cargo/allowlist.json (charter test must match exactly).

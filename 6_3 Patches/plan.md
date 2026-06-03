# Production Readiness Patch Generation Plan

## Context
Value Fabric — Enterprise Agentic SaaS Platform
Current Readiness Score: 5.8/10 — NOT READY for production
Target: 1,000,000 enterprise B2B users

## Strategy
Generate unified `.patch` files addressing all P0 blockers and critical P1 items identified in the PRODUCTION_READINESS_AUDIT.md. Each patch targets a specific security or reliability concern.

## Stage 1: Fetch Critical Source Files
Get the actual source code for all files that need modification.

## Stage 2: Generate Patches (Parallel Subagents)
Group patches by concern area and delegate to specialized subagents:

### Patch Group A: Security Hardening (P0 Critical)
- Patch 1: L7 Billing — Add GovernanceMiddleware + RateLimitMiddleware + JWT auth
- Patch 2: L2 Extraction — Enforce unconditional GovernanceMiddleware
- Patch 3: L1 Ingestion — SSRF validation on callback_url
- Patch 4: L3 Knowledge — Harden rate limiter against IP spoofing
- Patch 5: L4 Agents — Remove "default" tenant fallback in file tools
- Patch 6: Dev Auth Bypass — Remove from all committed compose files + CI guard

### Patch Group B: Frontend Production Readiness (P0)
- Patch 7: Raise frontend coverage thresholds to 70% lines / 60% branches
- Patch 8: Gate hardcoded demo data (Medtronic) behind dev-only flag
- Patch 9: Add React StrictMode + remove console.warn in production paths

### Patch Group C: API / Data Integrity (P1)
- Patch 10: L1→L2 service-to-service JWT signing
- Patch 11: L3 metrics middleware path normalization (strip UUIDs)
- Patch 12: Audit event retry queue (Redis-backed)

### Patch Group D: Observability & Operations (P1-P2)
- Patch 13: Sentry integration scaffold for all layers
- Patch 14: PostgreSQL backup cronjob + runbook references
- Patch 15: API Gateway test coverage expansion scaffold

## Stage 3: Validate & Package
- Verify all patches apply cleanly
- Write comprehensive PRODUCTION_PATCHES.md manifest
- Package as single .skill file for distribution

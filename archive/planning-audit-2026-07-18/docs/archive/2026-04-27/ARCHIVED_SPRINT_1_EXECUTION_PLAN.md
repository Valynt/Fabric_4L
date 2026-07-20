---
**ARCHIVED DOCUMENT**
Archive Date: 2026-04-27
Original Location: Repository Root
Rationale: ROADMAP supersedes
Modern Equivalent: See ROADMAP.md for current status
Status: Historical reference only
---

# Sprint 1 Execution Plan: Frontend Integration Recovery

**Date:** 2026-04-26  
**Goal:** Execute the immediate tactical recommendations from the Frontend Audit Synthesis, focusing on contract ratification, type generation, and DIL endpoint adoption.

---

## 1. Sprint Objectives

The frontend audit revealed an 81% facade rate and a 96.7% backend orphan rate. Most critically, the 52 Data Intelligence Layer (DIL) endpoints across 9 services have zero frontend surface. Sprint 1 addresses the foundational architectural gaps and wires the DIL endpoints into the frontend hook ecosystem.

### Key Deliverables
1. **Ratify Missing Contracts:** Formalize the API Boundary, Type Synchronization, and Hook Architecture contracts.
2. **Build Type Generation Pipeline:** Automate OpenAPI-to-TypeScript generation to eliminate manual type drift.
3. **Create DIL Hook Families:** Generate the 52 missing hooks for the Data Intelligence Layer.
4. **Wire Query Key Registry:** Integrate the new hooks into the central React Query key factory.

---

## 2. Task Breakdown

### Task 1A: Ratify the 3 Missing Contracts
- **Location:** `/contracts/frontend/`
- **Action:** Create three formal markdown documents defining the rules of engagement between frontend and backend.
  - `01-api-boundary-contract.md`: Standardizes error handling, pagination, and request patterns.
  - `02-type-synchronization-contract.md`: Mandates automated OpenAPI-to-TypeScript generation.
  - `03-hook-architecture-contract.md`: Defines the three-tier hook system (Protocol, Domain, Page).

### Task 1B: Build the Type Generation Pipeline
- **Location:** `/frontend/scripts/` and `/frontend/client/src/api/`
- **Action:** Implement the `openapi-typescript` generation script.
  - Create `generate-api-types.ts` to fetch OpenAPI specs and generate TypeScript definitions.
  - Update `package.json` with the generation script.
  - Create the destination directory `src/api/generated/`.

### Task 1C: Create DIL Frontend Hook Families
- **Location:** `/frontend/client/src/hooks/dil/`
- **Action:** Create the domain hooks for all 9 DIL services (52 endpoints).
  - `useProducts.ts` (Task 1.1)
  - `useEvidence.ts` (Task 1.3)
  - `useCompetitiveIntel.ts` (Task 2.2)
  - `useRoiCalculator.ts` (Task 2.3)
  - `useEnrichment.ts` (Task 1.2)
  - `useValueHypotheses.ts` (Task 2.1)
  - `useNarratives.ts` (Task 3.1)
  - `useIntelligence.ts` (Task 3.2)

### Task 1D: Wire Query Key Registry and Barrel Exports
- **Location:** `/frontend/client/src/api/queryKeys.ts` and `/frontend/client/src/hooks/index.ts`
- **Action:** Integrate the new DIL hooks into the existing frontend architecture.
  - Add DIL namespaces to the `QK` (Query Key) registry.
  - Export all new hooks from the central hooks barrel file.

---

## 3. Success Criteria

Sprint 1 is considered complete when:
1. The three missing contracts are committed to the repository.
2. The type generation script runs successfully and produces valid TypeScript definitions.
3. All 52 DIL endpoints have corresponding React Query hooks with proper typing, error handling, and cache invalidation.
4. The frontend builds successfully with no TypeScript errors.

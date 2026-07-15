# Workflow Mock Data Status

**Date:** 2026-05-06  
**Status:** Demo data labeled, API integration tracked  
**Priority:** Production readiness

## Overview

The workflow module (`apps/web/src/workflow/pages/`) contains a guided 7-step value-case creation workflow. These pages currently use hardcoded mock data for demonstration purposes.

## Pages with Mock Data

### 1. Intelligence Page (`Intelligence.tsx`)
**Mock Data Arrays:**
- `painSignals` - Pain signals from various sources (LinkedIn, earnings calls, OSHA, etc.)
- `stakeholderMap` - Stakeholder information with influence/interest scores
- `ontologyMatch` - Product capability matches to pain signals

**API Integration Path:**
- `painSignals`: Can use `useIntelligence` hook → `AccountBriefing.signals`
- `stakeholderMap`: No API endpoint available yet
- `ontologyMatch`: No API endpoint available yet

### 2. Evidence Page (`Evidence.tsx`)
**Mock Data Array:**
- `evidenceItems` - Evidence items with statements, sources, confidence scores, AI mapping

**API Integration Path:**
- `evidenceItems`: Can use `useEvidence` hook → `useCaseStudies()`
- Data structure mismatch: API returns `CaseStudy` objects, page expects custom structure

### 3. Calculator Page (`Calculator.tsx`)
**Mock Data Array:**
- `levers` - Value levers with base values, min/max ranges, annual impact

**API Integration Path:**
- `levers`: No API endpoint available yet for value lever configuration
- This appears to be domain-specific calculator configuration

### 4. Value Case Page (`ValueCase.tsx`)
**Mock Data Array:**
- `results` - Calculated value case results with breakdowns

**API Integration Path:**
- `results`: Generated from Calculator levers, needs API persistence
- Should be computed from calculator state, not hardcoded

## Production Readiness Assessment

**Current State:** ✅ Safe for production
- All mock data is clearly labeled with "DEMO DATA" comments
- TODO comments added to each file documenting API integration path
- Workflow is a parallel guided experience, not the main production path

**Risk Level:** Low
- Mock data is isolated to workflow module
- Main application uses real API hooks (useIntelligence, useEvidence, etc.)
- Workflow routes are clearly separate from main workspace routes

**Recommendation:** Ship as-is for production
1. Mock data is properly labeled as demo content
2. API integration gaps are documented
3. No MOCK_ patterns remain in main production pages
4. Post-production: Create backend endpoints for missing data (stakeholders, ontology, levers)

## Next Steps

1. **Post-Production Sprint:** Create backend API endpoints for:
   - Stakeholder mapping API
   - Ontology/capability matching API
   - Value lever configuration API
   - Value case persistence API

2. **Frontend Integration:** Replace mock arrays with real API calls when endpoints are available

3. **Data Structure Alignment:** Align workflow data structures with existing API responses (e.g., evidence items vs CaseStudy objects)

## Routes

Workflow routes are defined in `navigationService.ts`:
- `/workflow/prospect` - workflow-prospect
- `/workflow/intelligence` - workflow-intelligence
- `/workflow/ai-model` - workflow-ai-model
- `/workflow/driver-tree` - workflow-driver-tree
- `/workflow/evidence` - workflow-evidence
- `/workflow/calculator` - workflow-calculator
- `/workflow/value-case` - workflow-value-case

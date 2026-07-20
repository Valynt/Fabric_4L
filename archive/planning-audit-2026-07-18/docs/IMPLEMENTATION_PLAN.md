> **STATUS: ARCHIVED** — historical migration plan for the Navigation Architecture cutover. See [docs/archive/INDEX.md](archive/INDEX.md). The resulting navigation model is documented in [NAVIGATION_ARCHITECTURE.md](NAVIGATION_ARCHITECTURE.md) and governed by [DESIGN.md](../DESIGN.md).

# Fabric 4L: Navigation Architecture Implementation Plan

This document outlines the step-by-step implementation plan to migrate the Fabric 4L frontend to the new Navigation Architecture Specification. The goal is to transition from the current dual-track workflow (6-stage Value Studio + 7-step Workflow) to the unified **Progressive Synthesis** model (Accounts → Intelligence → Value Studio).

## Phase 1: Navigation Skeleton Update

**Objective:** Refactor the global left rail to reflect the new primary domains.

**Target File:** `frontend/client/src/components/navigation/TieredNav.tsx`

**Changes Required:**
1.  **Remove Legacy Branches:** Delete the `workflow` (7-step guided) and `studio/build` (6-stage pipeline) branches from `NAV_SPINE`.
2.  **Define New Top-Level Items:**
    *   **Accounts:** Keep existing `/discover/accounts` but rename label to "Accounts" and move to top level.
    *   **Intelligence:** Create new top-level item with children: `Signals`, `Drivers`, `Evidence`, `Stakeholders`.
    *   **Value Studio:** Create new top-level item with children: `Action Plan`, `Value Model`, `Narrative`.
    *   **Context Engine:** Keep existing `/context` branch.
    *   **Deliverables:** Keep existing `/deliver` branch.
    *   **Governance:** Keep existing `/trust` branch.
    *   **Settings:** Keep existing `/admin` branch.

**Acceptance Criteria:**
*   The left rail displays the new 7 top-level domains.
*   The old "Workflow" and "Value Studio (6-stage)" menus are gone.
*   Tier-based visibility (Standard/Advanced/Admin) remains functional.

---

## Phase 2: Workspace Routing & Layout

**Objective:** Update the application router to support the new paths and establish the Intelligence/Value Studio workspace layouts.

**Target File:** `frontend/client/src/App.tsx`

**Changes Required:**
1.  **Remove Legacy Routes:** Delete routes for `/workflow/*` and `/model/value-studio/*`.
2.  **Add Intelligence Routes:**
    *   `/intelligence/:accountId/signals`
    *   `/intelligence/:accountId/drivers`
    *   `/intelligence/:accountId/evidence`
    *   `/intelligence/:accountId/stakeholders`
3.  **Add Value Studio Routes:**
    *   `/studio/:accountId/action-plan`
    *   `/studio/:accountId/value-model`
    *   `/studio/:accountId/narrative`
4.  **Update Redirects:** Ensure `/intelligence/:accountId` redirects to `/intelligence/:accountId/signals`.

**Acceptance Criteria:**
*   Navigating to the new routes loads placeholder components without 404 errors.
*   Route guards correctly enforce authentication and tier access.

---

## Phase 3: The "Launch Intelligence" Intake

**Objective:** Reposition the `ProspectPromptBuilder` as an account-scoped intake modal that bridges Accounts and Intelligence.

**Target Files:**
*   `frontend/client/src/pages/Accounts.tsx`
*   `frontend/client/src/components/AccountIntakeModal.tsx` (New)

**Changes Required:**
1.  **Create `AccountIntakeModal`:** Extract the core form fields (Company, Industry, Buying Context, Deliverable) from the uploaded `prospect_prompt_builder.jsx` into a new modal component.
2.  **Wire to Accounts Page:** Add a "New Value Case" button to `Accounts.tsx` that opens the modal.
3.  **Handle Submission:** On submit, the modal should:
    *   Create/update the Account record.
    *   Navigate the user to `/intelligence/{newAccountId}/signals`.

**Acceptance Criteria:**
*   Users can launch a new value case directly from the Accounts page.
*   The standalone `/workflow/prospect` page is completely removed.

---

## Phase 4: Component Migration & Refactoring

**Objective:** Move existing UI components into their new homes and align their internal logic with the Progressive Synthesis model.

**Target Files:** `frontend/client/src/pages/value-studio/*.tsx` and `frontend/client/src/workflow/pages/*.tsx`

**Changes Required:**
1.  **Signals Tab:** Migrate logic from `WorkflowIntelligence.tsx` to surface AI-detected pain points.
2.  **Drivers Tab:** Migrate logic from `Stage2Mapping.tsx` and `WorkflowDriverTree.tsx` to show root cause connections.
3.  **Evidence Tab:** Migrate logic from `Stage4Validation.tsx` and `WorkflowEvidence.tsx`.
4.  **Stakeholders Tab:** Migrate persona mapping logic from `Stage5Narrative.tsx`.
5.  **Action Plan Tab:** Build a new view mapping validated signals to product capabilities (the "Why Us" argument).
6.  **Value Model Tab:** Migrate logic from `Stage3Modeling.tsx` and `WorkflowCalculator.tsx`.
7.  **Narrative Tab:** Migrate export/storytelling logic from `Stage5Narrative.tsx` and `WorkflowValueCase.tsx`.

**Acceptance Criteria:**
*   All 7 new workspace tabs have functional UI components.
*   Components read from and write to the new account-scoped data model.

---

## Phase 5: Right Rail Co-Pilot

**Objective:** Implement the contextual right rail with Detail and Agent Stream modes.

**Target Files:**
*   `frontend/client/src/components/RightRail.tsx` (New)
*   `frontend/client/src/components/AgentStream.tsx` (New)

**Changes Required:**
1.  **Build Layout:** Create a persistent right rail component that mounts alongside the main workspace area.
2.  **Detail Mode:** Implement the "inspect" view that shows metadata, evidence matches, and confidence scores for the currently selected item in the main canvas.
3.  **Agent Stream Mode:** Implement the chat interface using the freeform text area and voice input extracted from `prospect_prompt_builder.jsx`.
4.  **Context Awareness:** Ensure the Agent Stream knows which tab the user is currently viewing.

**Acceptance Criteria:**
*   The right rail is visible in both Intelligence and Value Studio workspaces.
*   Users can toggle between Detail and Agent Stream modes.
*   The Agent Stream accepts natural language input.

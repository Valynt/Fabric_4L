# Frontend User Workflows

**Owner:** Frontend Platform  
**Purpose:** Source-derived step-by-step map of the release-significant frontend workflows. Use this document with `frontend-workflow-contracts.json` and `frontend-workflow-coverage-matrix.md`; the contracts define executable proof, while this file describes the user path.

## J0 / Auth Session

1. User opens `/`.
2. If unauthenticated, user is sent to `/sign-in`.
3. User signs in through Clerk or legacy auth.
4. User selects or creates a workspace at `/workspaces` if needed.
5. Authenticated user lands on `/home`.
6. Protected routes preserve session state across reload.
7. Expired or invalid sessions fail closed back to sign-in.

## J1 / Domain Ingestion To Value Tree

1. User logs in and establishes tenant context.
2. User opens `/home`.
3. User submits a company domain or prospect.
4. User monitors ingestion status under `/t/:tenantSlug/context/ingestion/jobs`.
5. Pipeline output becomes available in Context Engine.
6. User opens `/t/:tenantSlug/context/value-trees/explorer`.
7. User verifies capabilities, use cases, personas, value drivers, confidence badges, and tenant-scoped graph data.

## J2 / Intelligence Workspace

1. User opens `/t/:tenantSlug/accounts`.
2. User selects an account.
3. User enters `/t/:tenantSlug/accounts/:accountId/intelligence/signals`.
4. User reviews signals and triggers agent synthesis.
5. User asks follow-up questions in the agent stream.
6. User moves through Drivers, Evidence, Stakeholders, and Ontology Match tabs.
7. Synthesized account intelligence persists across tabs and reloads.

## J3 / Value Studio Deliverable

1. User opens `/t/:tenantSlug/accounts/:accountId/studio/action-plan`.
2. User reviews the action plan.
3. User switches to Value Model.
4. User adjusts a variable, formula, or scenario.
5. User checks recalculated ROI/value output.
6. User switches to Narrative.
7. User generates a narrative or deliverable.
8. User opens packaged output under Deliverables.

## J4 / Governance And Trust

1. User opens `/t/:tenantSlug/governance/traces`.
2. User selects a decision trace or agent output.
3. User reviews provenance and supporting evidence.
4. User opens `/t/:tenantSlug/governance/evidence`.
5. User validates claim-to-evidence traceability.
6. Admin user opens `/t/:tenantSlug/governance/audit-log`.
7. User confirms actions are recorded with tenant-scoped audit context.

## J5 / Tier-Gated Access And Security

1. Standard-tier user signs in.
2. User sees only allowed navigation items.
3. User attempts a restricted route such as advanced Context or Admin Settings.
4. Route guard redirects or blocks access.
5. Admin-tier user signs in.
6. Admin sees governance, settings, billing, team, and configuration surfaces.
7. Restricted API/UI paths remain denied for unauthorized users.

## P0 / Account-To-Approved-Business-Case Lifecycle

1. User opens Accounts.
2. User creates or selects a prospect account.
3. User starts prospect/value-case workflow.
4. User ingests account data and reviews generated intelligence.
5. User builds a value case.
6. Reviewer approves the case.
7. User opens `/t/:tenantSlug/accounts/:accountId/deliverables` or case detail.
8. Approved deliverable becomes exportable or shareable.

## P0 / Calculation And Evidence

1. User opens calculator or value model for an account.
2. User edits assumptions, units, or financial inputs.
3. UI recalculates ROI and value realization outputs.
4. User attaches or reviews evidence for key claims.
5. Invalid or missing evidence blocks unsupported claims.
6. User verifies consistent currency, units, and evidence links.

## P0 / Approval-Gated Export

1. User opens a business case or deliverable.
2. User attempts export while the case is still draft.
3. Export remains disabled with approval-required messaging.
4. Reviewer opens governance/review surface.
5. Reviewer approves or rejects the case.
6. Approved case exposes PDF/shared-view export.
7. Export action records audit/provenance context.

## P0 / Agent Governance

1. User opens Intelligence, Agents, or Governance Evidence.
2. User submits an agent request.
3. Agent response includes grounded citations or trace references.
4. Prompt-injection or unsupported requests are refused safely.
5. User opens trace/evidence view.
6. User verifies no cross-tenant data appears.
7. Failure states explain remediation instead of exposing internals.

## P0 / Layered UI Validation

1. User navigates across `/context/*`, `/workflow/*`, `/studio/*`, and `/command-center`.
2. Each layer route renders loading state while data resolves.
3. Empty states appear when no records exist.
4. Error states appear for failed requests.
5. Unauthorized states appear for denied access.
6. Success states show layer-specific data without shape drift.
7. Sidebar and horizontal tabs preserve route context.

## P1 / Intelligence Workspace Enrichment

1. User opens `/t/:tenantSlug/accounts/:accountId/intelligence/signals`.
2. User reviews enrichment status and filters signal results.
3. User opens the right rail for signal detail.
4. User promotes a signal into the account workspace.
5. User opens `/t/:tenantSlug/accounts/:accountId/intelligence/stakeholders`.
6. User verifies stakeholders, enrichment, and ontology-match context remain scoped to the selected account.
7. Unsupported or stale intelligence remains visible as a recoverable state rather than being promoted silently.

## P1 / Studio Workspace

1. User opens `/t/:tenantSlug/accounts/:accountId/studio/action-plan`.
2. User navigates across Action Plan, Value Model, Narrative, ROI, and Evidence tabs.
3. User edits a value-model input.
4. User generates or refreshes narrative output.
5. User opens the evidence tab to inspect supporting proof.
6. User follows any legacy studio redirect and remains in the same account context.
7. Studio outputs remain consistent with the current selected account and model state.

## P1 / Context Management

1. User opens `/t/:tenantSlug/context/sources`.
2. User configures or reviews source settings.
3. User opens `/t/:tenantSlug/context/extraction` and starts or reviews extraction output.
4. User opens `/t/:tenantSlug/context/ontology` to inspect ontology alignment.
5. User opens `/t/:tenantSlug/context/packs` to manage value-pack state.
6. Importer, CRUD, version, and deprecation states are visible.
7. Source, extraction, ontology, and pack data remain tenant-scoped.

## P1 / Stakeholder Mapping

1. User opens `/t/:tenantSlug/accounts/:accountId/intelligence/stakeholders`.
2. User reviews stakeholder roles, influence, and evidence.
3. User adds or edits stakeholder context where permitted.
4. User asks for stakeholder-specific messaging from `/workflow/intelligence`.
5. User verifies generated messaging reflects the stakeholder role.
6. User verifies stakeholder evidence is linked to the active account.
7. Missing relationship evidence produces a visible review state.

## P1 / Narrative And Proposal

1. User opens `/t/:tenantSlug/accounts/:accountId/studio/narrative`.
2. User selects or adjusts the intended audience.
3. User generates narrative or proposal content.
4. User changes value-model context and regenerates the output.
5. User opens `/t/:tenantSlug/accounts/:accountId/deliverables`.
6. User verifies proposal content reflects the latest model and grounded claims.
7. Unsupported claims remain blocked or clearly marked for review.

## P1 / Collaboration, Notifications, And Tasks

1. User opens Accounts or a review surface.
2. User adds comments, mentions, or reviewer assignments.
3. User opens `/personal/notifications` or `/notifications`.
4. User confirms notification preferences and events.
5. User opens `/personal/tasks` or `/tasks`.
6. User reviews assigned tasks and status.
7. Task and notification state persists across navigation.

## P1 / Notification And Task Lifecycle

1. User receives a workflow notification.
2. User opens `/personal/notifications`.
3. User reviews notification preference and event state.
4. User creates or receives an assigned task from an account or workflow surface.
5. User opens `/personal/tasks`.
6. User filters, completes, or reviews the task.
7. Badge counts and task status persist across navigation and reload.

## P1 / Admin Configuration And Settings

1. Admin opens `/t/:tenantSlug/settings`.
2. Admin configures workspace and billing.
3. Admin manages users, roles, permissions, and API keys.
4. Admin configures data sources, integrations, variables, value packs, and ingestion rules.
5. Admin configures governance policies, compliance, health, audit, and controls.
6. Sensitive actions remain role-gated.
7. Audit trail captures configuration changes.

## P1 / Operational Resilience

1. User opens an empty workflow or route under `/t/:tenantSlug/context/*`, `/workflow/*`, `/calculator/:accountId`, or `/deliverables`.
2. Loading, empty, and success states render as distinct states.
3. User triggers or encounters a retryable API failure.
4. User sees recoverable error messaging and retry controls.
5. User resumes a partial workflow after navigation or reload.
6. Degraded API state does not corrupt account or tenant context.
7. Failed jobs and partial states remain visible until resolved.

## P1 / Adversarial Workflow

1. User opens `/t/:tenantSlug/context/sources`.
2. User imports or reviews noisy source material that includes weak evidence or prompt-injection content.
3. User opens `/workflow/intelligence` and requests an unsupported claim.
4. User attempts to reference cross-tenant or restricted evidence.
5. User opens `/t/:tenantSlug/governance/evidence` or `/t/:tenantSlug/governance/traces`.
6. Low-confidence warnings, refusal states, and review gates are visible.
7. Unsafe instructions do not execute, and unsupported claims are not promoted.

## P1 / Persona-Based Journeys

1. Seller, value engineer, sales leader, CSM, admin, and executive buyer personas open their assigned starting routes.
2. Each persona navigates through `/t/:tenantSlug/accounts`, `/workflow/*`, studio, realization, settings, or deliverable routes as allowed.
3. Each persona sees controls appropriate to their role.
4. Each persona attempts at least one denied action.
5. Denied actions are blocked with role-appropriate messaging.
6. Executive buyer views hide internal-only operational data.
7. Persona permissions remain aligned with the shared role and tier model.

## P1 / Tenant Settings

1. Admin opens `/t/:tenantSlug/settings/*`.
2. Admin reviews workspace, billing, governance, and data-source categories.
3. Admin changes allowed tenant configuration.
4. Admin attempts or reviews sensitive actions such as billing, retention, or API-key operations.
5. Sensitive values remain masked.
6. Restricted users remain blocked from admin-only settings.
7. Tenant settings changes preserve audit and tenant context.

## P1 / Personal Settings

1. User opens `/personal/profile`.
2. User updates profile details.
3. User opens Security.
4. User reviews security settings and active sessions.
5. User opens Preferences and Notifications.
6. User adjusts personal preferences.
7. User opens Activity to review personal audit history.

## P1 / Search And Retrieval

1. User opens Command Center or Context/Governance surfaces.
2. User enters a search query.
3. Results are filtered by tenant and role.
4. User selects a result.
5. UI routes to the relevant account, evidence, trace, or context object.
6. Restricted or cross-tenant results are hidden.
7. Empty/error states are recoverable.

## P1 / Integrations

1. Admin opens `/t/:tenantSlug/settings/integrations` or Context Integrations.
2. Admin reviews available CRM/external integrations.
3. Admin configures or reconnects an integration.
4. User imports CRM/account data.
5. User pushes approved value-case output back to CRM.
6. Failed sync shows retryable status.
7. Secret values remain masked.

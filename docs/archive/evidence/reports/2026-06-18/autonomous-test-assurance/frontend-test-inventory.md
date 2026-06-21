# Frontend Web App Test Inventory

Generated: 2026-05-28

## Frontend Tests
| Type | Unit Tests | Component Tests | E2E Tests | Accessibility Tests |
|------|-----------|-----------------|-----------|---------------------|
| Frontend | 57 unit tests | 58 component tests | 56 E2E tests | 3 accessibility tests |

## Test Categories

### Unit Tests (57 files)
- AgentEventClient.context.test.ts
- eventSchemas.test.ts
- useAgentEvents.context.test.ts
- client.url.test.ts
- accounts-create.contract.test.ts
- agent-stream.contract.test.ts
- benchmarks.contract.test.ts
- domain-coverage.contract.test.ts
- extraction.contract.test.ts
- formulas.contract.test.ts
- governance.contract.test.ts
- graph.contract.test.ts
- ground-truth.contract.test.ts
- intelligence.contract.test.ts
- openapi-drift.contract.test.ts
- statuses.contract.test.ts
- tenant-context.contract.test.ts
- valuepacks.contract.test.ts
- workflows.contract.test.ts
- workspace.contract.test.ts
- auth.test.ts
- client.clerkBearer.adversarial.test.ts
- client.test.ts
- access.test.ts
- auth.component.test.ts
- clerkConfig.test.ts
- clerkSession.test.ts
- workspaceTabRegistry.test.ts
- useApiShared.test.ts
- useAuth.test.ts
- useBenchmarks.test.ts
- useCompetitiveIntel.test.ts
- useExtractionConfig.test.ts
- useFormulaDependents.test.ts
- useFormulaVersions.test.ts
- useGraphQuery.comprehensive.test.ts
- useGraphQuery.performance.test.ts
- useGraphQuery.property.test.ts
- useGraphQuery.test.ts
- useHarness.test.ts
- useHealthMonitor.test.ts
- useIngestion.test.ts
- useJobStream.test.ts
- useOpportunities.test.ts
- useROICalculator.test.ts
- useROIScenarios.test.ts
- useSkillJobs.test.ts
- useTargets.test.ts
- useTenantMembership.test.ts
- useValueCaseArtifacts.test.ts
- useValueCase.test.ts
- useValueHypothesis.test.ts
- useValuePacks.test.ts
- useValueTree.test.ts
- useWorkspaceCase.test.ts
- workflowStore.test.ts

### Component Tests (58 files)
- GovernanceAuditTrail.test.tsx
- TeamAccessPages.test.tsx
- ClerkAuthBridge.test.tsx
- ProspectSetup.behavior.test.tsx
- WfPrimitives.test.tsx
- EvidenceCard.test.tsx
- HorizontalTabWrapper.test.tsx
- ValueLeversCalculator.test.tsx
- GlobalLayout.test.tsx
- RightRailPanel.test.tsx
- landmarks.test.tsx
- TieredNav.test.tsx
- RequireClerkAuth.test.tsx
- UnifiedRouteGuard.test.tsx
- states.test.tsx
- virtual-list.test.tsx
- virtual-list.visual.test.tsx
- AccountPickerModal.test.tsx
- IntelligenceWorkspaceTabs.test.tsx
- useAccountAccess.test.tsx
- useAccounts.test.tsx
- useBilling.test.tsx
- useBusinessCases.test.tsx
- useComments.test.tsx
- useDocuments.test.tsx
- useEntitlements.test.tsx
- useFormulas.test.tsx
- useIntelligence.test.tsx
- useL5Governance.test.tsx
- useModels.test.tsx
- useNavigation.test.tsx
- useNotifications.test.tsx
- usePlatformSettings.test.tsx
- useProvenance.test.tsx
- useRoutePrefetch.test.tsx
- useTasks.test.tsx
- useValuePacks.test.tsx
- useWorkspaceCase.pageActions.test.tsx
- useWorkspacePageActions.test.tsx
- Accounts.test.tsx
- AgentWorkflows.harness.test.tsx
- AgentWorkflows.test.tsx
- BusinessCase.test.tsx
- BusinessCaseList.test.tsx
- DecisionTrace.test.tsx
- EntityBrowser.contract.test.tsx
- ExtractionEngine.test.tsx
- ScenarioPanel.test.tsx
- FormulaBuilder.test.tsx
- GovernancePages.test.tsx
- IntelligenceWorkspace.test.tsx
- NarrativeProposal.test.tsx
- Notifications.test.tsx
- Settings.test.tsx
- ValueTreeExplorer.test.tsx
- Workspace.test.tsx

### E2E Tests (56 files)
- journeys.spec.ts
- axe-audit.spec.ts
- keyboard-flow.spec.ts
- admin-system.spec.ts
- admin.spec.ts
- session-refresh-edge-cases.spec.ts
- auth-lifecycle.spec.ts
- business-case-list.spec.ts
- business-case-trust-status.spec.ts
- business-case.spec.ts
- collaboration-notifications-tasks.spec.ts
- command-center.spec.ts
- account-scoped-workspaces.spec.ts
- agent-workflow-lifecycle.spec.ts
- harness-runs.spec.ts
- settings-governance.spec.ts
- tier-gated-navigation.spec.ts
- workflow-session-context.spec.ts
- debug-auth.spec.ts
- decision-trace.spec.ts
- export-workflows-deep.spec.ts
- export-workflows.spec.ts
- extraction-engine.spec.ts
- formula-builder.spec.ts
- global-search.spec.ts
- graph-explorer.spec.ts
- hypothesis-convert-selection.spec.ts
- crm-external-integrations.spec.ts
- review-approval-lifecycle.spec.ts
- debug-sidebar.spec.ts
- debug-ui.spec.ts
- full-ui-debug.spec.ts
- j0-auth-session.spec.ts
- j1-created-account-golden-path-backend-integrated.spec.ts
- j1-golden-path-backend-integrated.spec.ts
- j1-golden-path-deep.spec.ts
- j1-ingestion-to-value-tree.spec.ts
- j10-layer-ui-validation-deep.spec.ts
- j10-layer-ui-validation.spec.ts
- j11-golden-path-business-lifecycle.spec.ts
- j12-resilience-error-recovery.spec.ts
- j13-long-running-workflow-progress.spec.ts
- j13-stakeholder-mapping.spec.ts
- j14-value-pack-governance.spec.ts
- j15-narrative-proposal.spec.ts
- j16-collaboration.spec.ts
- j16-collaboration-comments-backend-integrated.spec.ts
- j17-crm-integration.spec.ts
- j18-search-retrieval.spec.ts
- j19-notifications-persistence-backend-integrated.spec.ts
- mock-auth.spec.ts
- my-models.spec.ts
- navigation.spec.ts
- opportunity-finder.spec.ts
- route-validation.spec.ts
- signal-review-persistence.spec.ts
- source-configuration.spec.ts
- targets-admin.spec.ts
- ui-audit.spec.ts
- value-case-regenerate.spec.ts
- value-tree-explorer.spec.ts
- whitespace-analysis.spec.ts

### Accessibility Tests (3 files)
- journeys.spec.ts
- axe-audit.spec.ts
- keyboard-flow.spec.ts

## Key Invariants Discovered

### Authentication
- **Rule**: No unauthenticated access to protected routes
- **Enforcement**: Clerk authentication, RequireClerkAuth component, UnifiedRouteGuard
- **Code Path**: `src/auth/`, `src/components/routing/`

### Tenant Context
- **Rule**: Tenant context must be propagated through all API calls
- **Enforcement**: Tenant context in API client, tenant-scoped routes
- **Code Path**: `src/api/`, `src/stores/userTierStore.ts`

### Authorization
- **Rule**: Role-based access control for tier-gated navigation
- **Enforcement**: User tier store, tier-gated navigation guards
- **Code Path**: `src/stores/userTierStore.ts`, `src/components/navigation/`

### Input Validation
- **Rule**: No unvalidated input reaching backend API
- **Enforcement**: Pydantic-like validation in API client, form validation
- **Code Path**: `src/api/`, form components

### Session Management
- **Rule**: Session ID must be cryptographically secure and persistent
- **Enforcement**: Session ID generation, workflow store session management
- **Code Path**: `src/workflow/store/workflowStore.ts`

### Adversarial Testing
- **Rule**: Frontend must handle adversarial inputs and token attacks
- **Enforcement**: Adversarial test suites, clerk bearer token tests
- **Code Path**: `src/api/client.clerkBearer.adversarial.test.ts`

## Test Markers
- `@backend` - Backend-integrated E2E tests (require PLAYWRIGHT_BACKEND_URL)
- Contract tests - Isolated page-level contract tests (mocked)
- Journey tests - Chained user journey tests (live or contract mode)

## Discovery Notes
- Frontend has comprehensive test coverage (171 total tests)
- Strong E2E test coverage with golden path journeys
- Good coverage of authentication and authorization
- Contract tests for API drift detection
- Accessibility tests present
- Adversarial testing for security
- Backend-integrated E2E tests for critical journeys

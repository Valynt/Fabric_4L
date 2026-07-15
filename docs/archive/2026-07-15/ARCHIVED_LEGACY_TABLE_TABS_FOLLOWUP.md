# Legacy Table/Tabs Migration Follow-up Backlog

Remaining high-priority page migrations after this change set:

1. `apps/web/src/pages/AgentWorkflows.tsx` (LegacyDataTable + LegacyTabs)
2. `apps/web/src/pages/EntityBrowser.tsx` (LegacyDataTable)
3. `apps/web/src/pages/ExtractionEngine.tsx` (LegacyDataTable)
4. `apps/web/src/pages/DecisionTrace.tsx` (LegacyDataTable)
5. `apps/web/src/pages/ValueTreeExplorer.tsx` (LegacyTabs)

Notes:
- Preserve loading/empty/error/pagination behaviors during migration.
- Replace `@/components/ui/fabric` legacy table/tab imports with canonical `DataTable` and `@/components/ui/tabs` primitives.
- Add behavior-parity tests for sorting/selection/tab switching and accessibility labels.

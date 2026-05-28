# Repo Hygiene Cleanup Work Items (2026-05-12)

Created from unresolved checklist items in `reports/repo-hygiene-cleanup-summary.md`.

| Issue ID | Work Item | Owner | Target Date | Source Report Item | Status |
|---|---|---|---|---|---|
| RH-2026-001 | Remove locked `pytest-cache-files-*` directories after process lock release and verify deletion. | Dev Productivity | 2026-05-20 | Remove pytest-cache-files-* directories | Open |
| RH-2026-002 | Remove locked `.pytest-tmp` directory after process lock release and verify deletion. | Dev Productivity | 2026-05-20 | Remove `.pytest-tmp` directory | Open |
| RH-2026-003 | Complete manual cleanup sweep of locked cache artifacts and attach validation evidence. | Repo Stewardship | 2026-05-22 | Manual cleanup of locked directories | Open |
| RH-2026-004 | Inspect `bns.zip`, determine retention policy (delete/relocate), and document decision in follow-up PR. | Platform Architecture | 2026-05-27 | `bns.zip` manual inspection (separate PR) | Closed (relocated to `artifacts/non-runtime/bns.zip`, 2026-05-12) |
| RH-2026-005 | Review `temp_nav_service.ts` usage and remove or relocate with references updated. | Frontend Platform | 2026-05-27 | `temp_nav_service.ts` manual review (separate PR) | Open |

## Tracking Notes

- Completion evidence should include command output or PR link.
- If a target date slips, add a dated extension note with rationale.

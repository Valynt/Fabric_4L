# Review Queue

**Pending:** 1
**Oldest staged:** 2026-09-03T04:11:46.153430+00:00

Run `python .agent/tools/list_candidates.py` for detail, then:
- `python .agent/tools/graduate.py <id> --rationale "..."` to accept
- `python .agent/tools/reject.py <id> --reason "..."` to reject
- Review in a batch so cross-candidate contradictions are caught.

## Priority order (top 10)

- **16fd951baf2a** (priority=67.50, size=5, rejections=0) — High-stakes op completed (release): a Fabric_4L release operation completed on a GitHub Actions CI runner; the captured event text was truncated mid-command, so no reproducible command is recorded.

# Review Queue

**Pending:** 5
**Oldest staged:** 2026-07-22T13:15:59.950907+00:00

Run `python .agent/tools/list_candidates.py` for detail, then:
- `python .agent/tools/graduate.py <id> --rationale "..."` to accept
- `python .agent/tools/reject.py <id> --reason "..."` to reject
- Review in a batch so cross-candidate contradictions are caught.

## Priority order (top 10)

- **b2647b04bded** (priority=13864.50, size=1027, rejections=0) — High-stakes op completed (prod): sed -n '1310,1365p' .github/workflows/pr-checks
- **d4931e63e57c** (priority=13662.00, size=1012, rejections=0) — High-stakes op completed (release): uname -a; sed -n '1,40p' /etc/os-release; pr
- **4a05d1b610e7** (priority=12676.50, size=939, rejections=0) — High-stakes op completed (secret): perl -0pi -e 's/from layer4_agents\.integrati
- **32f152b98992** (priority=11853.00, size=878, rejections=0) — High-stakes op completed (release): pwd; git branch --show-current; git rev-pars
- **73778721a450** (priority=5940.00, size=440, rejections=0) — High-stakes op completed (production): sed -n '1,260p' docs/development/DISCOVER

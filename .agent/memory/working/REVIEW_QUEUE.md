# Review Queue

**Pending:** 2
**Oldest staged:** 2026-08-09T20:44:54.402259+00:00

Run `python .agent/tools/list_candidates.py` for detail, then:
- `python .agent/tools/graduate.py <id> --rationale "..."` to accept
- `python .agent/tools/reject.py <id> --reason "..."` to reject
- Review in a batch so cross-candidate contradictions are caught.

## Priority order (top 10)

- **e399ba505bb0** (priority=1080.00, size=80, rejections=0) — High-stakes op completed (prod): for f in infra/compose/docker-compose.prod.yml 
- **bc0262ebd4c1** (priority=54.00, size=4, rejections=0) — High-stakes op completed (secret): API_KEY_HMAC_SECRET=devcontainer-contract-api

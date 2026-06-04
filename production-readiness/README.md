# Production Readiness

This directory is the visible launch-readiness roll-up for Fabric_4L. It does not replace detailed governance docs, CI logs, or operational runbooks; it links them into one review surface so readiness status is explicit before production launch.

## Files

| File | Purpose |
|---|---|
| [scorecard.md](scorecard.md) | Executive readiness scorecard with owner, status, risk, validation command, blocker state, and CI artifact link for each production-readiness area. |
| [launch_checklist.md](launch_checklist.md) | Required launch review checklist. Production launch cannot proceed until this checklist records scorecard review. |
| [ownership_matrix.md](ownership_matrix.md) | Named functional ownership and escalation paths for each readiness area. |
| [risk_register.md](risk_register.md) | P0/P1 launch blockers and tracked readiness risks. |

## Required Review Gate

Production launch requires an explicit scorecard review. The launch reviewer must run:

```bash
pnpm production:scorecard
pnpm production:check
```

The review must confirm that every P0/P1 blocker in [scorecard.md](scorecard.md) and [risk_register.md](risk_register.md) is closed, waived by the accountable owner, or intentionally scoped out of the launch decision.

## Source Documents

- [P0 production-readiness foundations](../docs/governance/production-readiness-p0-foundations.md)
- [P1 operational controls](../docs/governance/production-readiness-p1-operational-controls.md)
- [P2 governance and commercialization](../docs/governance/production-readiness-p2-governance-commercialization.md)
- [Launch drift prevention SOP](../docs/governance/launch-drift-prevention-sop.md)
- [Launch evidence bundle generator](../scripts/ci/generate_launch_evidence_bundle.py)

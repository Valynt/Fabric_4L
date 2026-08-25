# Incident Operations Package

This package defines the operational standards for incident response, reporting, and learning.

## Contents

1. [Incident severity matrix and on-call escalation policy](severity-escalation-policy.md)
2. [MTTA/MTTR definitions and monthly reporting process](mtta-mttr-reporting.md)
3. [Postmortem template and corrective action tracking](postmortem-template.md)
4. [Production Operations Plan](production-operations-plan.md)

## How to use this package

- **During incidents**: classify severity first, then follow the escalation policy.
- **For all alerts**: start with the relevant runbook in `docs/runbooks/` and apply severity/escalation expectations from this package.
- **After incidents**: complete a postmortem and track corrective actions to closure.
- **Monthly**: publish MTTA/MTTR metrics and trend analysis.

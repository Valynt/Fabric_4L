# Launch Checklist

Production launch requires scorecard review before approval.

| Check | Owner | Required evidence | Status |
|---|---|---|---|
| Scorecard review completed | Release Engineering | Reviewed [scorecard.md](scorecard.md), latest CI artifact links attached, and every owner acknowledged current status. | REQUIRED |
| P0 blockers resolved | Release Engineering | No open `[BLOCKER:P0]` item remains in [scorecard.md](scorecard.md) or [risk_register.md](risk_register.md). | REQUIRED |
| P1 blockers accepted or resolved | Product and Platform Owners | Every `[BLOCKER:P1]` item is closed, waived, or explicitly scoped out of launch. | REQUIRED |
| Security evidence retained | Security Engineering | Security regression, supply-chain, and audit evidence artifacts retained in CI. | REQUIRED |
| Tenant isolation evidence retained | Platform Security | Tenant isolation gate and route tenant propagation artifacts retained in CI. | REQUIRED |
| DR and rollback evidence retained | SRE | Backup, restore, rollback, and deploy evidence artifacts retained in CI or release archive. | REQUIRED |
| Billing launch decision recorded | Product Engineering | Paid launch scope and billing evidence status recorded. | REQUIRED |
| Compliance owner signoff recorded | Compliance Owner | Audit snapshot, control owner review, and evidence retention location recorded. | REQUIRED |

## Launch Decision

Do not approve production launch from ticket comments, informal chat, or isolated CI logs. The launch decision must cite this checklist, the current scorecard, and retained evidence artifacts.

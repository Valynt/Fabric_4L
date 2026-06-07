---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# ROI Calculations

ROI calculations in ValuePact are built on driver trees, formulas, and scenario modeling. They translate qualitative value hypotheses into quantified, auditable financial projections.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Executive</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Prerequisites

- A ValuePact account with identified [value drivers](opportunities.md) or hypotheses
- The account's industry and value pack configured
- At least one formula available in the account's value pack

## Overview

The ROI calculator is powered by Layer 4 agentic workflows and the Layer 3 formula engine. It resolves value trees from the knowledge graph, substitutes prospect-specific variables, evaluates mathematical expressions safely, and runs sensitivity analysis.

## Driver trees

A driver tree decomposes high-level value into levers and metrics. For example, a SaaS value tree might look like:

```
SaaS Platform Value
├── Cost Efficiency (35%)
│   ├── Infrastructure optimization
│   └── Tool consolidation
├── Revenue Growth (40%)
│   ├── New ARR
│   └── Expansion ARR
└── Retention (25%)
    ├── Churn reduction
    └── NRR improvement
```

Each node links to a formula that computes a monetary value from baseline and target inputs.

## Formulas

Formulas are stored per value pack and evaluated using safe numeric expression evaluation. A formula defines:

- **Inputs** — variables such as `affected_fte_count`, `hours_saved_per_fte_weekly`
- **Expression** — a mathematical formula such as `affected_fte_count * hours_saved_per_fte_weekly * 52 * fully_loaded_cost_per_hour`
- **Outputs** — computed values such as `annual_savings`, `payback_months`
- **Validation rules** — constraints such as `payback_months <= 36`

Example formula from the Enterprise SaaS value pack:

```yaml
annual_savings: affected_fte_count * hours_saved_per_fte_weekly * 52 * fully_loaded_cost_per_hour
net_value: annual_savings - implementation_cost
payback_months: implementation_cost / (annual_savings / 12)
```

## Calculator usage

1. Open the account's **Value Studio** workspace.
2. Select the **ROI Calculator** tab.
3. Choose a scenario: **Conservative**, **Expected**, or **Optimistic**.
4. Edit variables in the **Variables** panel. Defaults are populated from the value pack.
5. Click **Calculate ROI**.
6. Review the summary card: NPV, IRR, payback period, and total ROI percentage.

### Scenario modeling

| Scenario | Use case | Typical adjustment |
|----------|----------|-------------------|
| Conservative | Risk-averse planning | 80% of expected benefit, 120% of cost |
| Expected | Standard planning | Baseline assumptions |
| Optimistic | Best-case planning | 120% of expected benefit, 90% of cost |

## Sensitivity analysis

Toggle **Sensitivity Analysis** to run a Monte Carlo simulation across key variables. The output shows:

- **Tornado chart** — which variables have the largest impact on NPV
- **Probability distribution** — likelihood of achieving target ROI
- **Break-even thresholds** — input values required for payback within 12 or 24 months

## Benchmark comparison

After calculation, the platform fetches industry benchmarks from Layer 6. The comparison card shows where the account's projected ROI, payback, and NPV rank against peers.

| Percentile | Interpretation |
|------------|---------------|
| Below p25 | Conservative relative to peers |
| p25–p75 | Typical range |
| Above p75 | Aggressive but achievable with strong evidence |

### Formula validation rules

Every formula enforces validation rules at calculation time. Rules protect against unrealistic assumptions and ensure defensible outputs.

Common validation rule patterns:

| Rule type | Example | Failure message |
|-----------|---------|----------------|
| Range check | `hours_saved_per_fte_weekly <= 40` | "Hours saved cannot exceed a full work week" |
| Greater than | `target_yield_pct > current_yield_pct` | "Target must exceed current baseline" |
| Payback cap | `payback_months <= 36` | "Payback exceeds 36-month threshold" |
| Non-negative | `annual_savings >= 0` | "Savings cannot be negative" |

When a rule fails, the offending variable is highlighted in red and a tooltip shows the rule text. The calculation is blocked until the input is corrected or the rule is waived by an admin.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure formulas and value packs | Organization |
| User | Run calculations and edit variables | Assigned accounts |
| Executive | View results and benchmarks | Organization or assigned accounts |

<span class="vp-badge vp-badge--permission">Required</span> `value_model:write` to edit variables; `value_model:read` to view.

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Formula evaluation timeout is 5 seconds per expression.

<span class="vp-badge vp-badge--limit">Limit</span> Sensitivity analysis runs up to 10,000 Monte Carlo iterations.

<span class="vp-badge vp-badge--limit">Limit</span> A maximum of 20 active formulas can be attached to a single account's value model.

## Troubleshooting

??? question "Issue: ROI calculation returns 'validation failed'"
    **Cause:** An input violates a formula validation rule, such as `payback_months <= 36`.
    **Resolution:** Check the red-highlighted variable in the **Variables** panel. Adjust the value to satisfy the rule, or contact an admin to relax the constraint if justified.

??? question "Issue: Benchmark comparison shows 'industry not found'"
    **Cause:** The account industry does not match a benchmark dataset in Layer 6.
    **Resolution:** Verify the account industry in **Account Settings**. If the industry is correct but no benchmark exists, the comparison card is hidden automatically.

??? question "Issue: Sensitivity analysis takes too long"
    **Cause:** The account's value model has deeply nested formulas or many linked drivers.
    **Resolution:** Reduce the iteration count in **Settings > Analysis > Monte Carlo Iterations**, or simplify the driver tree.

??? question "Issue: Formula output shows scientific notation instead of currency"
    **Cause:** The output unit is not set to `currency` or the display format is overridden.
    **Resolution:** Check the formula definition in **Value Studio > Formulas**. Ensure `output_unit` is set to `USD` or the appropriate currency, and verify the account's regional display settings.

## Related pages

- [Value Metrics](value-metrics.md)
- [Forecasts](forecasts.md)
- [Business Cases](business-cases.md)
- [Opportunities](opportunities.md)

## Escalation path

For formula configuration issues, contact your value pack admin. For calculation engine errors, open a support ticket with the calculation ID and tenant ID.
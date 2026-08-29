# Fabric Authorization Rego Bundle

OPA/Rego policy bundle for the Fabric authorization control plane
(`fabric.authz.*`). This bundle is the independent Rego mirror of the
Python `InProcessPolicyEngine` in `services/api/app/authz/engine.py`: the same
decision tables are tested in Python and in Rego so divergence is detectable
before OPA is deployed as a service.

## Layout

OPA bundles map `<namespace>/data.json` to `data.<namespace>`, so the static
catalog documents live in namespace directories:

- `bundle/manifest.json` - OPA bundle manifest (revision, roots, metadata).
- `bundle/action_catalog/data.json` - `data.action_catalog`: 54 known actions,
  per-action resource type map, protected (critical four) actions, and the
  agent-forbidden action set.
- `bundle/baseline_roles/data.json` - `data.baseline_roles`: baseline workflow
  and platform role namespaces.
- `bundle/static_sod/data.json` - `data.static_sod`: static
  separation-of-duty constraints (design Section 7.3).
- `bundle/policy/` - policy packages:
  - `global.rego` (`package fabric.authz`) - default-deny, tenant equality
    (necessary, never sufficient), agent-forbidden actions, known-action
    gating, and the minimum-eligibility allow for non-critical known actions.
  - `claims.rego` (`package fabric.authz.claims`) - `claim.approve`.
  - `deliverables.rego` (`package fabric.authz.deliverables`) -
    `deliverable.publish_external`.
  - `exceptions.rego` (`package fabric.authz.exceptions`) -
    `exception.activate`.
  - `opportunities.rego` (`package fabric.authz.opportunities`) -
    `opportunity.lock_realization`.
- `bundle/tests/` - Rego unit tests (`opa test -b bundle`).
- `schemas/` - JSON Schemas for `fabric.authz.request.v1` and
  `fabric.authz.decision.v1`.

## Response surface

Every package exposes `allow` (boolean, default false), `deny_reason`
(set of stable reason codes), and `obligations` (set of obligation types).
`data.fabric.authz` additionally exposes `reason` (semicolon-joined deny
reasons) for logging.

## Rules encoded

- Default deny; unknown actions and unknown resource types deny.
- Agent categorical deny for the ten forbidden verbs (design Section 11.1).
- Tenant equality is necessary but never sufficient for allow.
- Self-approval denial (`claim.approve`, `exception.activate`).
- Approval-ceiling denial above `principal.approval_ceiling_usd`.
- Model-version-stale denial when a requested model version does not match.
- Publication requires all included claims approved, no open included
  disputes, quote/model match, exception requirement satisfied, and
  publisher SoD not failed.
- Exception activation requires the named approver (not the requester),
  `APPROVED` state, policy eligibility PASS, non-empty scope, and unexpired
  approval.
- Realization lock requires the realization-owner relationship, permitted
  lifecycle state, complete approvals, no blocking dispute, and logical
  realization eligibility (ceiling or finance/deal-desk/value-manager role).

## Validation

With OPA installed:

```bash
opa test -b policies/authorization/bundle
opa eval -b policies/authorization/bundle --failed-builtins \
  --input example.json "data.fabric.authz"
```

The Rego here is `import rego.v1` (OPA 1.0+ semantics). Time comparisons use
`time.parse_rfc3339_ns`, so decision inputs must carry RFC3339 timestamps.

# opportunity.lock_realization tests (design Section 12.3).

package fabric.authz.opportunities_test

import data.fabric.authz.opportunities

lock_input := {
    "schema_version": "fabric.authz.request.v1",
    "request_id": "req-o-1",
    "action": "opportunity.lock_realization",
    "context": {"now": "2025-06-01T12:00:00Z"},
    "principal": {"id": "p-own", "type": "human", "tenant_id": "t-1", "status": "active", "workflow_roles": ["workflow.realization_owner", "workflow.finance_approver"], "approval_ceiling_usd": 1000000},
    "resource": {"type": "opportunity", "id": "o-1", "tenant_id": "t-1", "attributes": {"lifecycle_state": "QUALIFIED", "required_approvals_complete": true, "blocking_dispute_count": 0}},
}

# ??? Allow ????????????????????????????????????????????????????????????????

test_lock_realization_allowed_for_realization_owner if {
    opportunities.allow with input as lock_input
}

test_lock_realization_allowed_with_ceiling_without_extra_role if {
    opportunities.allow with input as _strip_logical_roles(lock_input)
}

# ??? Deny paths ???????????????????????????????????????????????????????????

test_lock_realization_denied_without_owner_role if {
    not opportunities.allow with input as _strip_all_roles(lock_input)
    "ROLE_MISSING" in opportunities.deny_reason with input as _strip_all_roles(lock_input)
}

test_lock_realization_denied_for_illegal_lifecycle_state if {
    not opportunities.allow with input as _with_attr(lock_input, "lifecycle_state", "ARCHIVED")
    "POLICY_INPUT_INVALID" in opportunities.deny_reason with input as _with_attr(lock_input, "lifecycle_state", "ARCHIVED")
}

test_lock_realization_denied_when_approvals_incomplete if {
    not opportunities.allow with input as _with_attr(lock_input, "required_approvals_complete", false)
}

test_lock_realization_denied_on_blocking_dispute if {
    not opportunities.allow with input as _with_attr(lock_input, "blocking_dispute_count", 1)
    "DISPUTE_OPEN" in opportunities.deny_reason with input as _with_attr(lock_input, "blocking_dispute_count", 1)
}

test_lock_realization_denied_for_agent if {
    not opportunities.allow with input as _as_agent(lock_input)
}

# ??? Obligations on allow ????????????????????????????????????????????????

test_allow_carries_idempotency_obligation if {
    "require_idempotency_key" in opportunities.obligations with input as lock_input
}

# ??? Helpers ??????????????????????????????????????????????????????????????

_strip_logical_roles(req) := object.union(req, {"principal": object.union(req.principal, {"workflow_roles": ["workflow.realization_owner"]})})

_strip_all_roles(req) := object.union(req, {"principal": object.union(req.principal, {"workflow_roles": []})})

_with_attr(req, key, value) := {"schema_version": req.schema_version, "request_id": req.request_id, "action": req.action, "context": req.context, "principal": req.principal, "resource": object.union(req.resource, {"attributes": object.union(req.resource.attributes, {key: value})})}

_as_agent(req) := object.union(req, {"principal": object.union(req.principal, {"type": "agent"})})

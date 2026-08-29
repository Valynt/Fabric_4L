# exception.activate tests (design Section 11.4).

package fabric.authz.exceptions_test

import data.fabric.authz.exceptions

activate_input := {
    "schema_version": "fabric.authz.request.v1",
    "request_id": "req-e-1",
    "action": "exception.activate",
    "context": {"now": "2025-06-01T12:00:00Z"},
    "principal": {"id": "p-approver", "type": "human", "tenant_id": "t-1", "status": "active"},
    "resource": {"type": "exception", "id": "x-1", "tenant_id": "t-1", "attributes": {"approver_id": "p-approver", "requester_id": "p-requester", "state": "APPROVED", "policy_eligibility": "PASS", "scope_non_empty": true, "approval_expires_at": "2030-01-01T00:00:00Z"}},
}

# ??? Allow ????????????????????????????????????????????????????????????????

test_exception_activate_allowed_for_named_approver if {
    exceptions.allow with input as activate_input
}

# ??? Deny paths ???????????????????????????????????????????????????????????

test_exception_activate_denied_for_requester if {
    not exceptions.allow with input as _with_principal_id(activate_input, "p-requester")
    "SELF_APPROVAL_FORBIDDEN" in exceptions.deny_reason with input as _with_principal_id(activate_input, "p-requester")
}

test_exception_activate_denied_for_unapproved_state if {
    not exceptions.allow with input as _with_attr(activate_input, "state", "SUBMITTED")
}

test_exception_activate_denied_when_eligibility_fails if {
    not exceptions.allow with input as _with_attr(activate_input, "policy_eligibility", "FAIL")
}

test_exception_activate_denied_for_empty_scope if {
    not exceptions.allow with input as _with_attr(activate_input, "scope_non_empty", false)
    "EXCEPTION_SCOPE_MISMATCH" in exceptions.deny_reason with input as _with_attr(activate_input, "scope_non_empty", false)
}

test_exception_activate_denied_when_approval_expired if {
    not exceptions.allow with input as _with_attr(activate_input, "approval_expires_at", "2020-01-01T00:00:00Z")
    "EXCEPTION_EXPIRED" in exceptions.deny_reason with input as _with_attr(activate_input, "approval_expires_at", "2020-01-01T00:00:00Z")
}

# ??? Obligations on allow ????????????????????????????????????????????????

test_allow_carries_audit_obligation if {
    "write_audit_event" in exceptions.obligations with input as activate_input
}

# ??? Helpers ??????????????????????????????????????????????????????????????

_with_principal_id(req, id) := object.union(req, {"principal": object.union(req.principal, {"id": id})})

_with_attr(req, key, value) := {"schema_version": req.schema_version, "request_id": req.request_id, "action": req.action, "context": req.context, "principal": req.principal, "resource": object.union(req.resource, {"attributes": object.union(req.resource.attributes, {key: value})})}

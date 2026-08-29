# deliverable.publish_external tests (design Section 11.3).

package fabric.authz.deliverables_test

import data.fabric.authz.deliverables

pub_input := {
    "schema_version": "fabric.authz.request.v1",
    "request_id": "req-d-1",
    "action": "deliverable.publish_external",
    "context": {"now": "2025-06-01T12:00:00Z"},
    "principal": {"id": "p-dd", "type": "human", "tenant_id": "t-1", "status": "active", "workflow_roles": ["workflow.deal_desk"]},
    "resource": {"type": "deliverable", "id": "d-1", "tenant_id": "t-1", "attributes": {"all_included_claims_approved": true, "open_included_dispute_count": 0, "quote_matches_model": true, "exception_required": false}},
}

# ??? Allow ????????????????????????????????????????????????????????????????

test_publish_allowed_for_deal_desk if {
    deliverables.allow with input as pub_input
}

test_publish_allowed_for_value_manager if {
    deliverables.allow with input as _with_role(pub_input, "workflow.value_manager")
}

# ??? Deny paths ???????????????????????????????????????????????????????????

test_publish_denied_without_publication_role if {
    not deliverables.allow with input as _strip_role(pub_input)
    "ROLE_MISSING" in deliverables.deny_reason with input as _strip_role(pub_input)
}

test_publish_denied_when_included_claim_not_approved if {
    not deliverables.allow with input as _with_attr(pub_input, "all_included_claims_approved", false)
    "PUBLICATION_BLOCKED" in deliverables.deny_reason with input as _with_attr(pub_input, "all_included_claims_approved", false)
}

test_publish_denied_when_quote_mismatch if {
    not deliverables.allow with input as _with_attr(pub_input, "quote_matches_model", false)
}

test_publish_denied_on_open_included_dispute if {
    not deliverables.allow with input as _with_attr(pub_input, "open_included_dispute_count", 2)
    "DISPUTE_OPEN" in deliverables.deny_reason with input as _with_attr(pub_input, "open_included_dispute_count", 2)
}

test_publish_denied_when_exception_required_but_not_activated if {
    not deliverables.allow with input as _with_exception(pub_input, "DRAFT", "2030-01-01T00:00:00Z", true)
    "EXCEPTION_NOT_ACTIVATED" in deliverables.deny_reason with input as _with_exception(pub_input, "DRAFT", "2030-01-01T00:00:00Z", true)
}

test_publish_denied_when_exception_expired if {
    not deliverables.allow with input as _with_exception(pub_input, "ACTIVATED", "2020-01-01T00:00:00Z", true)
    "EXCEPTION_EXPIRED" in deliverables.deny_reason with input as _with_exception(pub_input, "ACTIVATED", "2020-01-01T00:00:00Z", true)
}

test_publish_allowed_when_active_exception_covers if {
    deliverables.allow with input as _with_exception(pub_input, "ACTIVATED", "2030-01-01T00:00:00Z", true)
}

# ??? Helpers ??????????????????????????????????????????????????????????????

_with_role(req, role) := object.union(req, {"principal": object.union(req.principal, {"workflow_roles": [role]})})

_strip_role(req) := object.union(req, {"principal": object.union(req.principal, {"workflow_roles": []})})

_with_attr(req, key, value) := {"schema_version": req.schema_version, "request_id": req.request_id, "action": req.action, "context": req.context, "principal": req.principal, "resource": object.union(req.resource, {"attributes": object.union(req.resource.attributes, {key: value})})}

_with_exception(req, state, expires, covers) := _with_attrs(req, {"exception_required": true, "exception_state": state, "exception_expires_at": expires, "exception_covers_deliverable": covers})

_with_attrs(req, attrs) := {"schema_version": req.schema_version, "request_id": req.request_id, "action": req.action, "context": req.context, "principal": req.principal, "resource": object.union(req.resource, {"attributes": object.union(req.resource.attributes, attrs)})}

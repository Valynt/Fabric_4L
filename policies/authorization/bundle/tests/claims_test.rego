# claim.approve tests (design Section 11.2).

package fabric.authz.claims_test

import data.fabric.authz.claims

finance_input := {
    "schema_version": "fabric.authz.request.v1",
    "request_id": "req-c-1",
    "action": "claim.approve",
    "context": {"now": "2025-06-01T12:00:00Z", "requested_model_version": "v2.1"},
    "principal": {"id": "p-fin", "type": "human", "tenant_id": "t-1", "status": "active", "workflow_roles": ["workflow.finance_approver"], "approval_ceiling_usd": 1000000},
    "resource": {"type": "claim", "id": "c-1", "tenant_id": "t-1", "relationships": ["economic_reviewer"], "attributes": {"author_id": "p-auth", "validation_state": "REVIEWED", "model_version": "v2.1", "impact_usd": 50000, "open_dispute_count": 0, "publication_state": "CANDIDATE"}},
}

# ??? Allow ????????????????????????????????????????????????????????????????

test_claim_approve_allowed_for_eligible_finance_approver if {
    claims.allow with input as finance_input
}

test_claim_approve_allowed_with_realization_owner_on_locked if {
    claims.allow with input as _with_publication_state(_with_role(finance_input, "workflow.realization_owner"), "LOCKED_REALIZATION")
}

# ??? Deny paths ???????????????????????????????????????????????????????????

test_self_approval_denied if {
    not claims.allow with input as _with_author(finance_input, "p-fin")
    "SELF_APPROVAL_FORBIDDEN" in claims.deny_reason with input as _with_author(finance_input, "p-fin")
}

test_missing_finance_role_denied if {
    not claims.allow with input as _strip_role(finance_input)
    "ROLE_MISSING" in claims.deny_reason with input as _strip_role(finance_input)
}

test_missing_economic_reviewer_relationship_denied if {
    not claims.allow with input as _strip_relationship(finance_input)
    "RELATIONSHIP_MISSING" in claims.deny_reason with input as _strip_relationship(finance_input)
}

test_model_version_stale_denied if {
    not claims.allow with input as _with_model_version(finance_input, "v1.9")
    "MODEL_VERSION_STALE" in claims.deny_reason with input as _with_model_version(finance_input, "v1.9")
}

test_approval_ceiling_exceeded_denied if {
    not claims.allow with input as _with_impact(finance_input, 2000000)
    "APPROVAL_CEILING_EXCEEDED" in claims.deny_reason with input as _with_impact(finance_input, 2000000)
}

test_open_dispute_denied if {
    not claims.allow with input as _with_dispute(finance_input, 1)
    "DISPUTE_OPEN" in claims.deny_reason with input as _with_dispute(finance_input, 1)
}

test_locked_realization_without_owner_denied if {
    not claims.allow with input as _with_publication_state(finance_input, "LOCKED_REALIZATION")
    "REALIZATION_CONSTRAINT_FAILED" in claims.deny_reason with input as _with_publication_state(finance_input, "LOCKED_REALIZATION")
}

test_unreviewed_claim_denied if {
    not claims.allow with input as _with_validation_state(finance_input, "NOT_REVIEWED")
}

# ??? Obligations on allow ????????????????????????????????????????????????

test_allow_carries_record_approval_reason_obligation if {
    "record_approval_reason" in claims.obligations with input as finance_input
}

# ??? Helpers ??????????????????????????????????????????????????????????????

_with_role(req, role) := object.union(req, {"principal": object.union(req.principal, {"workflow_roles": array.concat(req.principal.workflow_roles, [role])})})

_with_author(req, author) := {"schema_version": req.schema_version, "request_id": req.request_id, "action": req.action, "context": req.context, "principal": req.principal, "resource": object.union(req.resource, {"attributes": object.union(req.resource.attributes, {"author_id": author})})}

_strip_role(req) := object.union(req, {"principal": object.union(req.principal, {"workflow_roles": []})})

_strip_relationship(req) := object.union(req, {"resource": object.union(req.resource, {"relationships": []})})

_with_model_version(req, version) := {"schema_version": req.schema_version, "request_id": req.request_id, "action": req.action, "context": req.context, "principal": req.principal, "resource": object.union(req.resource, {"attributes": object.union(req.resource.attributes, {"model_version": version})})}

_with_impact(req, impact) := {"schema_version": req.schema_version, "request_id": req.request_id, "action": req.action, "context": req.context, "principal": req.principal, "resource": object.union(req.resource, {"attributes": object.union(req.resource.attributes, {"impact_usd": impact})})}

_with_dispute(req, count) := {"schema_version": req.schema_version, "request_id": req.request_id, "action": req.action, "context": req.context, "principal": req.principal, "resource": object.union(req.resource, {"attributes": object.union(req.resource.attributes, {"open_dispute_count": count})})}

_with_publication_state(req, state) := {"schema_version": req.schema_version, "request_id": req.request_id, "action": req.action, "context": req.context, "principal": req.principal, "resource": object.union(req.resource, {"attributes": object.union(req.resource.attributes, {"publication_state": state})})}

_with_validation_state(req, state) := {"schema_version": req.schema_version, "request_id": req.request_id, "action": req.action, "context": req.context, "principal": req.principal, "resource": object.union(req.resource, {"attributes": object.union(req.resource.attributes, {"validation_state": state})})}

package fabric.authz.claims

import rego.v1
import future.keywords.every

# claim.view — read access to a claim (RBAC role grant, tenant contained).
# generic view is allowed wherever the role matrix grants it.
domain_ok if {
	input.action == "claim.view"
}

# claim.edit_working — principally authored/owned working claims.
domain_ok if {
	input.action == "claim.edit_working"
	not has_open_dispute
}

# claim.validate — protected domain command (technical/finance reviewer).
domain_ok if {
	input.action == "claim.validate"
	not has_open_dispute
}

# claim.approve — protected domain command.
domain_ok if {
	input.action == "claim.approve"
	claim_approve_ok
}

claim_approve_ok if {
	not self_approval
	validation_complete
	not has_open_dispute
	current_model_version
	within_ceiling
	binding_ok
}

self_approval if {
	requester_id := object.get(input.principal, "user_id", object.get(input.principal, "principal_id", ""))
	requester_id != ""
	requester_id == object.get(input.resource, "author_id", "")
}

validation_complete if object.get(input.environment, "validation_complete", object.get(input.resource, "author_id", "")) != ""

has_open_dispute if object.get(input.resource, "has_open_dispute", object.get(input.environment, "has_open_dispute", false)) == true

within_ceiling if {
	approved_ceiling := object.get(input.resource, "approval_ceiling", object.get(input.environment, "approval_ceiling", null))
	impact := object.get(input.resource, "impact_amount", object.get(input.environment, "impact_amount", null))
	is_null(approved_ceiling) or is_null(impact) or impact <= approved_ceiling
}

# ReBAC: the approver must be bound to the economic review (per-claim binding)
# or to an approved review pool for the tenant.
binding_ok if object.get(input.resource, "per_claim_binding", false) == true
binding_ok if object.get(input.resource, "review_pool_binding", object.get(input.environment, "review_pool_binding", false)) == true

# claim.include_in_case — protected command on an approved claim.
domain_ok if {
	input.action == "claim.include_in_case"
	not has_open_dispute
}

# claim.open_dispute / claim.resolve_dispute
domain_ok if {
	input.action == "claim.open_dispute"
	not already_open_dispute
}
already_open_dispute if has_open_dispute

# resolve_dispute requires the resolver not be a party to the dispute and no
# blocking older dispute on the same claim graph.
domain_ok if {
	input.action == "claim.resolve_dispute"
	not has_open_dispute
	resolver_not_party
}
resolver_not_party if {
	parties := object.get(input.resource, "dispute_parties", [])
	resolver := object.get(input.principal, "user_id", "")
	not array_some(parties, resolver)
}
array_some(arr, x) if arr[_] == x
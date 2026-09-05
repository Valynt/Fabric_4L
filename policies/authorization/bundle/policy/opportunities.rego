package fabric.authz.opportunities

import rego.v1

# opportunity.lock_realization — protected domain command (realization_owner).
domain_ok if {
	input.action == "opportunity.lock_realization"
	realization_lock_ok
}

realization_lock_ok if {
	# Default deny unless every requirement met.
	input.action == "opportunity.lock_realization"
	already_locked == false
	opportunity_bound == true
	claim_approved == true
	has_exception == false
}

already_locked if {
	status := object.get(input.resource, "realization_status", object.get(input.environment, "realization_status", ""))
	status == "locked"
}

opportunity_bound if {
	rel := object.get(input.resource, "relationships", object.get(input.environment, "relationships", {}))
	object.get(rel, "opportunity", object.get(input.resource, "opportunity_bound", false)) == true
}

# All included claims must be approved before locking realization.
claim_approved if {
	included := object.get(input.resource, "included_claims", object.get(input.environment, "included_claims", []))
	some_denied(included) == false
}
some_denied(claims) if {
	some c in claims
	object.get(c, "status", "") != "approved"
}

# No active exception may be in force that was not explicitly resolved.
has_exception if {
	exceptions := object.get(input.resource, "exceptions", [])
	some e in exceptions
	object.get(e, "status", "") == "active"
}
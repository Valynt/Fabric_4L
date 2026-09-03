package fabric.authz.deliverables

import rego.v1

# deliverable.publish_external — protected domain command.
domain_ok if {
	input.action == "deliverable.publish_external"
	publish_external_ok
}

publish_external_ok if {
	input.action == "deliverable.publish_external"
	publisher_sod_ok == true
	quote_matches_model == true
	all_included_claims_approved == true
	no_blocking_dispute == true
	exception_gate_ok == true
}

publisher_sod_ok if {
	# Publisher may not be the claim author or the sole approver of every claim.
	distinct_actors(input.resource, "publisher") == true
}

quote_matches_model if {
	quote_model := object.get(input.resource, "quote_model_version", object.get(input.environment, "quote_model_version", ""))
	model_version := object.get(input.resource, "model_version", object.get(input.environment, "model_version", ""))
	quote_model != "" and quote_model == model_version
}

all_included_claims_approved if {
	claims := object.get(input.resource, "included_claims", object.get(input.environment, "included_claims", []))
	not some { some c in claims; object.get(c, "status", "") != "approved" }
}

no_blocking_dispute if {
	claims := object.get(input.resource, "included_claims", object.get(input.environment, "included_claims", []))
	not some { some c in claims; object.get(c, "has_open_dispute", false) == true }
	not object.get(input.resource, "has_open_dispute", false) == true
}

# If any exception is required it must be ACTIVATED, in scope, unexpired.
exception_gate_ok if {
	requires_exception := object.get(input.resource, "requires_exception", object.get(input.environment, "requires_exception", false))
	requires_exception == false
}
exception_gate_ok if {
	requires_exception := object.get(input.resource, "requires_exception", object.get(input.environment, "requires_exception", false))
	requires_exception == true
	exceptions := object.get(input.resource, "exceptions", object.get(input.environment, "exceptions", []))
	some e in exceptions
	object.get(e, "status", "") == "activated"
	not object.get(e, "expired", false) == true
	scope_ok := object.get(input.resource, "exception_in_scope", object.get(input.environment, "exception_in_scope", true))
	scope_ok == true
}

distinct_actors(r, actor_key) if {
	author := object.get(r, "author_id", "")
	publisher := object.get(r, actor_key, "")
	author != "" and publisher != "" and author != publisher
	# publisher must differ from each claim author
	claims := object.get(r, "included_claims", [])
	not some { some c in claims; object.get(c, "author_id", "") == publisher }
}

# deliverable.revoke_link — caller must be on tenant and either the publisher or a designated revoker.
domain_ok if {
	input.action == "deliverable.revoke_link"
	revoke_binding_ok
}
revoke_binding_ok if {
	publisher := object.get(input.resource, "publisher", "")
	requester := object.get(input.principal, "user_id", "")
	publisher != "" and requester == publisher
}
revoke_binding_ok if {
	rel := object.get(input.resource, "relationships", object.get(input.environment, "relationships", {}))
	object.get(rel, "can_revoke", false) == true
}
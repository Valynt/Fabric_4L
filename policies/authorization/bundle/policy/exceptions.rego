package fabric.authz.exceptions

import rego.v1

# exception.submit — protected domain command. Agent may draft but the
# first authoritative transition (submit) is human-only.
domain_ok if {
	input.action == "exception.submit"
	submit_ok
}
submit_ok if {
	not agent_principal
	transition_allowed
	is_author_or_designee
}

# exception.approve — protected domain command.
domain_ok if {
	input.action == "exception.approve"
	approve_ok
}
approve_ok if {
	not agent_principal
	not self_approval
	transition_allowed
	not expired
	eligible_approver
}

# exception.activate — protected domain command (third transition, eligible activator only).
domain_ok if {
	input.action == "exception.activate"
	activate_ok
}
activate_ok if {
	not agent_principal
	transition_allowed
	not expired
	eligible_activator
	not self_activated
}

# exception.revoke — protected domain command.
domain_ok if {
	input.action == "exception.revoke"
	transition_allowed
	not agent_principal
	not expired
}

transition_allowed if {
	current := object.get(input.resource, "state", object.get(input.environment, "state", ""))
	desired := object.get(input.environment, "desired_state", object.get(input.resource, "desired_state", ""))
	transitions := object.get(input.resource, "allowed_transitions", object.get(input.environment, "allowed_transitions", []))
	transitions[_] == desired
	desired != ""
}
# Fallback: if caller supplies only a target, require it to be a successor.
transition_allowed if {
	current := object.get(input.resource, "state", "")
	desired := object.get(input.environment, "desired_state", "")
	successor(current, desired)
}
successor(from, to) if { from == "draft"; to == "submitted" }
successor(from, to) if { from == "submitted"; to == "under_review" }
successor(from, to) if { from == "under_review"; to == "approved" }
successor(from, to) if { from == "under_review"; to == "rejected" }
successor(from, to) if { from == "approved"; to == "activated" }
successor(from, to) if { from == "approved"; to == "revoked" }
successor(from, to) if { from == "activated"; to == "expired" }
successor(from, to) if { from == "activated"; to == "revoked" }

expired if object.get(input.resource, "expired", object.get(input.environment, "expired", false)) == true

agent_principal if input.principal.principal_type == "agent"

self_approval if {
	requester := object.get(input.principal, "user_id", "")
	requester != ""
	requester == object.get(input.resource, "requester_id", "")
}

self_activated if {
	activator := object.get(input.environment, "activator_id", object.get(input.principal, "user_id", ""))
	activator == object.get(input.resource, "requester_id", "")
}

is_author_or_designee if {
	requester := object.get(input.principal, "user_id", "")
	requester == object.get(input.resource, "requester_id", "")
}
is_author_or_designee if object.get(input.resource, "author_designee", false) == true

eligible_approver if object.get(input.resource, "eligible_approver", object.get(input.environment, "eligible_approver", false)) == true

# Activation normally requires a controlled system transition or direct designation.
eligible_activator if object.get(input.resource, "eligible_activator", object.get(input.environment, "eligible_activator", false)) == true
eligible_activator if object.get(input.environment, "controlled_system_activation", false) == true
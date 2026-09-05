package fabric.authz.administration

import rego.v1

# membership.assign_role — protected command, tenant_admin only (role grant).
domain_ok if {
	input.action == "membership.assign_role"
	target_is_tenant_scope
}

target_is_tenant_scope if {
	target := object.get(input.resource, "applies_to_tenant", object.get(input.environment, "applies_to_tenant", ""))
	target == ""
	target := object.get(input.environment, "tenant_id", "")
	target != ""
}
target_is_tenant_scope if {
	object.get(input.resource, "applies_to_tenant", "") != ""
}

# break_glass.approve — protected command, dual control required.
domain_ok if {
	input.action == "break_glass.approve"
	dual_control_ok
	not agent_principal
}

dual_control_ok if {
	second_approved := object.get(input.resource, "second_approver_approved", object.get(input.environment, "second_approver_approved", false))
	second_approved == true
	approver_count := object.get(input.resource, "approver_count", 0)
	approver_count >= 2
}

agent_principal if input.principal.principal_type == "agent"
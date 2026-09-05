# global: default-deny entrypoint + shared helpers for the Fabric workflow authz.
#
# Declarative mirror of packages/shared/src/value_fabric/shared/authz/engine.py.
# The pure-Python engine loads the same data JSON directly, so behavior parity
# is enforced by construction. If OPA is present, run: opa eval --bundle .
# If OPA is absent, the Python engine is the runtime PDP and fails closed.

package fabric.authz

import rego.v1

# ---------------------------------------------------------------------------
# Entry point (default deny)
# ---------------------------------------------------------------------------
default allow := false

allow if {
	valid_request
	catalogued
	authorized_by_role
	principal_active
	not agent_forbidden
	tenant_ok
	domain_ok
	not static_sod_violation
}

valid_request if {
	object.get(input, "action", "")
	object.get(input, "principal", {})
	object.get(input.principal, "principal_type", "")
	object.get(input.principal, "principal_id", "")
}

catalogued if data.action_catalog.actions[_] == input.action

authorized_by_role if {
	some role in object.get(input.principal, "roles", [])
	data.baseline_roles.roles[role].actions[_] == input.action
}

principal_active := object.get(input.principal, "is_active", true)

agent_forbidden if {
	input.principal.principal_type == "agent"
	data.action_catalog.agent_forbidden[_] == input.action
}

# ---------------------------------------------------------------------------
# Tenant containment (ReBAC / RLS backstop)
# ---------------------------------------------------------------------------
res_tenant := object.get(input.resource, "tenant_id", null)
prin_tenant := object.get(input.principal, "tenant_id", null)

tenant_ok if res_tenant == null
tenant_ok if {
	not is_null(prin_tenant)
	not is_null(res_tenant)
	prin_tenant == res_tenant
}

# ---------------------------------------------------------------------------
# Static separation of duties (role pairs and action-source conflicts)
# ---------------------------------------------------------------------------
principal_has(role_name) if object.get(input.principal, "roles", [])[_] == role_name

static_sod_violation if {
	some pair in data.static_sod.pairs
	principal_has(pair[0])
	principal_has(pair[1])
}

# ---------------------------------------------------------------------------
# Per-domain rules live in child packages, so this entrypoint explicitly
# bridges each child package's decision into the global default-deny rule.
# ---------------------------------------------------------------------------
default domain_ok := false

domain_ok if data.fabric.authz.administration.domain_ok
domain_ok if data.fabric.authz.claims.domain_ok
domain_ok if data.fabric.authz.deliverables.domain_ok
domain_ok if data.fabric.authz.exceptions.domain_ok
domain_ok if data.fabric.authz.external_access.domain_ok
domain_ok if data.fabric.authz.opportunities.domain_ok

package fabric.authz.external_access

import rego.v1

# External viewer access: only allowed with a live, unrevoked external grant
# scoped to the tenant and resource; otherwise default deny.
domain_ok if external_access_ok

external_access_ok if {
	input.principal.principal_type == "external_viewer"
	grant := object.get(input.resource, "external_grant", object.get(input.environment, "external_grant", {}))
	grant.status == "active"
	grant.expired == false
	grant.revoked == false
	scope_match(input.environment, grant)
}

scope_match(env, grant) if {
	scope := object.get(grant, "scope_tenant", object.get(env, "tenant_id", ""))
	scope == object.get(env, "tenant_id", "")
}
scope_match(env, grant) if {
	object.get(grant, "resource_id", "") == object.get(env, "resource_id", "")
	object.get(grant, "action", "") == input.action
}
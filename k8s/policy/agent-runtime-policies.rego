package gate.tool_access

import rego.v1

# Default deny — all tool access requires explicit policy allow.
default allow := false

allow if {
    input.tenant_id != ""
    input.tool_name in input.allowed_tools
    not input.tool_name in input.denied_tools
    input.hourly_budget_remaining > 0
}

deny_reason := "missing_tenant" if {
    input.tenant_id == ""
}

deny_reason := "tool_not_in_abom" if {
    not input.tool_name in input.allowed_tools
}

deny_reason := "tool_explicitly_denied" if {
    input.tool_name in input.denied_tools
}

deny_reason := "budget_exhausted" if {
    input.hourly_budget_remaining <= 0
}

obligations contains "audit_tool_invocation" if {
    input.privilege_tier == "high_privilege"
}

obligations contains "audit_tool_invocation" if {
    input.privilege_tier == "elevated"
}

package gate.tool_access

import rego.v1

test_allows_allowed_tool_with_budget if {
    allow with input as {
        "tenant_id": "tenant-123",
        "tool_name": "calculate_roi",
        "allowed_tools": ["calculate_roi", "query_graph"],
        "denied_tools": [],
        "hourly_budget_remaining": 10,
        "privilege_tier": "standard",
    }
}

test_denies_missing_tenant if {
    not allow with input as {
        "tenant_id": "",
        "tool_name": "calculate_roi",
        "allowed_tools": ["calculate_roi"],
        "denied_tools": [],
        "hourly_budget_remaining": 10,
        "privilege_tier": "standard",
    }
    deny_reason == "missing_tenant" with input as {
        "tenant_id": "",
        "tool_name": "calculate_roi",
        "allowed_tools": ["calculate_roi"],
        "denied_tools": [],
        "hourly_budget_remaining": 10,
        "privilege_tier": "standard",
    }
}

test_denies_tool_not_in_abom if {
    not allow with input as {
        "tenant_id": "tenant-123",
        "tool_name": "delete_tenant",
        "allowed_tools": ["calculate_roi"],
        "denied_tools": [],
        "hourly_budget_remaining": 10,
        "privilege_tier": "standard",
    }
}

test_denies_explicitly_denied_tool if {
    not allow with input as {
        "tenant_id": "tenant-123",
        "tool_name": "export_to_crm",
        "allowed_tools": ["export_to_crm", "calculate_roi"],
        "denied_tools": ["export_to_crm"],
        "hourly_budget_remaining": 10,
        "privilege_tier": "standard",
    }
}

test_denies_exhausted_budget if {
    not allow with input as {
        "tenant_id": "tenant-123",
        "tool_name": "calculate_roi",
        "allowed_tools": ["calculate_roi"],
        "denied_tools": [],
        "hourly_budget_remaining": 0,
        "privilege_tier": "standard",
    }
}

test_elevated_obligation if {
    "audit_tool_invocation" in obligations with input as {
        "tenant_id": "tenant-123",
        "tool_name": "calculate_roi",
        "allowed_tools": ["calculate_roi"],
        "denied_tools": [],
        "hourly_budget_remaining": 10,
        "privilege_tier": "elevated",
    }
}

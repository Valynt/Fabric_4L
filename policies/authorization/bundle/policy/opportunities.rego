# fabric.authz.opportunities ? opportunity.lock_realization (design Section 12.3).
#
# Creating an immutable baseline requires the realization-owner relationship, a
# permitted lifecycle state, complete required approvals, no blocking dispute,
# and logical realization eligibility (an approval ceiling, or one of the
# finance/deal-desk/value-manager roles).

package fabric.authz.opportunities

import rego.v1

default allow := false

allow if {
    input.action == "opportunity.lock_realization"
    input.principal.type == "human"
    "workflow.realization_owner" in input.principal.workflow_roles
    input.resource.attributes.lifecycle_state in {"QUALIFIED", "COMMITTED", "WON"}
    input.resource.attributes.required_approvals_complete == true
    input.resource.attributes.blocking_dispute_count == 0
    logical_realization_eligible
}

logical_realization_eligible if {
    input.principal.approval_ceiling_usd != null
}
logical_realization_eligible if {
    count({role |
        some role in input.principal.workflow_roles
        role in {"workflow.finance_approver", "workflow.deal_desk", "workflow.value_manager"}
    }) > 0
}

# ??? Deny reasons ?????????????????????????????????????????????????????????

deny_reason contains "ROLE_MISSING" if {
    input.action == "opportunity.lock_realization"
    not "workflow.realization_owner" in input.principal.workflow_roles
}

deny_reason contains "POLICY_INPUT_INVALID" if {
    input.action == "opportunity.lock_realization"
    not input.resource.attributes.lifecycle_state in {"QUALIFIED", "COMMITTED", "WON"}
}

deny_reason contains "ROLE_MISSING" if {
    input.action == "opportunity.lock_realization"
    input.resource.attributes.required_approvals_complete != true
}

deny_reason contains "DISPUTE_OPEN" if {
    input.action == "opportunity.lock_realization"
    input.resource.attributes.blocking_dispute_count != 0
}

deny_reason contains "ROLE_MISSING" if {
    input.action == "opportunity.lock_realization"
    input.principal.approval_ceiling_usd == null
    not logical_realization_eligible
}

# ??? Obligations ??????????????????????????????????????????????????????????

obligations contains "write_audit_event" if {
    allow
}
obligations contains "require_idempotency_key" if {
    allow
}

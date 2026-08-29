# fabric.authz.claims ? claim.approve (design Section 11.2).
#
# Approval is authorized for a human working principal that is the bound
# economic reviewer, is not the author, reviews an already-validated claim at
# the requested model version within the approval ceiling, with no open
# dispute, and satisfies the realization constraint.

package fabric.authz.claims

import rego.v1

default allow := false

allow if {
    input.action == "claim.approve"
    input.principal.type == "human"
    "workflow.finance_approver" in input.principal.workflow_roles
    "economic_reviewer" in input.resource.relationships
    input.principal.id != input.resource.attributes.author_id
    input.resource.attributes.validation_state in {"REVIEWED", "DISPUTED_RESOLVED"}
    model_version_matches
    approval_ceiling_passes
    input.resource.attributes.open_dispute_count == 0
    realization_constraint_passes
}

# ??? Sub-conditions ???????????????????????????????????????????????????????

model_version_matches if {
    input.context.requested_model_version == null
}
model_version_matches if {
    input.context.requested_model_version != null
    input.resource.attributes.model_version == input.context.requested_model_version
}

approval_ceiling_passes if {
    input.principal.approval_ceiling_usd == null
}
approval_ceiling_passes if {
    input.principal.approval_ceiling_usd != null
    abs(input.resource.attributes.impact_usd) <= input.principal.approval_ceiling_usd
}

realization_constraint_passes if {
    input.resource.attributes.publication_state != "LOCKED_REALIZATION"
}
realization_constraint_passes if {
    input.resource.attributes.publication_state == "LOCKED_REALIZATION"
    "workflow.realization_owner" in input.principal.workflow_roles
}

# ??? Deny reasons ?????????????????????????????????????????????????????????

deny_reason contains "ROLE_MISSING" if {
    input.action == "claim.approve"
    not "workflow.finance_approver" in input.principal.workflow_roles
}

deny_reason contains "RELATIONSHIP_MISSING" if {
    input.action == "claim.approve"
    not "economic_reviewer" in input.resource.relationships
}

deny_reason contains "SELF_APPROVAL_FORBIDDEN" if {
    input.action == "claim.approve"
    input.principal.id == input.resource.attributes.author_id
}

deny_reason contains "POLICY_INPUT_INVALID" if {
    input.action == "claim.approve"
    not input.resource.attributes.validation_state in {"REVIEWED", "DISPUTED_RESOLVED"}
}

deny_reason contains "MODEL_VERSION_STALE" if {
    input.action == "claim.approve"
    input.context.requested_model_version != null
    input.resource.attributes.model_version != input.context.requested_model_version
}

deny_reason contains "APPROVAL_CEILING_EXCEEDED" if {
    input.action == "claim.approve"
    input.principal.approval_ceiling_usd != null
    abs(input.resource.attributes.impact_usd) > input.principal.approval_ceiling_usd
}

deny_reason contains "DISPUTE_OPEN" if {
    input.action == "claim.approve"
    input.resource.attributes.open_dispute_count != 0
}

deny_reason contains "REALIZATION_CONSTRAINT_FAILED" if {
    input.action == "claim.approve"
    input.resource.attributes.publication_state == "LOCKED_REALIZATION"
    not "workflow.realization_owner" in input.principal.workflow_roles
}

# ??? Obligations ??????????????????????????????????????????????????????????

obligations contains "record_approval_reason" if {
    allow
}

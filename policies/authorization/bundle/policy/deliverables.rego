# fabric.authz.deliverables ? deliverable.publish_external (design Section 11.3).
#
# Publication is authorized against a server-generated publication projection
# (all included claims approved, no open included dispute, quote matches the
# model) for a human principal holding a publication role, and requires the
# exception requirement to be satisfied and publisher soD to pass.

package fabric.authz.deliverables

import rego.v1

default allow := false

allow if {
    input.action == "deliverable.publish_external"
    input.principal.type == "human"
    publication_role
    input.resource.attributes.all_included_claims_approved == true
    input.resource.attributes.open_included_dispute_count == 0
    input.resource.attributes.quote_matches_model == true
    exception_requirement_passes
    publisher_sod_passes
}

publication_role if {
    "workflow.deal_desk" in input.principal.workflow_roles
}
publication_role if {
    "workflow.value_manager" in input.principal.workflow_roles
}

# If no exception is required, nothing more is needed. If one is required it
# must be ACTIVATED, unexpired, and cover the deliverable.
exception_requirement_passes if {
    input.resource.attributes.exception_required == false
}
exception_requirement_passes if {
    input.resource.attributes.exception_required == true
    input.resource.attributes.exception_state == "ACTIVATED"
    time.parse_rfc3339_ns(input.context.now) < time.parse_rfc3339_ns(input.resource.attributes.exception_expires_at)
    input.resource.attributes.exception_covers_deliverable == true
}

# SoD between publisher and the economic reviewer is enforced at the
# membership layer; the projection carries only a boolean verdict here.
publisher_sod_passes if {
    not input.resource.attributes.publisher_sod_ok == false
}

# ??? Deny reasons ?????????????????????????????????????????????????????????

deny_reason contains "ROLE_MISSING" if {
    input.action == "deliverable.publish_external"
    not publication_role
}

deny_reason contains "PUBLICATION_BLOCKED" if {
    input.action == "deliverable.publish_external"
    publication_role
    not input.resource.attributes.all_included_claims_approved == true
}

deny_reason contains "DISPUTE_OPEN" if {
    input.action == "deliverable.publish_external"
    input.resource.attributes.open_included_dispute_count != 0
}

deny_reason contains "PUBLICATION_BLOCKED" if {
    input.action == "deliverable.publish_external"
    publication_role
    not input.resource.attributes.quote_matches_model == true
}

deny_reason contains "EXCEPTION_NOT_ACTIVATED" if {
    input.action == "deliverable.publish_external"
    input.resource.attributes.exception_required == true
    input.resource.attributes.exception_state != "ACTIVATED"
}

deny_reason contains "EXCEPTION_EXPIRED" if {
    input.action == "deliverable.publish_external"
    input.resource.attributes.exception_required == true
    input.resource.attributes.exception_state == "ACTIVATED"
    time.parse_rfc3339_ns(input.context.now) >= time.parse_rfc3339_ns(input.resource.attributes.exception_expires_at)
}

deny_reason contains "EXCEPTION_SCOPE_MISMATCH" if {
    input.action == "deliverable.publish_external"
    input.resource.attributes.exception_required == true
    input.resource.attributes.exception_state == "ACTIVATED"
    input.resource.attributes.exception_covers_deliverable != true
}

deny_reason contains "SOD_FAILED" if {
    input.action == "deliverable.publish_external"
    input.resource.attributes.publisher_sod_ok == false
}

# ??? Obligations ??????????????????????????????????????????????????????????

obligations contains "watermark_provisional" if {
    allow
}
obligations contains "write_audit_event" if {
    allow
}

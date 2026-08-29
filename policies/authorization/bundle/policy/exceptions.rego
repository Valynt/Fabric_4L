# fabric.authz.exceptions ? exception.activate (design Section 11.4).
#
# Activation requires the named approver (who is not the requester), an
# APPROVED exception, policy eligibility PASS, non-empty scope, and an
# unexpired approval window. Submission never activates; approval never
# silently publishes.

package fabric.authz.exceptions

import rego.v1

default allow := false

allow if {
    input.action == "exception.activate"
    input.principal.type == "human"
    input.principal.id == input.resource.attributes.approver_id
    input.principal.id != input.resource.attributes.requester_id
    input.resource.attributes.state == "APPROVED"
    input.resource.attributes.policy_eligibility == "PASS"
    input.resource.attributes.scope_non_empty == true
    activation_window_ok
}

activation_window_ok if {
    input.resource.attributes.approval_expires_at == null
}
activation_window_ok if {
    input.resource.attributes.approval_expires_at != null
    time.parse_rfc3339_ns(input.context.now) < time.parse_rfc3339_ns(input.resource.attributes.approval_expires_at)
}

# ??? Deny reasons ?????????????????????????????????????????????????????????

deny_reason contains "RELATIONSHIP_MISSING" if {
    input.action == "exception.activate"
    input.principal.id != input.resource.attributes.approver_id
}

deny_reason contains "SELF_APPROVAL_FORBIDDEN" if {
    input.action == "exception.activate"
    input.principal.id == input.resource.attributes.requester_id
}

deny_reason contains "EXCEPTION_NOT_ACTIVATED" if {
    input.action == "exception.activate"
    not input.resource.attributes.state == "APPROVED"
}

deny_reason contains "EXCEPTION_NOT_ACTIVATED" if {
    input.action == "exception.activate"
    not input.resource.attributes.policy_eligibility == "PASS"
}

deny_reason contains "EXCEPTION_SCOPE_MISMATCH" if {
    input.action == "exception.activate"
    input.resource.attributes.scope_non_empty != true
}

deny_reason contains "EXCEPTION_EXPIRED" if {
    input.action == "exception.activate"
    input.resource.attributes.approval_expires_at != null
    time.parse_rfc3339_ns(input.context.now) >= time.parse_rfc3339_ns(input.resource.attributes.approval_expires_at)
}

# ??? Obligations ??????????????????????????????????????????????????????????

obligations contains "write_audit_event" if {
    allow
}

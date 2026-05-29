from __future__ import annotations

"""Structured pause point definitions for human-in-the-loop workflows.

Defines typed pause point schemas that enable contextual user interactions
when workflows require human input or approval.
"""


from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class PauseReason(str, Enum):
    """Reasons why a workflow may pause for human input."""

    MISSING_DATA = "missing_data"  # Required input data unavailable
    MISSING_BENCHMARK = "missing_benchmark"  # Benchmark data not found
    APPROVAL_REQUIRED = "approval_required"  # Human approval needed before proceeding
    CLARIFICATION_NEEDED = "clarification_needed"  # Ambiguous input requires clarification
    EXTERNAL_API_FAILURE = "external_api_failure"  # External service unavailable, manual fallback
    VALIDATION_ERROR = "validation_error"  # Data validation failed, needs correction
    BUDGET_THRESHOLD = "budget_threshold"  # ROI/Budget threshold crossed, needs review
    CUSTOM_PAUSE = "custom_pause"  # Workflow-specific pause point


class PauseSeverity(str, Enum):
    """Severity level of the pause - determines notification urgency."""

    INFO = "info"  # Informational, can wait
    WARNING = "warning"  # Should be addressed soon
    CRITICAL = "critical"  # Blocks progress, immediate attention needed


class InputField(BaseModel):
    """Definition of a required input field for resume."""

    name: str = Field(..., description="Field identifier")
    label: str = Field(..., description="Human-readable label")
    field_type: str = Field(
        default="text", description="Input type: text, number, select, boolean, textarea"
    )
    required: bool = Field(default=True, description="Whether field is required")
    default_value: Any | None = Field(None, description="Default value if any")
    options: list[dict[str, str]] | None = Field(None, description="Options for select fields")
    validation_regex: str | None = Field(None, description="Regex pattern for validation")
    min_value: float | None = Field(None, description="Minimum value for numbers")
    max_value: float | None = Field(None, description="Maximum value for numbers")
    placeholder: str | None = Field(None, description="Placeholder text")
    help_text: str | None = Field(None, description="Additional help/instructions")


class PauseContext(BaseModel):
    """Context information to help user understand what happened."""

    node_id: str = Field(..., description="ID of the node that triggered the pause")
    node_name: str = Field(..., description="Human-readable node name")
    step_number: int = Field(default=0, description="Step number in workflow sequence")
    total_steps: int = Field(default=0, description="Total steps in workflow")
    elapsed_seconds: int = Field(default=0, description="Seconds elapsed since workflow started")
    previous_outputs: dict[str, Any] = Field(
        default_factory=dict, description="Outputs from previous nodes"
    )
    error_details: str | None = Field(None, description="Error message if pause due to failure")


class PausePoint(BaseModel):
    """Structured pause point for human-in-the-loop workflows.

    Provides rich context when workflows pause for user input, enabling
    the UI to render contextual forms, notifications, and help text.

    Attributes:
        pause_id: Unique identifier for this pause point
        reason: Why the workflow paused
        severity: Urgency level affecting notifications
        title: Short title for the pause (displayed in UI)
        message: Detailed message explaining what is needed
        help_text: Additional guidance on how to proceed
        required_inputs: Fields the user must provide to resume
        validation_schema: JSON Schema for validating resume_data
        context: Execution context (current node, progress, etc.)
        estimated_wait_seconds: Seconds until auto-resume attempt (if applicable)
        auto_resume_on: Conditions for automatic resumption
        expires_at: When this pause point expires (optional timeout)
        created_at: When this pause point was created
    """

    pause_id: str = Field(default_factory=lambda: str(uuid4()))
    reason: PauseReason
    severity: PauseSeverity = PauseSeverity.WARNING
    title: str = Field(..., description="Short title for display in UI")
    message: str = Field(..., description="Detailed explanation of what is needed")
    help_text: str | None = Field(None, description="Additional guidance for user")
    required_inputs: list[InputField] = Field(
        default_factory=list, description="Fields needed to resume"
    )
    validation_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for resume_data"
    )
    context: PauseContext | None = Field(None, description="Execution context")
    estimated_wait_seconds: int | None = Field(
        None, description="Seconds until auto-resume (if any)"
    )
    auto_resume_conditions: dict[str, Any] | None = Field(
        None, description="Conditions for auto-resumption"
    )
    expires_at: datetime | None = Field(None, description="Pause expiration time")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_pause_point(self) -> PausePoint:
        """Validate pause point consistency."""
        # Ensure required_inputs has entries if pause reason is missing_data
        if self.reason == PauseReason.MISSING_DATA and not self.required_inputs:
            raise ValueError("MISSING_DATA pause points must specify required_inputs")

        # Validate severity aligns with reason
        if self.reason == PauseReason.APPROVAL_REQUIRED and self.severity == PauseSeverity.INFO:
            # Approval typically shouldn't be just info level
            pass  # But allow it if explicitly set

        return self

    def to_resume_prompt(self) -> str:
        """Generate a user-friendly prompt for this pause point."""
        lines = [
            f"## {self.title}",
            "",
            self.message,
            "",
        ]

        if self.help_text:
            lines.extend([self.help_text, ""])

        if self.required_inputs:
            lines.append("### Required Information:")
            for field in self.required_inputs:
                req_marker = " (required)" if field.required else ""
                lines.append(
                    f"- **{field.label}**{req_marker}: {field.help_text or field.field_type}"
                )

        if self.context:
            lines.extend(
                ["", f"_Progress: Step {self.context.step_number} of {self.context.total_steps}_"]
            )

        return "\n".join(lines)


class PausePointTemplate(BaseModel):
    """Reusable template for creating pause points.

    Allows workflows to define pause point patterns that can be
    instantiated with specific context.
    """

    template_id: str = Field(..., description="Template identifier")
    reason: PauseReason
    severity: PauseSeverity
    title_template: str = Field(..., description="Title with {placeholders}")
    message_template: str = Field(..., description="Message with {placeholders}")
    help_text_template: str | None = Field(None, description="Help text with {placeholders}")
    default_inputs: list[InputField] = Field(default_factory=list)

    def instantiate(
        self,
        context: PauseContext,
        placeholders: dict[str, str],
        custom_inputs: list[InputField] | None = None,
    ) -> PausePoint:
        """Create a PausePoint from this template."""
        title = self.title_template.format(**placeholders)
        message = self.message_template.format(**placeholders)
        help_text = (
            self.help_text_template.format(**placeholders) if self.help_text_template else None
        )

        return PausePoint(
            reason=self.reason,
            severity=self.severity,
            title=title,
            message=message,
            help_text=help_text,
            required_inputs=custom_inputs or self.default_inputs,
            context=context,
        )


# Predefined pause point templates for common scenarios
PAUSE_TEMPLATES: dict[str, PausePointTemplate] = {
    "missing_benchmark": PausePointTemplate(
        template_id="missing_benchmark",
        reason=PauseReason.MISSING_BENCHMARK,
        severity=PauseSeverity.WARNING,
        title_template="Benchmark Data Unavailable",
        message_template="Unable to find benchmark data for {industry_vertical}. "
        "Please provide benchmark values or select an alternative industry.",
        help_text_template="You can enter approximate values based on your knowledge of {industry_vertical} "
        "or choose a similar industry from our database.",
        default_inputs=[
            InputField(
                name="industry_vertical",
                label="Industry Vertical",
                field_type="select",
                required=True,
                options=[
                    {"value": "software", "label": "Software/SaaS"},
                    {"value": "manufacturing", "label": "Manufacturing"},
                    {"value": "healthcare", "label": "Healthcare"},
                    {"value": "financial", "label": "Financial Services"},
                ],
            ),
            InputField(
                name="benchmark_revenue_impact",
                label="Benchmark Revenue Impact (%)",
                field_type="number",
                required=False,
                min_value=0,
                max_value=100,
                placeholder="e.g., 15",
            ),
        ],
    ),
    "approval_required": PausePointTemplate(
        template_id="approval_required",
        reason=PauseReason.APPROVAL_REQUIRED,
        severity=PauseSeverity.CRITICAL,
        title_template="Approval Required: {step_name}",
        message_template="The workflow has reached {step_name} and requires your approval before proceeding.",
        help_text_template="Please review the outputs from previous steps and confirm approval to continue.",
        default_inputs=[
            InputField(
                name="approved",
                label="Approve and Continue",
                field_type="boolean",
                required=True,
                default_value=False,
            ),
            InputField(
                name="approval_notes",
                label="Approval Notes (Optional)",
                field_type="textarea",
                required=False,
                placeholder="Add any notes or conditions for this approval",
            ),
        ],
    ),
    "missing_prospect_data": PausePointTemplate(
        template_id="missing_prospect_data",
        reason=PauseReason.MISSING_DATA,
        severity=PauseSeverity.WARNING,
        title_template="Missing Prospect Data",
        message_template="Required prospect data is missing: {missing_fields}. "
        "Please provide this information to continue.",
        default_inputs=[
            InputField(
                name="company_size",
                label="Company Size (employees)",
                field_type="select",
                required=True,
                options=[
                    {"value": "1-50", "label": "1-50"},
                    {"value": "51-200", "label": "51-200"},
                    {"value": "201-1000", "label": "201-1000"},
                    {"value": "1000+", "label": "1000+"},
                ],
            ),
            InputField(
                name="annual_revenue",
                label="Annual Revenue (USD)",
                field_type="number",
                required=False,
                min_value=0,
                placeholder="e.g., 10000000",
            ),
        ],
    ),
}

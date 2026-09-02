from __future__ import annotations

"""Workflows package for Layer 4 Agentic Workflow Orchestrator."""


from typing import Any

from value_fabric.shared.models.typed_dict import TypedDictModel

from .base import BaseWorkflow, NodeExecutionError, WorkflowBuilder, WorkflowError
from .business_case import BusinessCaseGeneratorWorkflow
from .roi_calculator import ROICalculatorWorkflow
from .whitespace import WhitespaceAnalysisWorkflow


class list_workflow_typesResult(TypedDictModel):
    business_case: dict[str, Any]
    roi_calculator: dict[str, Any]
    whitespace_analysis: dict[str, Any]

# Workflow type registry
WORKFLOW_TYPES = {
    "roi_calculator": ROICalculatorWorkflow,
    "whitespace_analysis": WhitespaceAnalysisWorkflow,
    "business_case": BusinessCaseGeneratorWorkflow,
}


def register_workflow_type(workflow_type: str, workflow_class: type[BaseWorkflow]) -> None:
    """Register a new workflow type dynamically.

    Allows packs and extensions to inject workflows without modifying
    core code. Existing types may not be overwritten.

    Args:
        workflow_type: Unique type identifier
        workflow_class: Workflow class inheriting from BaseWorkflow

    Raises:
        ValueError: If the type identifier is already registered
    """
    if workflow_type in WORKFLOW_TYPES:
        raise ValueError(f"Workflow type {workflow_type!r} is already registered")
    WORKFLOW_TYPES[workflow_type] = workflow_class


def create_workflow(
    workflow_type: str,
    tool_registry,
    checkpoint_saver=None,
    tool_gateway=None,
) -> BaseWorkflow:
    """Create a workflow instance by type.

    Args:
        workflow_type: Type identifier (e.g., "roi_calculator")
        tool_registry: Tool registry for workflow
        checkpoint_saver: Optional checkpoint saver
        tool_gateway: Optional policy-enforced tool gateway

    Returns:
        Workflow instance

    Raises:
        ValueError: If workflow type is unknown
    """
    if workflow_type not in WORKFLOW_TYPES:
        raise ValueError(f"Unknown workflow type: {workflow_type}")

    workflow_class = WORKFLOW_TYPES[workflow_type]
    if workflow_type == "business_case":
        from layer4_agents.adapters.business_case_ground_truth import (
            create_layer5_business_case_ground_truth_client,
        )

        return workflow_class(
            tool_registry,
            checkpoint_saver,
            ground_truth_client_factory=create_layer5_business_case_ground_truth_client,
            tool_gateway=tool_gateway,
        )
    return workflow_class(tool_registry, checkpoint_saver, tool_gateway=tool_gateway)


def list_workflow_types() -> dict:
    """List available workflow types and their descriptions."""
    return list_workflow_typesResult.model_validate({
        "roi_calculator": {
            "name": "ROI Calculator",
            "description": "Calculates ROI from value driver formulas with prospect data",
            "class": ROICalculatorWorkflow,
        },
        "whitespace_analysis": {
            "name": "Whitespace Analysis",
            "description": "Identifies gaps between prospect needs and solution capabilities",
            "class": WhitespaceAnalysisWorkflow,
        },
        "business_case": {
            "name": "Business Case Generator",
            "description": "Generates comprehensive business case documents",
            "class": BusinessCaseGeneratorWorkflow,
        },
    })


__all__ = [
    # Base
    "BaseWorkflow",
    "WorkflowError",
    "NodeExecutionError",
    "WorkflowBuilder",
    # Workflows
    "ROICalculatorWorkflow",
    "WhitespaceAnalysisWorkflow",
    "BusinessCaseGeneratorWorkflow",
    # Factory
    "create_workflow",
    "list_workflow_types",
    "register_workflow_type",
    "WORKFLOW_TYPES",
]

# mypy: ignore-missing-imports, disable-error-code="import-not-found,no-untyped-def,no-any-return,no-untyped-call,attr-defined,misc,union-attr,arg-type,assignment,var-annotated,return-value"
"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Narrative Synthesis Agent.

Implements template-based narrative generation for:
- Executive summaries
- Slide decks
- Risk proposals
- Board presentations
"""

import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, cast

from value_fabric.shared.models.typed_dict import TypedDictModel

from .base import AgentResult, BaseAgent


class NarrativeSynthesisAgent__generate_executive_summaryResult(TypedDictModel):
    content: dict[str, Any]
    format: Any
    generated_at: Any
    narrative_id: str
    structured_data: dict[str, Any]
    template_used: Any
    title: Any

class NarrativeSynthesisAgent__generate_slide_deckResult(TypedDictModel):
    format: Any
    generated_at: Any
    narrative_id: str
    slide_count: Any
    slides: Any
    template_used: Any
    title: Any

class NarrativeSynthesisAgent__generate_risk_proposalResult(TypedDictModel):
    content: dict[str, Any]
    format: Any
    generated_at: Any
    narrative_id: str
    structured_data: dict[str, Any]
    template_used: Any
    title: Any

logger = logging.getLogger(__name__)


class OutputFormat(Enum):
    """Supported output formats for narrative generation."""

    EXECUTIVE_SUMMARY = "executive_summary"
    SLIDE_DECK = "slide_deck"
    RISK_PROPOSAL = "risk_proposal"
    TECHNICAL_SPEC = "technical_spec"
    BOARD_PRESENTATION = "board_presentation"


@dataclass
class Template:
    """Template for narrative generation."""

    template_id: str
    name: str
    description: str
    format_type: str
    version: str
    content: str  # Jinja2-style template
    variables: list[dict[str, Any]]
    styles: dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True


@dataclass
class SynthesizedNarrative:
    """Synthesized narrative output."""

    narrative_id: str
    format: OutputFormat
    title: str
    content: dict[str, Any]
    raw_text: str
    structured_data: dict[str, Any]
    generated_at: datetime
    template_used: str
    customization_applied: dict[str, Any]


class NarrativeSynthesisAgent(BaseAgent):
    """Agent for narrative synthesis and report generation.

    Capabilities:
    - executive_summary_generation: Generate executive summaries
    - slide_deck_creation: Create structured slide decks
    - risk_proposal_drafting: Draft risk mitigation proposals
    - stakeholder_alignment: Align messaging for stakeholders
    """

    # Default templates
    DEFAULT_TEMPLATES: ClassVar[dict[str, dict[str, Any]]] = {
        "executive_summary_v2": {
            "name": "Executive Summary",
            "format": OutputFormat.EXECUTIVE_SUMMARY,
            "content": """
# Executive Summary: {title}

## Overview
{overview}

## Key Findings
{findings}

## Recommended Actions
{recommendations}

## Financial Impact
- Total Investment: {total_investment}
- Expected ROI: {expected_roi}
- Payback Period: {payback_period}

## Risk Assessment
{risk_assessment}

## Next Steps
{next_steps}
""",
        },
        "slide_deck_standard_v3": {
            "name": "Standard Slide Deck",
            "format": OutputFormat.SLIDE_DECK,
            "slides": [
                {"slide_number": 1, "layout": "title", "title": "{title}"},
                {
                    "slide_number": 2,
                    "layout": "executive_summary",
                    "title": "Executive Summary",
                    "content": "{executive_summary}",
                },
                {
                    "slide_number": 3,
                    "layout": "challenges",
                    "title": "Current State Challenges",
                    "content": "{challenges}",
                },
                {
                    "slide_number": 4,
                    "layout": "solution",
                    "title": "Proposed Solution",
                    "content": "{solution}",
                },
                {
                    "slide_number": 5,
                    "layout": "financial",
                    "title": "Financial Analysis",
                    "content": "{financial_analysis}",
                },
                {
                    "slide_number": 6,
                    "layout": "sensitivity",
                    "title": "Sensitivity Analysis",
                    "content": "{sensitivity_analysis}",
                },
                {
                    "slide_number": 7,
                    "layout": "roadmap",
                    "title": "Implementation Roadmap",
                    "content": "{roadmap}",
                },
                {
                    "slide_number": 8,
                    "layout": "risks",
                    "title": "Risk Mitigation",
                    "content": "{risks}",
                },
                {
                    "slide_number": 9,
                    "layout": "next_steps",
                    "title": "Recommended Next Steps",
                    "content": "{next_steps}",
                },
            ],
        },
        "risk_proposal_v1": {
            "name": "Risk Mitigation Proposal",
            "format": OutputFormat.RISK_PROPOSAL,
            "content": """
# Risk Mitigation Proposal: {title}

## Risk Description
{risk_description}

## Current Exposure
- Likelihood: {likelihood}
- Impact: {impact}
- Current Mitigation: {current_mitigation}

## Proposed Solution
{proposed_solution}

## Implementation Plan
{implementation_plan}

## Cost-Benefit Analysis
{cost_benefit_analysis}

## Approval Request
{approval_request}
""",
        },
    }

    # Template filters for formatting
    TEMPLATE_FILTERS: ClassVar[dict[str, Callable[[Any], str]]] = {
        "currency": lambda x: f"${x:,.2f}" if isinstance(x, (int, float)) else str(x),
        "percentage": lambda x: f"{x:.1f}%" if isinstance(x, (int, float)) else str(x),
        "number": lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) else str(x),
        "month_year": lambda x: (
            x.strftime("%B %Y") if hasattr(x, "strftime") else str(x)
        ),
    }

    def __init__(self) -> None:
        """Initialize narrative synthesis agent."""
        super().__init__("NarrativeSynthesisAgent")
        self.templates = self._load_templates()

    def _load_templates(self) -> dict[str, Template]:
        """Load default templates."""
        templates: dict[str, Template] = {}

        for template_id, template_def in self.DEFAULT_TEMPLATES.items():
            template_name = str(template_def["name"])
            format_type = cast(OutputFormat, template_def["format"])
            templates[template_id] = Template(
                template_id=template_id,
                name=template_name,
                description=f"Default {template_name} template",
                format_type=format_type.value,
                version="1.0",
                content=str(template_def.get("content", "")),
                variables=[],  # Would be extracted from template
                styles={},
                created_by="system",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

        return templates

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        """Execute narrative synthesis.

        Args:
            context: Must contain:
                - operation: 'generate_executive_summary', 'generate_slide_deck', 'generate_proposal'
                - template_id: Template to use
                - data: Data for template substitution
                - title: Document title

        Returns:
            AgentResult with synthesized narrative
        """
        start_time = time.time()

        try:
            operation = context.get("operation", "generate_executive_summary")
            template_id = context.get("template_id", "executive_summary_v2")
            data = context.get("data", {})
            title = context.get("title", "Business Case")

            if operation == "generate_executive_summary":
                result = await self._generate_executive_summary(
                    title, data, template_id
                )
            elif operation == "generate_slide_deck":
                result = await self._generate_slide_deck(title, data, template_id)
            elif operation == "generate_proposal":
                result = await self._generate_risk_proposal(title, data, template_id)
            else:
                return self._create_result(
                    status="failed",
                    output={},
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    errors=[f"Unknown operation: {operation}"],
                )

            return self._create_result(
                status="success",
                output=result,
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        except Exception as e:
            logger.error(f"Narrative synthesis failed: {e}")
            return self._create_result(
                status="failed",
                output={},
                execution_time_ms=int((time.time() - start_time) * 1000),
                errors=["agent_execution_failed"],
            )

    async def _generate_executive_summary(
        self, title: str, data: dict[str, Any], template_id: str
    ) -> dict[str, Any]:
        """Generate executive summary.

        Args:
            title: Document title
            data: Template data
            template_id: Template ID

        Returns:
            Dict with generated summary
        """
        template = (
            self.templates.get(template_id) or self.templates["executive_summary_v2"]
        )

        # Apply template filters
        formatted_data = self._apply_filters(data)

        # Simple template substitution (in production, use Jinja2)
        content = self._substitute_template(template.content, formatted_data)

        return NarrativeSynthesisAgent__generate_executive_summaryResult.model_validate({
            "narrative_id": f"exec-summary-{int(time.time())}",
            "format": OutputFormat.EXECUTIVE_SUMMARY.value,
            "title": title,
            "content": {
                "sections": self._parse_sections(content),
                "full_text": content,
            },
            "structured_data": {
                "key_metrics": self._extract_metrics(data),
                "recommendations": data.get("recommendations", []),
                "risks": data.get("risk_assessment", {}).get("risks", []),
            },
            "template_used": template_id,
            "generated_at": datetime.utcnow().isoformat(),
        }).model_dump()


    async def _generate_slide_deck(
        self, title: str, data: dict[str, Any], template_id: str
    ) -> dict[str, Any]:
        """Generate slide deck structure.

        Args:
            title: Presentation title
            data: Template data
            template_id: Template ID

        Returns:
            Dict with slide deck structure
        """
        template_def = self.DEFAULT_TEMPLATES["slide_deck_standard_v3"]
        slide_defs = cast(list[dict[str, Any]], template_def.get("slides", []))
        slides: list[dict[str, Any]] = []

        formatted_data = self._apply_filters(data)

        for slide_def in slide_defs:
            slide_content = self._substitute_template(
                slide_def.get("content", ""), formatted_data
            )

            slides.append(
                {
                    "slide_number": slide_def["slide_number"],
                    "layout": slide_def["layout"],
                    "title": self._substitute_template(
                        slide_def["title"], formatted_data
                    ),
                    "content": slide_content,
                    "notes": self._generate_speaker_notes(
                        slide_def["layout"], formatted_data
                    ),
                }
            )

        return NarrativeSynthesisAgent__generate_slide_deckResult.model_validate({
            "narrative_id": f"slide-deck-{int(time.time())}",
            "format": OutputFormat.SLIDE_DECK.value,
            "title": title,
            "slide_count": len(slides),
            "slides": slides,
            "template_used": template_id,
            "generated_at": datetime.utcnow().isoformat(),
        }).model_dump()


    async def _generate_risk_proposal(
        self, title: str, data: dict[str, Any], template_id: str
    ) -> dict[str, Any]:
        """Generate risk mitigation proposal.

        Args:
            title: Proposal title
            data: Template data
            template_id: Template ID

        Returns:
            Dict with generated proposal
        """
        template = self.templates.get(template_id) or self.templates["risk_proposal_v1"]

        formatted_data = self._apply_filters(data)
        content = self._substitute_template(template.content, formatted_data)

        return NarrativeSynthesisAgent__generate_risk_proposalResult.model_validate({
            "narrative_id": f"risk-proposal-{int(time.time())}",
            "format": OutputFormat.RISK_PROPOSAL.value,
            "title": title,
            "content": {
                "sections": self._parse_sections(content),
                "full_text": content,
            },
            "structured_data": {
                "risk_level": self._calculate_risk_level(data),
                "mitigation_cost": data.get("mitigation_cost"),
                "approval_threshold": self._determine_approval_threshold(data),
            },
            "template_used": template_id,
            "generated_at": datetime.utcnow().isoformat(),
        }).model_dump()


    def _apply_filters(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply template filters to data values.

        Args:
            data: Input data

        Returns:
            Data with filters applied
        """
        result: dict[str, Any] = {}

        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self._apply_filters(value)
            elif isinstance(value, (int, float)):
                # Auto-apply appropriate formatting based on key name
                if any(
                    x in key.lower()
                    for x in [
                        "cost",
                        "investment",
                        "revenue",
                        "savings",
                        "price",
                        "value",
                        "roi",
                    ]
                ):
                    result[key] = self.TEMPLATE_FILTERS["currency"](value)
                elif any(
                    x in key.lower()
                    for x in ["rate", "percentage", "percent", "growth"]
                ):
                    result[key] = self.TEMPLATE_FILTERS["percentage"](value)
                else:
                    result[key] = self.TEMPLATE_FILTERS["number"](value)
            else:
                result[key] = value

        return result

    def _substitute_template(self, template: str, data: dict[str, Any]) -> str:
        """Simple template substitution.

        In production, use Jinja2 for proper templating.

        Args:
            template: Template string with {variable} placeholders
            data: Substitution data

        Returns:
            Substituted string
        """
        result = template

        # Flatten nested data for substitution
        flat_data = self._flatten_dict(data)

        for key, value in flat_data.items():
            placeholder = "{" + key + "}"
            result = result.replace(placeholder, str(value))

        # Remove unfilled placeholders
        result = re.sub(r"\{[^}]+\}", "", result)

        return result

    def _flatten_dict(
        self, d: dict[str, Any], parent_key: str = "", sep: str = "."
    ) -> dict[str, Any]:
        """Flatten nested dictionary.

        Args:
            d: Dictionary to flatten
            parent_key: Parent key prefix
            sep: Separator for nested keys

        Returns:
            Flattened dictionary
        """
        items: list[tuple[str, Any]] = []

        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k

            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep).items())
            else:
                items.append((new_key, v))

        return dict(items)

    def _parse_sections(self, content: str) -> list[dict[str, str]]:
        """Parse markdown-style sections.

        Args:
            content: Markdown content

        Returns:
            List of section dicts
        """
        sections: list[dict[str, str]] = []
        lines = content.split("\n")
        current_section: str | None = None
        current_content: list[str] = []

        for line in lines:
            if line.startswith("# "):
                # Title, skip
                continue
            elif line.startswith("## "):
                # Save previous section
                if current_section:
                    sections.append(
                        {
                            "title": current_section,
                            "content": "\n".join(current_content).strip(),
                        }
                    )

                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_section:
            sections.append(
                {
                    "title": current_section,
                    "content": "\n".join(current_content).strip(),
                }
            )

        return sections

    def _extract_metrics(self, data: dict[str, Any]) -> dict[str, Any]:
        """Extract key metrics from data.

        Args:
            data: Input data

        Returns:
            Dict of metrics
        """
        metrics: dict[str, Any] = {}

        metric_keys = [
            "total_investment",
            "expected_roi",
            "payback_period",
            "net_present_value",
            "internal_rate_of_return",
            "total_savings",
            "revenue_increase",
            "cost_reduction",
        ]

        for key in metric_keys:
            if key in data:
                metrics[key] = data[key]

        return metrics

    def _generate_speaker_notes(self, layout: str, data: dict[str, Any]) -> str:
        """Generate speaker notes for a slide.

        Args:
            layout: Slide layout type
            data: Slide data

        Returns:
            Speaker notes
        """
        notes_map = {
            "title": "Introduce the proposal and establish context.",
            "executive_summary": "Focus on the 3 key takeaways. Emphasize ROI and timeline.",
            "challenges": "Connect challenges to business impact. Use specific examples.",
            "solution": "Walk through the solution approach. Highlight key differentiators.",
            "financial": "Explain the numbers. Be prepared for detailed questions.",
            "sensitivity": "Discuss variables that could affect outcomes. Show scenarios.",
            "roadmap": "Outline phases and milestones. Identify critical dependencies.",
            "risks": "Be transparent about risks. Emphasize mitigation strategies.",
            "next_steps": "Be clear on decision timeline. Define next actions.",
        }

        return notes_map.get(layout, "No specific notes available.")

    def _calculate_risk_level(self, data: dict[str, Any]) -> str:
        """Calculate overall risk level.

        Args:
            data: Risk data

        Returns:
            Risk level string
        """
        likelihood = data.get("likelihood", "Medium")
        impact = data.get("impact", "Medium")

        risk_matrix = {
            ("High", "High"): "Critical",
            ("High", "Medium"): "High",
            ("Medium", "High"): "High",
            ("High", "Low"): "Medium",
            ("Low", "High"): "Medium",
            ("Medium", "Medium"): "Medium",
            ("Medium", "Low"): "Low",
            ("Low", "Medium"): "Low",
            ("Low", "Low"): "Low",
        }

        return risk_matrix.get((likelihood, impact), "Medium")

    def _determine_approval_threshold(self, data: dict[str, Any]) -> str:
        """Determine approval authority needed.

        Args:
            data: Proposal data

        Returns:
            Approval threshold description
        """
        cost = data.get("mitigation_cost", 0)

        if isinstance(cost, str):
            # Try to parse currency string
            cost = float(re.sub(r"[^\d.]", "", cost))

        if cost > 1000000:
            return "Board approval required"
        elif cost > 500000:
            return "C-level approval required"
        elif cost > 100000:
            return "VP approval required"
        else:
            return "Director approval sufficient"

from __future__ import annotations

"""Document export tool for generating PDFs from business cases."""
import asyncio
import logging
from datetime import datetime
from io import BytesIO
from typing import Any

import aiofiles
from jinja2 import Template, select_autoescape

# Optional weasyprint import - allows tests to run without it
try:
    from weasyprint import HTML

    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    # OSError: missing GTK system libraries on Windows
    WEASYPRINT_AVAILABLE = False
    HTML = None  # type: ignore

from ..models.tool_schemas import ExportDocumentInput, ExportDocumentOutput, ToolCategory
from .registry import BaseTool

logger = logging.getLogger(__name__)


# Default business case PDF template
BUSINESS_CASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>
        @page {
            size: letter;
            margin: 1in;
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 9pt;
                color: #666;
            }
        }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
        }
        .header {
            border-bottom: 3px solid #2563eb;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #1e40af;
            font-size: 24pt;
            margin: 0 0 10px 0;
        }
        .header .subtitle {
            color: #666;
            font-size: 12pt;
        }
        .header .meta {
            color: #999;
            font-size: 10pt;
            margin-top: 10px;
        }
        .hero {
            background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
        }
        .hero .value-label {
            font-size: 11pt;
            text-transform: uppercase;
            letter-spacing: 1px;
            opacity: 0.8;
            margin-bottom: 5px;
        }
        .hero .value-amount {
            font-size: 36pt;
            font-weight: bold;
            margin: 10px 0;
        }
        .hero .value-details {
            font-size: 11pt;
            opacity: 0.9;
            margin-top: 15px;
        }
        .hero .metrics {
            display: flex;
            gap: 30px;
            margin-top: 20px;
        }
        .hero .metric {
            text-align: center;
        }
        .hero .metric-label {
            font-size: 9pt;
            text-transform: uppercase;
            opacity: 0.7;
        }
        .hero .metric-value {
            font-size: 18pt;
            font-weight: bold;
            margin-top: 5px;
        }
        h2 {
            color: #1e40af;
            font-size: 16pt;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 10px;
            margin-top: 30px;
        }
        h3 {
            color: #374151;
            font-size: 13pt;
            margin-top: 20px;
        }
        .use-case {
            background: #f9fafb;
            border-left: 4px solid #2563eb;
            padding: 15px 20px;
            margin: 15px 0;
            border-radius: 0 8px 8px 0;
        }
        .use-case h4 {
            color: #1e40af;
            font-size: 12pt;
            margin: 0 0 10px 0;
        }
        .use-case-meta {
            display: flex;
            gap: 20px;
            font-size: 10pt;
            color: #666;
            margin-bottom: 10px;
        }
        .use-case-meta span {
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 9pt;
            font-weight: 600;
        }
        .badge-persona {
            background: #dbeafe;
            color: #1e40af;
        }
        .badge-driver {
            background: #dcfce7;
            color: #166534;
        }
        .roi-positive {
            color: #16a34a;
            font-weight: bold;
        }
        .confidence-bar {
            width: 100px;
            height: 6px;
            background: #e5e7eb;
            border-radius: 3px;
            display: inline-block;
            margin-right: 10px;
        }
        .confidence-fill {
            height: 100%;
            background: #2563eb;
            border-radius: 3px;
        }
        .executive-summary {
            background: #f8fafc;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }
        .executive-summary p {
            margin: 0 0 15px 0;
            text-align: justify;
        }
        .footer-note {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            font-size: 9pt;
            color: #666;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <div class="subtitle">Business Case Analysis</div>
        <div class="meta">
            Generated: {{ generated_at }} | 
            Version: {{ version }} |
            Organization: {{ organization }}
        </div>
    </div>

    <div class="hero">
        <div class="value-label">Total Estimated Value</div>
        <div class="value-amount">{{ total_value }}</div>
        <div class="value-details">
            Across {{ use_case_count }} use cases | 
            Average payback: {{ avg_payback }} | 
            Generated by {{ generator }}
        </div>
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">Confidence</div>
                <div class="metric-value">{{ avg_confidence }}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Use Cases</div>
                <div class="metric-value">{{ use_case_count }}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Personas</div>
                <div class="metric-value">{{ persona_count }}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Value Drivers</div>
                <div class="metric-value">{{ driver_count }}</div>
            </div>
        </div>
    </div>

    <h2>Executive Summary</h2>
    <div class="executive-summary">
        {{ executive_summary }}
    </div>

    <h2>Use Case Breakdown</h2>
    {% for use_case in use_cases %}
    <div class="use-case">
        <h4>{{ use_case.name }}</h4>
        <div class="use-case-meta">
            <span class="badge badge-persona">{{ use_case.persona }}</span>
            <span class="badge badge-driver">{{ use_case.driver }}</span>
            <span class="roi-positive">{{ use_case.roi }}</span>
            <span>Payback: {{ use_case.payback }}</span>
        </div>
        <div>
            <span class="confidence-bar">
                <span class="confidence-fill" style="width: {{ use_case.confidence }}%"></span>
            </span>
            <span>{{ use_case.confidence }}% confidence</span>
        </div>
    </div>
    {% endfor %}

    <h2>Methodology & Assumptions</h2>
    <p>{{ methodology }}</p>

    <div class="footer-note">
        This business case was generated by Value Fabric's AI-powered analysis engine.<br>
        Data sources and confidence scores are based on automated extraction from organizational documents.<br>
        © {{ year }} Value Fabric. Confidential.
    </div>
</body>
</html>
"""


class DocumentExportTool(BaseTool):
    """Export business cases and documents to PDF format."""

    name = "export_document"
    category = ToolCategory.GENERATION
    description = "Export business cases and documents to PDF format"
    input_schema = ExportDocumentInput
    output_schema = ExportDocumentOutput
    timeout_seconds = 60

    async def execute(self, input_data: ExportDocumentInput) -> ExportDocumentOutput:
        """Generate PDF from business case data.

        Args:
            input_data: Validated ExportDocumentInput with document_type, business_case_data, etc.

        Returns:
            ExportDocumentOutput with pdf_bytes, content_type, filename, success status
        """
        try:
            if input_data.document_type == "business_case":
                return await self._generate_business_case_pdf(
                    input_data.business_case_data,
                    input_data.template,
                    input_data.branding,
                )
            else:
                # CONTRACT_EXCEPTION AP-7: Return structured error, don't raise
                return ExportDocumentOutput(
                    success=False,
                    error=f"Unsupported document type: {input_data.document_type}",
                    filename="error.pdf",
                )

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error("PDF generation failed: PDF_GENERATION_ERROR")
            return ExportDocumentOutput(
                success=False,
                error="PDF_GENERATION_ERROR",
                filename="error.pdf",
            )

    async def _generate_business_case_pdf(
        self,
        data: dict[str, Any],
        custom_template: str | None = None,
        branding: dict[str, str] | None = None,
    ) -> ExportDocumentOutput:
        """Generate business case PDF."""
        template_str = custom_template or BUSINESS_CASE_TEMPLATE
        template = Template(template_str, autoescape=select_autoescape(["html", "xml"]))

        # Calculate derived values
        use_cases = data.get("use_cases", [])
        total_value = self._format_currency(
            sum(self._parse_currency(uc.get("roi", "$0")) for uc in use_cases)
        )

        avg_confidence = (
            int(sum(uc.get("confidence", 0) for uc in use_cases) / len(use_cases))
            if use_cases
            else 0
        )

        avg_payback = self._calculate_avg_payback(use_cases)

        # Render HTML
        html_content = template.render(
            title=data.get("title", "Business Case"),
            organization=data.get("organization", "Acme Corp"),
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
            version=data.get("version", "1.0"),
            generator=data.get("generator", "BusinessCaseGenerator-v3.0"),
            total_value=total_value,
            use_case_count=len(use_cases),
            persona_count=len(set(uc.get("persona") for uc in use_cases if uc.get("persona"))),
            driver_count=len(set(uc.get("driver") for uc in use_cases if uc.get("driver"))),
            avg_confidence=avg_confidence,
            avg_payback=avg_payback,
            use_cases=use_cases,
            executive_summary=data.get("executive_summary", ""),
            methodology=data.get(
                "methodology",
                "Value estimation based on industry benchmarks and organizational data. "
                "ROI calculations include direct cost savings, efficiency gains, and risk mitigation. "
                "Confidence scores reflect data quality and extraction certainty.",
            ),
            year=datetime.now().year,
        )

        # Generate PDF (or return HTML if weasyprint unavailable)
        if not WEASYPRINT_AVAILABLE:
            logger.warning("weasyprint not available, returning HTML content instead of PDF")
            # Return HTML as bytes for testing purposes
            html_bytes = html_content.encode("utf-8")
            safe_title = "".join(
                c if c.isalnum() or c in ("-", "_") else "_"
                for c in data.get("title", "business_case")
            ).lower()
            filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d')}.html"
            return ExportDocumentOutput(
                pdf_bytes=html_bytes,
                content_type="text/html",
                filename=filename,
                success=True,
                file_size_bytes=len(html_bytes),
            )

        pdf_buffer = BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)  # type: ignore
        pdf_bytes = pdf_buffer.getvalue()

        # Generate filename
        safe_title = "".join(
            c if c.isalnum() or c in ("-", "_") else "_" for c in data.get("title", "business_case")
        ).lower()
        filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d')}.pdf"

        return ExportDocumentOutput(
            pdf_bytes=pdf_bytes,
            content_type="application/pdf",
            filename=filename,
            success=True,
            file_size_bytes=len(pdf_bytes),
        )

    def _format_currency(self, amount: float) -> str:
        """Format amount as currency string."""
        if amount >= 1_000_000:
            return f"${amount / 1_000_000:.2f}M"
        elif amount >= 1_000:
            return f"${amount / 1_000:.1f}K"
        else:
            return f"${amount:,.0f}"

    def _parse_currency(self, value: str) -> float:
        """Parse currency string to float.

        Supports formats: $1.5M, $500K, $1,234.56, 1000
        Returns 0.0 for invalid/empty input.
        """
        if not value or not isinstance(value, str):
            return 0.0

        # Remove $ and commas
        cleaned = value.replace("$", "").replace(",", "").strip()
        if not cleaned:
            return 0.0

        # Handle M/Million suffix
        if cleaned.endswith("M") and len(cleaned) > 1:
            try:
                return float(cleaned[:-1]) * 1_000_000
            except ValueError:
                return 0.0

        # Handle K/Thousand suffix
        if cleaned.endswith("K") and len(cleaned) > 1:
            try:
                return float(cleaned[:-1]) * 1_000
            except ValueError:
                return 0.0

        # Plain number
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _calculate_avg_payback(self, use_cases: list[dict[str, Any]]) -> str:
        """Calculate average payback period."""
        months = []
        for uc in use_cases:
            payback = uc.get("payback", "")
            if "mo" in payback.lower():
                try:
                    months.append(int(payback.split()[0]))
                except (ValueError, IndexError):
                    pass

        if months:
            avg = sum(months) / len(months)
            return f"{avg:.1f} mo"
        return "N/A"


class PDFGenerator:
    """Standalone PDF generator for non-tool usage."""

    def __init__(self, template_dir: str | None = None):
        self.template_dir = template_dir
        self.logger = logging.getLogger(__name__)

    async def generate_business_case_pdf(
        self,
        data: dict[str, Any],
        output_path: str | None = None,
    ) -> bytes:
        """Generate PDF from business case data.

        Args:
            data: Business case dictionary
            output_path: Optional path to save PDF

        Returns:
            PDF bytes
        """
        tool = DocumentExportTool()
        result = await tool._generate_business_case_pdf(data)

        pdf_bytes = result.pdf_bytes

        if output_path:
            async with aiofiles.open(output_path, "wb") as f:
                await f.write(pdf_bytes)
            self.logger.info(f"PDF saved to {output_path}")

        return pdf_bytes

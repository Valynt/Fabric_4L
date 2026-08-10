from __future__ import annotations

import asyncio
from io import BytesIO

import pytest

from layer4_agents.models.tool_schemas import ExportDocumentInput, ExportDocumentOutput
from layer4_agents.tools import document_export
from layer4_agents.tools.document_export import DocumentExportTool, PDFGenerator


def business_case() -> dict:
    return {
        "title": "Validated Case / 2026",
        "organization": "Example Org",
        "version": "2.0",
        "generator": "test",
        "executive_summary": "Evidence-backed value.",
        "use_cases": [
            {
                "name": "Automation",
                "persona": "CFO",
                "driver": "Efficiency",
                "roi": "$1.5M",
                "payback": "6 mo",
                "confidence": 80,
            },
            {
                "name": "Quality",
                "persona": "COO",
                "driver": "Risk",
                "roi": "$500K",
                "payback": "12 mo",
                "confidence": 60,
            },
        ],
    }


@pytest.mark.asyncio
async def test_business_case_export_returns_html_when_pdf_engine_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(document_export, "WEASYPRINT_AVAILABLE", False)

    result = await DocumentExportTool().execute(
        ExportDocumentInput(document_type="business_case", business_case_data=business_case())
    )

    assert result.success is True
    assert result.content_type == "text/html"
    assert result.filename.startswith("validated_case___2026_")
    assert result.file_size_bytes == len(result.pdf_bytes or b"")
    assert b"$2.00M" in (result.pdf_bytes or b"")
    assert b"9.0 mo" in (result.pdf_bytes or b"")


@pytest.mark.asyncio
async def test_business_case_export_uses_custom_template(monkeypatch) -> None:
    monkeypatch.setattr(document_export, "WEASYPRINT_AVAILABLE", False)
    result = await DocumentExportTool().execute(
        ExportDocumentInput(
            document_type="business_case",
            business_case_data={"title": "Custom", "use_cases": []},
            template="<h1>{{ title }}</h1><p>{{ total_value }}</p>",
        )
    )

    assert result.pdf_bytes == b"<h1>Custom</h1><p>$0</p>"


@pytest.mark.asyncio
async def test_business_case_export_generates_pdf_with_available_engine(monkeypatch) -> None:
    class FakeHTML:
        def __init__(self, *, string: str) -> None:
            assert "Validated Case" in string

        def write_pdf(self, target: BytesIO) -> None:
            target.write(b"%PDF-test")

    monkeypatch.setattr(document_export, "WEASYPRINT_AVAILABLE", True)
    monkeypatch.setattr(document_export, "HTML", FakeHTML)

    result = await DocumentExportTool().execute(
        ExportDocumentInput(document_type="business_case", business_case_data=business_case())
    )

    assert result.pdf_bytes == b"%PDF-test"
    assert result.content_type == "application/pdf"
    assert result.filename.endswith(".pdf")


@pytest.mark.asyncio
async def test_unsupported_document_type_returns_structured_error() -> None:
    result = await DocumentExportTool().execute(
        ExportDocumentInput(document_type="audit_report", business_case_data={})
    )

    assert result.success is False
    assert result.error == "Unsupported document type: audit_report"
    assert result.filename == "error.pdf"


@pytest.mark.asyncio
async def test_export_normalizes_generation_failure(monkeypatch) -> None:
    tool = DocumentExportTool()

    async def failed(*args, **kwargs):
        raise RuntimeError("secret content")

    monkeypatch.setattr(tool, "_generate_business_case_pdf", failed)
    result = await tool.execute(
        ExportDocumentInput(document_type="business_case", business_case_data={})
    )

    assert result.success is False
    assert result.error == "PDF_GENERATION_ERROR"


@pytest.mark.asyncio
async def test_export_propagates_cancellation(monkeypatch) -> None:
    tool = DocumentExportTool()

    async def cancelled(*args, **kwargs):
        raise asyncio.CancelledError

    monkeypatch.setattr(tool, "_generate_business_case_pdf", cancelled)
    with pytest.raises(asyncio.CancelledError):
        await tool.execute(
            ExportDocumentInput(document_type="business_case", business_case_data={})
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("$1.5M", 1_500_000),
        ("500K", 500_000),
        ("$1,234.56", 1234.56),
        ("1000", 1000),
        ("", 0),
        (None, 0),
        ("$", 0),
        ("badM", 0),
        ("badK", 0),
        ("bad", 0),
    ],
)
def test_parse_currency(value, expected: float) -> None:
    assert DocumentExportTool()._parse_currency(value) == expected


@pytest.mark.parametrize(
    ("amount", "expected"),
    [(2_000_000, "$2.00M"), (1500, "$1.5K"), (42, "$42")],
)
def test_format_currency(amount: float, expected: str) -> None:
    assert DocumentExportTool()._format_currency(amount) == expected


@pytest.mark.parametrize(
    ("use_cases", "expected"),
    [
        ([{"payback": "6 mo"}, {"payback": "12 mo"}], "9.0 mo"),
        ([{"payback": "unknown"}, {"payback": "x mo"}, {}], "N/A"),
        ([], "N/A"),
    ],
)
def test_calculate_average_payback(use_cases: list[dict], expected: str) -> None:
    assert DocumentExportTool()._calculate_avg_payback(use_cases) == expected


@pytest.mark.asyncio
async def test_standalone_generator_returns_and_optionally_writes_bytes(
    monkeypatch, tmp_path
) -> None:
    async def generated(self, data):
        return ExportDocumentOutput(pdf_bytes=b"generated", success=True, file_size_bytes=9)

    monkeypatch.setattr(DocumentExportTool, "_generate_business_case_pdf", generated)
    output = tmp_path / "case.pdf"

    result = await PDFGenerator(template_dir="templates").generate_business_case_pdf(
        {}, str(output)
    )
    in_memory = await PDFGenerator().generate_business_case_pdf({})

    assert result == b"generated"
    assert in_memory == b"generated"
    assert output.read_bytes() == b"generated"

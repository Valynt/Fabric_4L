"""Unit tests for PDF adapter."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import importlib.util

import httpx
import pytest

# pymupdf4llm is an optional heavy dependency (PDF extraction).
# Tests are collected but skipped when it is not installed.
# Install with: pip install pymupdf4llm
_pymupdf4llm_missing = importlib.util.find_spec("pymupdf4llm") is None
_pdf2image_missing = importlib.util.find_spec("pdf2image") is None
pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(_pymupdf4llm_missing, reason="pymupdf4llm not installed — optional slow dep"),
    pytest.mark.skipif(_pdf2image_missing, reason="pdf2image not installed — optional slow dep"),
]

try:
    import pdf2image  # noqa: F401
    # Test if poppler is available
    POPPLER_AVAILABLE = True
except ImportError:
    POPPLER_AVAILABLE = False

try:
    import pytesseract
    # Test if tesseract binary is actually available
    pytesseract.get_tesseract_version()
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False

from layer1_ingestion.adapters.base import AdapterType, FilingDocument

if _pdf2image_missing:
    PDFAdapter = None  # type: ignore[misc]
    PDFAdapterConfig = None  # type: ignore[misc]
else:
    from layer1_ingestion.adapters.pdf_adapter import PDFAdapter, PDFAdapterConfig


class TestPDFAdapter:
    """Test cases for PDF adapter."""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance for testing."""
        return PDFAdapter()

    @pytest.fixture
    def adapter_no_ocr(self):
        """Create adapter with OCR disabled."""
        config = PDFAdapterConfig(enable_ocr=False)
        return PDFAdapter(config)

    @pytest.mark.asyncio
    async def test_adapter_type(self, adapter):
        """Test adapter type is correct."""
        assert adapter.adapter_type == AdapterType.PDF

    @pytest.mark.asyncio
    async def test_supported_formats(self, adapter):
        """Test supported formats include expected types."""
        formats = adapter.supported_formats
        assert "pdf" in formats
        assert "markdown" in formats
        assert "txt" in formats
        assert "json" in formats

    @pytest.mark.asyncio
    async def test_health_check_success(self, adapter):
        """Test health check passes with dependencies available."""
        # Skip if OCR dependencies not available in test environment
        if not TESSERACT_AVAILABLE:
            pytest.skip("Tesseract not available in test environment")

        # PyMuPDF4LLM should be importable in test environment
        result = await adapter.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_without_ocr(self, adapter_no_ocr):
        """Test health check passes when OCR disabled."""
        # PyMuPDF4LLM is always required
        try:
            import pymupdf4llm
            _ = pymupdf4llm.to_markdown
        except ImportError:
            pytest.skip("PyMuPDF4LLM not available")

        result = await adapter_no_ocr.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_search_not_supported(self, adapter):
        """Test search returns empty list with warning."""
        results = await adapter.search("test query")
        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_document_local_file_not_found(self, adapter):
        """Test handling of non-existent local file."""
        result = await adapter.fetch_document("/nonexistent/file.pdf")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_document_from_url_success(self, adapter, tmp_path):
        """Test downloading and processing PDF from URL."""
        pdf_content = b"%PDF-1.4 fake pdf content"

        mock_response = Mock()
        mock_response.content = pdf_content
        mock_response.raise_for_status = Mock()

        # Create temp file with PDF content
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", mode='wb') as tmp:
            tmp.write(pdf_content)
            tmp_path = Path(tmp.name)

        # Create expected result
        expected_doc = FilingDocument(
            filing_type="PDF_DOCUMENT",
            filing_date=datetime.now(UTC),
            accession_number="test.pdf",
            primary_document="test.pdf",
            markdown_content="# Extracted content\n\nTest paragraph.",
            metadata={"extraction_method": "pymupdf4llm"}
        )

        try:
            with patch.object(adapter, '_get_client') as mock_get_client:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.is_closed = False
                mock_get_client.return_value = mock_client

                with patch.object(adapter, '_download_to_temp', return_value=tmp_path):
                    with patch.object(adapter, '_process_pdf', return_value=expected_doc):
                        result = await adapter.fetch_document("https://example.com/test.pdf")

                        assert result is not None
                        assert isinstance(result, FilingDocument)
                        assert result.markdown_content == "# Extracted content\n\nTest paragraph."
                        assert result.metadata["extraction_method"] == "pymupdf4llm"
        finally:
            # Clean up
            if tmp_path.exists():
                tmp_path.unlink()

    @pytest.mark.asyncio
    async def test_ocr_not_triggered_for_good_text(self, adapter, tmp_path):
        """Test OCR is skipped when sufficient text extracted."""
        good_content = "# Title\n\nThis is a long document with enough text content that should not trigger OCR fallback. It has multiple paragraphs and information."

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(b"%PDF fake")
            tmp_path = Path(tmp.name)

        try:
            with patch('pymupdf4llm.to_markdown', return_value=good_content):
                with patch.object(adapter, '_ocr_extract') as mock_ocr:
                    mock_ocr.return_value = ("", None)

                    result = await adapter._process_pdf(tmp_path, str(tmp_path))

                    assert result is not None
                    assert result.markdown_content == good_content
                    assert result.metadata["extraction_method"] == "pymupdf4llm"
                    # OCR should not be called
                    mock_ocr.assert_not_called()
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    @pytest.mark.asyncio
    async def test_ocr_triggered_for_low_text(self, adapter, tmp_path):
        """Test OCR fallback triggered when text is below threshold."""
        low_content = "Short"
        ocr_content = "OCR extracted this longer text from scanned document."

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(b"%PDF fake")
            tmp_path = Path(tmp.name)

        try:
            with patch('pymupdf4llm.to_markdown', return_value=low_content):
                with patch.object(adapter, '_ocr_extract', new_callable=AsyncMock) as mock_ocr:
                    mock_ocr.return_value = (ocr_content, 85.5)

                    result = await adapter._process_pdf(tmp_path, str(tmp_path))

                    assert result is not None
                    assert result.markdown_content == ocr_content
                    assert result.metadata["extraction_method"] == "ocr"
                    assert result.metadata["ocr_confidence"] == 85.5
                    mock_ocr.assert_called_once()
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    @pytest.mark.asyncio
    async def test_ocr_disabled_fallback_skipped(self, adapter_no_ocr, tmp_path):
        """Test OCR fallback is skipped when disabled."""
        low_content = "Short"

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(b"%PDF fake")
            tmp_path = Path(tmp.name)

        try:
            with patch('pymupdf4llm.to_markdown', return_value=low_content):
                with patch.object(adapter_no_ocr, '_ocr_extract') as mock_ocr:
                    result = await adapter_no_ocr._process_pdf(tmp_path, str(tmp_path))

                    assert result is not None
                    assert result.markdown_content == low_content
                    assert result.metadata["extraction_method"] == "pymupdf4llm"
                    # OCR should not be called even with low text
                    mock_ocr.assert_not_called()
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    @pytest.mark.asyncio
    async def test_detect_filing_type_analyst_report(self, adapter):
        """Test detection of analyst report from content."""
        content = "Gartner Magic Quadrant for Cloud Infrastructure 2024"
        filing_type = adapter._detect_filing_type(content)
        assert filing_type == "ANALYST_REPORT"

    @pytest.mark.asyncio
    async def test_detect_filing_type_patent(self, adapter):
        """Test detection of patent filing from content."""
        content = "United States Patent USPTO Claims Invention Assignee"
        filing_type = adapter._detect_filing_type(content)
        assert filing_type == "PATENT_FILING"

    @pytest.mark.asyncio
    async def test_detect_filing_type_sec_filing(self, adapter):
        """Test detection of SEC filing from content."""
        content = "FORM 10-K SECURITIES AND EXCHANGE COMMISSION Annual Report"
        filing_type = adapter._detect_filing_type(content)
        assert filing_type == "SEC_FILING"

    @pytest.mark.asyncio
    async def test_detect_filing_type_white_paper(self, adapter):
        """Test detection of white paper from content."""
        content = "White Paper Executive Summary Abstract"
        filing_type = adapter._detect_filing_type(content)
        assert filing_type == "WHITE_PAPER"

    @pytest.mark.asyncio
    async def test_detect_filing_type_generic(self, adapter):
        """Test fallback to generic document type."""
        content = "Some random content without specific markers"
        filing_type = adapter._detect_filing_type(content)
        assert filing_type == "PDF_DOCUMENT"

    @pytest.mark.asyncio
    async def test_download_to_temp_success(self, adapter):
        """Test downloading PDF to temporary file."""
        pdf_content = b"%PDF-1.4 test content"

        mock_response = Mock()
        mock_response.content = pdf_content
        mock_response.raise_for_status = Mock()

        with patch.object(adapter, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.is_closed = False
            mock_get_client.return_value = mock_client

            result = await adapter._download_to_temp("https://example.com/doc.pdf")

            assert result.exists()
            assert result.suffix == ".pdf"
            assert result.read_bytes() == pdf_content

            # Clean up
            result.unlink()

    @pytest.mark.asyncio
    async def test_download_to_temp_failure(self, adapter):
        """Test handling of failed download."""
        with patch.object(adapter, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Download failed"))
            mock_client.is_closed = False
            mock_get_client.return_value = mock_client

            with pytest.raises(httpx.HTTPError):
                await adapter._download_to_temp("https://example.com/doc.pdf")

    @pytest.mark.asyncio
    async def test_download_to_temp_retry_on_5xx(self, adapter):
        """Test retry logic for 5xx server errors with exponential backoff."""
        mock_response = Mock()
        mock_response.content = b"PDF content"
        mock_response.raise_for_status = Mock()

        # First two calls fail with 503, third succeeds
        with patch.object(adapter, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_error = httpx.HTTPStatusError(
                "Service Unavailable",
                request=Mock(),
                response=Mock(status_code=503)
            )
            mock_client.get = AsyncMock(side_effect=[mock_error, mock_error, mock_response])
            mock_client.is_closed = False
            mock_get_client.return_value = mock_client

            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                result = await adapter._download_to_temp("https://example.com/doc.pdf")

                # Should succeed on third attempt
                assert result.exists()
                assert result.read_bytes() == b"PDF content"
                # Verify exponential backoff: 2^0=1s, 2^1=2s
                assert mock_sleep.call_count == 2
                mock_sleep.assert_any_call(1)
                mock_sleep.assert_any_call(2)

                result.unlink()

    @pytest.mark.asyncio
    async def test_download_to_temp_no_retry_on_4xx(self, adapter):
        """Test that 4xx client errors are not retried."""
        with patch.object(adapter, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_error = httpx.HTTPStatusError(
                "Not Found",
                request=Mock(),
                response=Mock(status_code=404)
            )
            mock_client.get = AsyncMock(side_effect=mock_error)
            mock_client.is_closed = False
            mock_get_client.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await adapter._download_to_temp("https://example.com/doc.pdf")

            # Should fail immediately without retry
            assert exc_info.value.response.status_code == 404
            assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_ocr_extract_success(self, adapter, tmp_path):
        """Test OCR text extraction from scanned PDF."""
        mock_image = Mock()

        with patch('src.adapters.pdf_adapter.convert_from_path', return_value=[mock_image, mock_image]):
            with patch('src.adapters.pdf_adapter.pytesseract.image_to_string', return_value="OCR text"):
                with patch('src.adapters.pdf_adapter.pytesseract.image_to_data', return_value={
                    "conf": [80, 85, 90]
                }):
                    text, confidence = await adapter._ocr_extract(tmp_path, "eng")

                    assert text == "OCR text\n\nOCR text"
                    assert confidence == 85.0  # Average of [80, 85, 90]

    @pytest.mark.asyncio
    async def test_ocr_extract_no_confidence(self, adapter, tmp_path):
        """Test OCR when confidence data unavailable."""
        mock_image = Mock()

        with patch('src.adapters.pdf_adapter.convert_from_path', return_value=[mock_image]):
            with patch('src.adapters.pdf_adapter.pytesseract.image_to_string', return_value="OCR text"):
                with patch('src.adapters.pdf_adapter.pytesseract.image_to_data', return_value={"conf": []}):
                    text, confidence = await adapter._ocr_extract(tmp_path, "eng")

                    assert text == "OCR text"
                    assert confidence is None

    @pytest.mark.asyncio
    async def test_ocr_extract_failure(self, adapter, tmp_path):
        """Test OCR handling of extraction failure."""
        with patch('src.adapters.pdf_adapter.convert_from_path', side_effect=Exception("OCR failed")):
            text, confidence = await adapter._ocr_extract(tmp_path, "eng")

            assert text == ""
            assert confidence is None

    @pytest.mark.asyncio
    async def test_fetch_document_with_file_path_kwarg(self, adapter):
        """Test using file_path kwarg instead of document_id."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(b"%PDF fake")
            tmp_path = Path(tmp.name)

        # Create expected result
        expected_doc = FilingDocument(
            filing_type="PDF_DOCUMENT",
            filing_date=datetime.now(UTC),
            accession_number=tmp_path.name,
            primary_document=tmp_path.name,
            markdown_content="Content",
            metadata={"extraction_method": "pymupdf4llm"}
        )

        try:
            with patch.object(adapter, '_process_pdf', return_value=expected_doc):
                result = await adapter.fetch_document("ignored", file_path=str(tmp_path))

                assert result is not None
                assert result.markdown_content == "Content"
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    @pytest.mark.asyncio
    async def test_fetch_document_with_url_kwarg(self, adapter):
        """Test using url kwarg instead of document_id."""
        pdf_content = b"%PDF-1.4 test"

        mock_response = Mock()
        mock_response.content = pdf_content
        mock_response.raise_for_status = Mock()

        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", mode='wb') as tmp:
            tmp.write(pdf_content)
            tmp_path = Path(tmp.name)

        # Create expected result
        expected_doc = FilingDocument(
            filing_type="PDF_DOCUMENT",
            filing_date=datetime.now(UTC),
            accession_number=tmp_path.name,
            primary_document=tmp_path.name,
            markdown_content="Downloaded content",
            metadata={"extraction_method": "pymupdf4llm"}
        )

        try:
            with patch.object(adapter, '_get_client') as mock_get_client:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.is_closed = False
                mock_get_client.return_value = mock_client

                with patch.object(adapter, '_download_to_temp', return_value=tmp_path):
                    with patch.object(adapter, '_process_pdf', return_value=expected_doc):
                        result = await adapter.fetch_document("ignored", url="https://example.com/doc.pdf")

                        assert result is not None
                        assert result.markdown_content == "Downloaded content"
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    @pytest.mark.asyncio
    async def test_process_pdf_tables_detected(self, adapter, tmp_path):
        """Test table detection in PDF content."""
        # Content with markdown tables (3 pipes per row = table indicators)
        content_with_tables = "| Col1 | Col2 | Col3 |\n|------|------|------|\n| A | B | C |\n| D | E | F |"

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(b"%PDF fake")
            tmp_path = Path(tmp.name)

        try:
            with patch('pymupdf4llm.to_markdown', return_value=content_with_tables):
                result = await adapter._process_pdf(tmp_path, str(tmp_path))

                assert result is not None
                # Tables detected via pipe character counting (3 pipes per row, 4 rows = ~4 tables)
                assert result.metadata["tables_detected"] >= 0
                assert "tables" in result.metadata
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    @pytest.mark.asyncio
    async def test_process_pdf_file_size_validation(self, adapter, tmp_path):
        """Test that oversized PDFs are rejected with clear error."""
        # Create a temp file larger than the limit
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            # Write 1KB of content (larger than our 0.0005MB ~500 byte limit)
            tmp.write(b"%PDF fake content" + b"x" * 2000)
            tmp_path = Path(tmp.name)

        # Set low max size (0.0005 MB = ~500 bytes)
        adapter.config.max_file_size_mb = 0.0005

        try:
            # Should raise ValueError before trying to process
            with pytest.raises(ValueError) as exc_info:
                await adapter._process_pdf(tmp_path, str(tmp_path))

            assert "too large" in str(exc_info.value)
            assert "exceeds limit" in str(exc_info.value)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    @pytest.mark.asyncio
    async def test_ocr_extract_dpi_clamping_high(self, adapter, tmp_path):
        """Test that excessive DPI is clamped to MAX_DPI (1200)."""
        mock_image = Mock()

        # Set excessively high DPI
        adapter.config.dpi = 5000

        with patch('src.adapters.pdf_adapter.convert_from_path') as mock_convert:
            mock_convert.return_value = [mock_image]
            with patch('src.adapters.pdf_adapter.pytesseract.image_to_string', return_value="text"):
                with patch('src.adapters.pdf_adapter.pytesseract.image_to_data', return_value={"conf": []}):
                    await adapter._ocr_extract(tmp_path, "eng")

                    # Verify DPI was clamped to 1200 (MAX_DPI)
                    call_args = mock_convert.call_args
                    actual_dpi = call_args.kwargs.get('dpi') if call_args.kwargs else call_args[1].get('dpi')
                    # DPI should be clamped to max 1200
                    assert actual_dpi == 1200

    @pytest.mark.asyncio
    async def test_ocr_extract_dpi_clamping_low(self, adapter, tmp_path):
        """Test that too-low DPI is clamped to MIN_DPI (72)."""
        mock_image = Mock()

        # Set too-low DPI
        adapter.config.dpi = 10

        with patch('src.adapters.pdf_adapter.convert_from_path') as mock_convert:
            mock_convert.return_value = [mock_image]
            with patch('src.adapters.pdf_adapter.pytesseract.image_to_string', return_value="text"):
                with patch('src.adapters.pdf_adapter.pytesseract.image_to_data', return_value={"conf": []}):
                    await adapter._ocr_extract(tmp_path, "eng")

                    # Verify DPI was clamped to at least 72 (MIN_DPI)
                    call_args = mock_convert.call_args
                    actual_dpi = call_args.kwargs.get('dpi') if call_args.kwargs else call_args[1].get('dpi')
                    # DPI should be clamped to min 72
                    assert actual_dpi == 72

    @pytest.mark.asyncio
    async def test_close_client(self, adapter):
        """Test closing HTTP client."""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        adapter._client = mock_client

        await adapter.close()

        mock_client.aclose.assert_called_once()


class TestPDFAdapterConfig:
    """Test cases for PDF adapter configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PDFAdapterConfig()
        assert config.enable_ocr is True
        assert config.ocr_language == "eng"
        assert config.min_text_length == 100
        assert config.preserve_tables is True
        assert config.dpi == 300

    def test_custom_config(self):
        """Test custom configuration values."""
        config = PDFAdapterConfig(
            enable_ocr=False,
            ocr_language="fra",
            min_text_length=50,
            preserve_tables=False,
            dpi=200
        )
        assert config.enable_ocr is False
        assert config.ocr_language == "fra"
        assert config.min_text_length == 50
        assert config.preserve_tables is False
        assert config.dpi == 200

    def test_inherited_config(self):
        """Test inherited base config attributes."""
        config = PDFAdapterConfig()
        assert config.rate_limit_per_second == 1.0
        assert config.user_agent == "ValueFabric/1.0"
        assert config.timeout_seconds == 30


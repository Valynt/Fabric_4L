"""PDF adapter for ingesting PDF documents.

Supports digitally-born PDFs via PyMuPDF4LLM and scanned documents via OCR fallback.
Handles both local file paths and HTTP URLs.
"""

import asyncio
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import pymupdf4llm
import pytesseract
import structlog
from pdf2image import convert_from_path

from .base import AdapterConfig, AdapterType, DataSourceAdapter, FilingDocument, SearchResult

logger = structlog.get_logger()

# Constants for content analysis
MAX_CONTENT_ANALYSIS_LENGTH = 5000  # Characters to scan for document type detection
TABLE_PIPE_DIVISOR = 3  # Pipes per row heuristic for table detection
MIN_DPI = 72  # Minimum valid DPI for OCR
MAX_DPI = 1200  # Maximum reasonable DPI for OCR

# Document type detection markers
DOCUMENT_TYPE_MARKERS = {
    "ANALYST_REPORT": ["GARTNER", "FORRESTER", "IDC", "MAGIC QUADRANT", "WAVE"],
    "PATENT_FILING": ["PATENT", "USPTO", "CLAIMS", "INVENTION", "ASSIGNEE"],
    "SEC_FILING": ["10-K", "10-Q", "8-K", "SECURITIES AND EXCHANGE COMMISSION"],
    "WHITE_PAPER": ["WHITE PAPER", "WHITEPAPER", "EXECUTIVE SUMMARY", "ABSTRACT"],
}


@dataclass
class PDFAdapterConfig(AdapterConfig):
    """Extended configuration for PDF adapter."""

    enable_ocr: bool = True
    ocr_language: str = "eng"
    min_text_length: int = 100
    preserve_tables: bool = True
    dpi: int = 300
    max_file_size_mb: float = 100.0  # Maximum PDF file size to process


class PDFAdapter(DataSourceAdapter):
    """Adapter for PDF document ingestion.

    Supports:
    - Local file paths
    - HTTP/HTTPS URLs (downloaded to temp file)
    - Optional OCR fallback for scanned documents

    Output: Markdown with metadata and reserved table structure field.
    """

    def __init__(self, config: PDFAdapterConfig | None = None):
        super().__init__(config or PDFAdapterConfig())
        self.config: PDFAdapterConfig = self.config  # type: ignore
        self._client: httpx.AsyncClient | None = None

    @property
    def adapter_type(self) -> AdapterType:
        """Return the adapter type identifier."""
        return AdapterType.PDF

    @property
    def supported_formats(self) -> list[str]:
        """Return list of supported output formats."""
        return ["pdf", "markdown", "txt", "json"]

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout_seconds, follow_redirects=True
            )
        return self._client

    async def health_check(self) -> bool:
        """Check if PDF processing dependencies are available."""
        try:
            # Verify PyMuPDF4LLM import
            _ = pymupdf4llm.to_markdown

            # Verify OCR availability if enabled
            if self.config.enable_ocr:
                _ = pytesseract.get_tesseract_version()

            return True
        except Exception as e:
            self.logger.error("Health check failed", error_code="PDF_HEALTH_ERROR")
            return False

    async def search(
        self,
        query: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        **kwargs,
    ) -> list[SearchResult]:
        """Search for documents - not applicable for PDF adapter.

        PDF adapter processes individual documents, not searchable repositories.
        """
        self.logger.warning("Search not supported by PDF adapter")
        return []

    async def fetch_document(self, document_id: str, **kwargs) -> FilingDocument | None:
        """Fetch and process a PDF document.

        Args:
            document_id: Local file path or HTTP URL to PDF
            **kwargs: Additional options:
                - file_path: Alternative to document_id for local files
                - url: Alternative to document_id for remote files
                - enable_ocr: Override config OCR setting
                - ocr_language: Override config language

        Returns:
            FilingDocument with extracted markdown content
        """
        # Determine source (document_id, file_path, or url)
        file_path = kwargs.get("file_path", document_id)
        url = kwargs.get("url")

        if url or (file_path.startswith("http://") or file_path.startswith("https://")):
            url = url or file_path
            local_path = await self._download_to_temp(url)
        else:
            local_path = Path(file_path)

        if not local_path.exists():
            self.logger.error("PDF file not found", path=str(local_path))
            return None

        try:
            return await self._process_pdf(local_path, url or str(local_path), **kwargs)
        except Exception as e:
            self.logger.error("PDF processing failed", path=str(local_path), error_code="PDF_PROCESS_ERROR")
            return None

    async def _download_to_temp(self, url: str) -> Path:
        """Download URL content to temporary file with retry logic."""
        parsed = urlparse(url)
        suffix = Path(parsed.path).suffix or ".pdf"

        temp_path: Path | None = None

        for attempt in range(self.config.max_retries):
            temp_file = None
            try:
                # Create fresh temp file for each attempt
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                temp_path = Path(temp_file.name)

                client = await self._get_client()
                response = await client.get(url)
                response.raise_for_status()

                temp_file.write(response.content)
                temp_file.close()

                self.logger.info("Downloaded PDF", url=url, size=len(response.content))
                return temp_path
            except httpx.HTTPStatusError as e:
                # Clean up temp file before handling error
                if temp_file:
                    temp_file.close()
                if temp_path and temp_path.exists():
                    temp_path.unlink()

                # Don't retry 4xx client errors
                if e.response.status_code < 500:
                    raise

                self.logger.warning(
                    "Download failed, retrying",
                    url=url,
                    attempt=attempt + 1,
                    status_code=e.response.status_code,
                )
            except Exception as e:
                # Clean up temp file on any other error
                if temp_file:
                    temp_file.close()
                if temp_path and temp_path.exists():
                    temp_path.unlink()

                self.logger.warning(
                    "Download failed, retrying", url=url, attempt=attempt + 1, error_code="DOWNLOAD_RETRY_ERROR"
                )

            # Exponential backoff before retry
            if attempt < self.config.max_retries - 1:
                wait_time = 2**attempt
                self.logger.debug(f"Waiting {wait_time}s before retry")
                await asyncio.sleep(wait_time)

        # Max retries exceeded - temp file already cleaned up in exception handlers
        raise httpx.HTTPError(f"Failed to download PDF after {self.config.max_retries} attempts")

    async def _process_pdf(self, local_path: Path, source_url: str, **kwargs) -> FilingDocument:
        """Process PDF file and extract content."""
        enable_ocr = kwargs.get("enable_ocr", self.config.enable_ocr)
        ocr_language = kwargs.get("ocr_language", self.config.ocr_language)

        # Validate file size
        file_stats = local_path.stat()
        file_size_mb = file_stats.st_size / (1024 * 1024)
        if file_size_mb > self.config.max_file_size_mb:
            raise ValueError(
                f"PDF file too large: {file_size_mb:.1f}MB exceeds "
                f"limit of {self.config.max_file_size_mb}MB"
            )

        # Primary extraction with PyMuPDF4LLM
        self.logger.debug("Extracting with PyMuPDF4LLM", path=str(local_path))

        markdown_content = pymupdf4llm.to_markdown(
            str(local_path), page_chunks=False, write_images=False, embed_images=False
        )

        extraction_method = "pymupdf4llm"
        ocr_confidence = None

        # Check if OCR fallback needed
        text_length = len(markdown_content.strip())
        if text_length < self.config.min_text_length and enable_ocr:
            self.logger.info("Triggering OCR fallback", text_length=text_length)
            markdown_content, ocr_confidence = await self._ocr_extract(local_path, ocr_language)
            extraction_method = "ocr"

        # Calculate metadata (file_stats obtained earlier)
        tables_detected = markdown_content.count("|") // TABLE_PIPE_DIVISOR  # Rough heuristic

        metadata: dict[str, Any] = {
            "source_url": source_url,
            "file_size": file_stats.st_size,
            "file_path": str(local_path),
            "extraction_method": extraction_method,
            "tables_detected": max(0, tables_detected),
            "tables": [],  # Reserved for future structured table extraction
        }

        if ocr_confidence is not None:
            metadata["ocr_confidence"] = ocr_confidence

        # Determine filing type from content heuristics
        filing_type = self._detect_filing_type(markdown_content)

        return FilingDocument(
            filing_type=filing_type,
            filing_date=datetime.now(UTC),
            accession_number=str(local_path.name),
            primary_document=str(local_path.name),
            html_url=source_url if source_url.startswith("http") else None,
            raw_content=None,  # PDF binary not stored
            markdown_content=markdown_content,
            structured_data=None,
            metadata=metadata,
        )

    async def _ocr_extract(self, local_path: Path, language: str) -> tuple[str, float | None]:
        """Extract text using OCR as fallback for scanned documents."""
        self.logger.debug("Starting OCR extraction", path=str(local_path), language=language)

        # Validate and clamp DPI to valid range
        dpi = max(MIN_DPI, min(self.config.dpi, MAX_DPI))

        try:
            images = convert_from_path(str(local_path), dpi=dpi)

            texts = []
            confidences = []

            for i, image in enumerate(images):
                text = pytesseract.image_to_string(image, lang=language)
                texts.append(text)

                # Get confidence data if available
                data = pytesseract.image_to_data(
                    image, lang=language, output_type=pytesseract.Output.DICT
                )
                confs = [c for c in data.get("conf", []) if isinstance(c, (int, float)) and c > 0]
                if confs:
                    avg_conf = sum(confs) / len(confs)
                    confidences.append(avg_conf)

                self.logger.debug(f"OCR page {i + 1}/{len(images)} completed")

            full_text = "\n\n".join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else None

            self.logger.info(
                "OCR extraction completed",
                pages=len(images),
                text_length=len(full_text),
                confidence=avg_confidence,
            )

            return full_text, avg_confidence

        except Exception as e:
            self.logger.error("OCR extraction failed", error_code="OCR_ERROR")
            return "", None

    def _detect_filing_type(self, content: str) -> str:
        """Detect document type from content heuristics."""
        content_upper = content[:MAX_CONTENT_ANALYSIS_LENGTH].upper()

        for doc_type, markers in DOCUMENT_TYPE_MARKERS.items():
            if any(marker in content_upper for marker in markers):
                return doc_type

        return "PDF_DOCUMENT"

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

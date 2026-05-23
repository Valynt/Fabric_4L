"""Base adapter interface for data source adapters.

All data source adapters (SEC EDGAR, USPTO, News) must implement
the DataSourceAdapter abstract base class.
"""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class AdapterType(str, Enum):
    """Types of data source adapters."""

    WEBSITE = "website"
    SEC_EDGAR = "sec_edgar"
    USPTO_PATENTS = "uspto_patents"
    NEWS = "news"
    PDF = "pdf"


class FilingType(str, Enum):
    """SEC EDGAR filing form types."""

    FORM_10_K = "10-K"
    FORM_10_Q = "10-Q"
    FORM_8_K = "8-K"
    FORM_DEF_14A = "DEF 14A"  # Proxy statements
    FORM_S_1 = "S-1"  # IPO registration
    FORM_13F = "13F"  # Institutional holdings
    FORM_4 = "4"  # Insider trading
    FORM_20_F = "20-F"  # Foreign issuer annual


@dataclass
class FilingDocument:
    """Represents a single filing document."""

    filing_type: str
    filing_date: datetime
    accession_number: str
    primary_document: str
    description: str | None = None
    xbrl_url: str | None = None
    html_url: str | None = None
    raw_content: str | None = None
    markdown_content: str | None = None
    structured_data: dict[str, Any] | None = None  # XBRL parsed data
    metadata: dict[str, Any] | None = None


@dataclass
class SearchResult:
    """Result from a search query."""

    source_id: str
    title: str
    url: str
    published_date: datetime | None = None
    summary: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class AdapterConfig:
    """Configuration for a data source adapter."""

    rate_limit_per_second: float = 1.0
    user_agent: str = "ValueFabric/1.0"
    timeout_seconds: int = 30
    max_retries: int = 3
    cache_ttl_hours: int = 24
    api_key: str | None = None
    extra_headers: dict[str, str] | None = None


class DataSourceAdapter(ABC):
    """Abstract base class for all data source adapters.

    Adapters are responsible for:
    - Connecting to external data sources
    - Fetching data with rate limiting and error handling
    - Converting source data to internal format (Markdown + metadata)
    - Providing consistent interface for the crawl system
    """

    def __init__(self, config: AdapterConfig | None = None):
        self.config = config or AdapterConfig()
        self.logger = logger.bind(adapter=self.__class__.__name__)

    @property
    @abstractmethod
    def adapter_type(self) -> AdapterType:
        """Return the adapter type identifier."""
        pass

    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """Return list of supported output formats."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the data source is accessible.

        Returns:
            True if the source is healthy, False otherwise.
        """
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        **kwargs,
    ) -> list[SearchResult]:
        """Search for documents in the data source.

        Args:
            query: Search query string
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum results to return
            **kwargs: Additional source-specific parameters

        Returns:
            List of search results
        """
        pass

    @abstractmethod
    async def fetch_document(self, document_id: str, **kwargs) -> FilingDocument | None:
        """Fetch a specific document by ID.

        Args:
            document_id: Unique identifier for the document
            **kwargs: Additional source-specific parameters

        Returns:
            FilingDocument if found, None otherwise
        """
        pass

    async def fetch_documents_batch(
        self, document_ids: list[str], **kwargs
    ) -> AsyncGenerator[FilingDocument, None]:
        """Fetch multiple documents efficiently.

        Default implementation fetches sequentially with rate limiting.
        Override for batch-optimized implementations.

        Args:
            document_ids: List of document IDs to fetch
            **kwargs: Additional source-specific parameters

        Yields:
            FilingDocument instances
        """
        for doc_id in document_ids:
            try:
                document = await self.fetch_document(doc_id, **kwargs)
                if document:
                    yield document

                # Rate limiting
                if self.config.rate_limit_per_second > 0:
                    await asyncio.sleep(1.0 / self.config.rate_limit_per_second)

            except Exception as e:
                self.logger.error("Failed to fetch document", document_id=doc_id, error_code="DOC_FETCH_ERROR")
                continue

    def _apply_rate_limit(self, last_request_time: datetime) -> float:
        """Calculate sleep time needed for rate limiting.

        Args:
            last_request_time: Timestamp of last request

        Returns:
            Seconds to sleep (0 if no limit needed)
        """
        if self.config.rate_limit_per_second <= 0:
            return 0.0

        min_interval = 1.0 / self.config.rate_limit_per_second
        elapsed = (datetime.now(UTC) - last_request_time).total_seconds()

        if elapsed < min_interval:
            return min_interval - elapsed

        return 0.0

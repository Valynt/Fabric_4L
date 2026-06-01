"""SEC EDGAR adapter for fetching financial filings.

Uses the SEC EDGAR Search API v3 and supports downloading:
- 10-K (Annual reports)
- 10-Q (Quarterly reports)
- 8-K (Current reports)
- DEF 14A (Proxy statements)
- Other SEC forms

Rate limited to 10 requests/second per SEC guidelines.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from value_fabric.shared.models.typed_dict import TypedDictModel

from .base import (
    AdapterConfig,
    AdapterType,
    DataSourceAdapter,
    FilingDocument,
    FilingType,
    SearchResult,
)


class SECEdgarAdapter__fetch_xbrl_dataResult(TypedDictModel):
    parsed: bool
    xbrl_available: bool
    xbrl_url: Any
    xbrl_xml_size: Any

logger = structlog.get_logger()


class SECEdgarAdapter(DataSourceAdapter):
    """Adapter for SEC EDGAR filings database.

    Fetches financial filings from the SEC EDGAR system.
    Implements rate limiting (10 req/sec) and proper User-Agent headers.

    References:
        - https://www.sec.gov/edgar/sec-api-documentation
        - https://www.sec.gov/os/webmaster-faq#code-support
    """

    BASE_URL = "https://www.sec.gov"
    ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"

    def __init__(self, config: AdapterConfig | None = None):
        default_config = AdapterConfig(
            rate_limit_per_second=10.0,  # SEC limit
            user_agent="ValueFabric/1.0 (contact@valuefabric.io)",
            timeout_seconds=30,
            max_retries=3,
            cache_ttl_hours=24,
        )

        if config:
            default_config.__dict__.update(config.__dict__)

        super().__init__(default_config)

        self._client: httpx.AsyncClient | None = None
        self._last_request_time: datetime | None = None

    @property
    def adapter_type(self) -> AdapterType:
        return AdapterType.SEC_EDGAR

    @property
    def supported_formats(self) -> list[str]:
        return ["html", "xbrl", "txt", "json"]

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper headers."""
        if self._client is None or self._client.is_closed:
            headers = {
                "User-Agent": self.config.user_agent,
                "Accept": "application/json",
            }

            if self.config.extra_headers:
                headers.update(self.config.extra_headers)

            self._client = httpx.AsyncClient(
                headers=headers, timeout=self.config.timeout_seconds, follow_redirects=True
            )

        return self._client

    async def _rate_limited_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make a rate-limited HTTP request.

        Ensures compliance with SEC's 10 requests/second limit.
        """
        # Apply rate limiting
        if self._last_request_time:
            sleep_time = self._apply_rate_limit(self._last_request_time)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        client = await self._get_client()

        for attempt in range(self.config.max_retries):
            try:
                self._last_request_time = datetime.now(UTC)
                response = await client.request(method, url, **kwargs)

                # Check for rate limit response
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 1))
                    self.logger.warning(
                        "Rate limited by SEC", retry_after=retry_after, attempt=attempt + 1
                    )
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response

            except httpx.HTTPStatusError:
                if attempt < self.config.max_retries - 1:
                    wait = 2**attempt  # Exponential backoff
                    self.logger.warning(
                        "Request failed, retrying", error_code="HTTP_RETRY_ERROR", attempt=attempt + 1, wait=wait
                    )
                    await asyncio.sleep(wait)
                else:
                    raise
            except Exception:
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2**attempt)
                else:
                    raise

        raise Exception("Max retries exceeded")

    async def health_check(self) -> bool:
        """Check SEC EDGAR accessibility."""
        try:
            response = await self._rate_limited_request(
                "GET", f"{self.BASE_URL}/files/company_tickers.json"
            )
            return response.status_code == 200
        except Exception:
            self.logger.error("Health check failed", error_code="HEALTH_CHECK_ERROR")
            return False

    async def get_company_cik(self, ticker: str) -> str | None:
        """Get CIK (Central Index Key) for a ticker symbol.

        The CIK is required for all EDGAR API queries.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")

        Returns:
            10-digit CIK string (zero-padded) or None if not found
        """
        try:
            response = await self._rate_limited_request(
                "GET", f"{self.BASE_URL}/files/company_tickers.json"
            )

            data = response.json()

            for entry in data.values():
                if entry.get("ticker", "").upper() == ticker.upper():
                    cik = str(entry["cik_str"]).zfill(10)
                    return cik

            self.logger.warning("Ticker not found", ticker=ticker)
            return None

        except Exception:
            self.logger.error("Failed to get CIK", ticker=ticker, error_code="CIK_LOOKUP_ERROR")
            return None

    async def search(
        self,
        query: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        form_types: list[str] | None = None,
        **kwargs,
    ) -> list[SearchResult]:
        """Search for SEC filings by ticker/form type.

        The query parameter should be a ticker symbol for SEC EDGAR.

        Args:
            query: Ticker symbol (e.g., "AAPL")
            start_date: Filter filings after this date
            end_date: Filter filings before this date
            limit: Maximum filings to return
            form_types: List of form types (e.g., ["10-K", "10-Q"])
            **kwargs: Additional parameters (unused)

        Returns:
            List of search results with filing metadata
        """
        ticker = query.upper().strip()
        cik = await self.get_company_cik(ticker)

        if not cik:
            return []

        try:
            # Get submission history
            response = await self._rate_limited_request(
                "GET", f"{self.BASE_URL}/submissions/CIK{cik}.json"
            )

            data = response.json()
            filings = data.get("filings", {}).get("recent", {})

            results = []

            # Parse recent filings
            forms = filings.get("form", [])
            dates = filings.get("filingDate", [])
            accession_numbers = filings.get("accessionNumber", [])
            primary_docs = filings.get("primaryDocument", [])
            descriptions = filings.get("primaryDocDescription", [])

            for i, form in enumerate(forms[:limit]):
                # Filter by form type if specified
                if form_types and form not in form_types:
                    continue

                filing_date_str = dates[i] if i < len(dates) else None

                # Date filtering
                if filing_date_str and (start_date or end_date):
                    filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d").replace(tzinfo=UTC)

                    if start_date and filing_date < start_date:
                        continue
                    if end_date and filing_date > end_date:
                        continue

                accession = accession_numbers[i] if i < len(accession_numbers) else ""
                doc = primary_docs[i] if i < len(primary_docs) else ""
                desc = descriptions[i] if i < len(descriptions) else ""

                # Build URLs
                accession_clean = accession.replace("-", "")
                html_url = f"{self.ARCHIVES_URL}/{cik}/{accession_clean}/{doc}"

                results.append(
                    SearchResult(
                        source_id=accession,
                        title=f"{ticker} - {form} ({filing_date_str})",
                        url=html_url,
                        published_date=datetime.strptime(filing_date_str, "%Y-%m-%d").replace(
                            tzinfo=UTC
                        )
                        if filing_date_str
                        else None,
                        summary=desc,
                        metadata={
                            "ticker": ticker,
                            "cik": cik,
                            "form_type": form,
                            "accession_number": accession,
                            "primary_document": doc,
                        },
                    )
                )

            self.logger.info(
                "SEC search completed",
                ticker=ticker,
                results_count=len(results),
                form_types=form_types,
            )

            return results

        except Exception:
            self.logger.error("SEC search failed", ticker=ticker, error_code="SEC_SEARCH_ERROR")
            return []

    async def fetch_document(
        self, document_id: str, include_xbrl: bool = True, **kwargs
    ) -> FilingDocument | None:
        """Fetch a specific SEC filing document.

        Args:
            document_id: Accession number (e.g., "0000320193-23-000106")
            include_xbrl: Whether to fetch and parse XBRL data
            **kwargs: Additional parameters:
                - ticker: Ticker symbol
                - cik: CIK number (10-digit)
                - form_type: Form type

        Returns:
            FilingDocument with HTML content and optional XBRL data
        """
        ticker = kwargs.get("ticker", "")
        cik = kwargs.get("cik", "")
        form_type = kwargs.get("form_type", "")

        if not cik and ticker:
            cik = await self.get_company_cik(ticker)

        if not cik:
            self.logger.error("CIK required for document fetch", document_id=document_id)
            return None

        try:
            accession_clean = document_id.replace("-", "")

            # Get filing metadata from submissions
            response = await self._rate_limited_request(
                "GET", f"{self.BASE_URL}/submissions/CIK{cik}.json"
            )

            data = response.json()
            filings = data.get("filings", {}).get("recent", {})

            # Find the specific filing
            accession_numbers = filings.get("accessionNumber", [])
            filing_dates = filings.get("filingDate", [])
            primary_docs = filings.get("primaryDocument", [])
            descriptions = filings.get("primaryDocDescription", [])

            idx = None
            for i, acc in enumerate(accession_numbers):
                if acc == document_id:
                    idx = i
                    break

            if idx is None:
                self.logger.warning("Filing not found", accession=document_id)
                return None

            filing_date_str = filing_dates[idx] if idx < len(filing_dates) else None
            primary_doc = primary_docs[idx] if idx < len(primary_docs) else ""
            description = descriptions[idx] if idx < len(descriptions) else ""

            filing_date = None
            if filing_date_str:
                filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d").replace(tzinfo=UTC)

            # Fetch HTML filing
            html_url = f"{self.ARCHIVES_URL}/{cik}/{accession_clean}/{primary_doc}"

            html_response = await self._rate_limited_request("GET", html_url)
            html_content = html_response.text

            # Try to get XBRL data
            structured_data = None
            if include_xbrl and form_type in [FilingType.FORM_10_K, FilingType.FORM_10_Q]:
                xbrl_data = await self._fetch_xbrl_data(cik, accession_clean, form_type)
                if xbrl_data:
                    structured_data = xbrl_data

            # Convert HTML to Markdown (simplified - full implementation would use content_extractor)
            markdown_content = self._html_to_markdown(html_content, document_id)

            return FilingDocument(
                filing_type=form_type or "UNKNOWN",
                filing_date=filing_date,
                accession_number=document_id,
                primary_document=primary_doc,
                description=description,
                html_url=html_url,
                raw_content=html_content,
                markdown_content=markdown_content,
                structured_data=structured_data,
                metadata={
                    "ticker": ticker,
                    "cik": cik,
                    "source": "SEC EDGAR",
                    "html_size": len(html_content),
                },
            )

        except Exception:
            self.logger.error("Failed to fetch document", document_id=document_id, error_code="DOC_FETCH_ERROR")
            return None

    async def _fetch_xbrl_data(
        self, cik: str, accession_clean: str, form_type: str
    ) -> dict[str, Any] | None:
        """Fetch XBRL financial data for a filing.

        Args:
            cik: 10-digit CIK
            accession_clean: Accession number without dashes
            form_type: Filing form type

        Returns:
            Parsed XBRL data or None
        """
        try:
            # XBRL instance document URL pattern
            xbrl_url = f"{self.ARCHIVES_URL}/{cik}/{accession_clean}/FilingSummary.xml"

            response = await self._rate_limited_request("GET", xbrl_url)

            # For now, return raw XML content
            # Full XBRL parsing would be in xbrl_parser.py
            return SECEdgarAdapter__fetch_xbrl_dataResult.model_validate({
                "xbrl_available": True,
                "xbrl_url": xbrl_url,
                "xbrl_xml_size": len(response.text),
                "parsed": False,  # Would be True if fully parsed
            })


        except Exception:
            self.logger.debug("XBRL not available", cik=cik, error_code="XBRL_UNAVAILABLE")
            return None

    def _html_to_markdown(self, html_content: str, document_id: str) -> str:
        """Convert SEC filing HTML to Markdown.

        Simplified conversion - for production, use content_extractor.ContentExtractor.
        """
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "head"]):
                script.decompose()

            # Get text
            text = soup.get_text(separator="\n")

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)

            # Add header
            header = f"# SEC Filing: {document_id}\n\n"

            return header + text

        except Exception:
            self.logger.error("HTML to Markdown conversion failed", error_code="HTML_TO_MD_ERROR")
            return f"# SEC Filing: {document_id}\n\n[HTML content conversion failed]"

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

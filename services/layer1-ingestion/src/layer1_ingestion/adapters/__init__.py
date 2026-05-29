"""Data source adapters for Layer 1 Ingestion.

Provides adapters for:
- SEC EDGAR (financial filings)
- USPTO Patents (patent search)
- News sources (GDELT, NewsAPI)
- Website crawling (via PlaywrightCrawler)
"""

from .base import (
    AdapterConfig,
    AdapterType,
    DataSourceAdapter,
    FilingDocument,
    FilingType,
    SearchResult,
)

try:
    from .pdf_adapter import PDFAdapter, PDFAdapterConfig
except ImportError:
    PDFAdapter = None  # type: ignore[assignment,misc]
    PDFAdapterConfig = None  # type: ignore[assignment,misc]
from .registry import AdapterRegistry, get_registry
from .sec_edgar import SECEdgarAdapter
from .xbrl_parser import FinancialFact, FinancialStatement, ParsedXBRL, XBRLParser

__all__ = [
    # Base classes
    "DataSourceAdapter",
    "AdapterType",
    "AdapterConfig",
    "FilingType",
    "FilingDocument",
    "SearchResult",
    # Implementations
    "SECEdgarAdapter",
    "PDFAdapter",
    "PDFAdapterConfig",
    "XBRLParser",
    "ParsedXBRL",
    "FinancialFact",
    "FinancialStatement",
    # Registry
    "AdapterRegistry",
    "get_registry",
]

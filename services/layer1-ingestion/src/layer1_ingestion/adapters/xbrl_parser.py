"""XBRL parser for extracting structured financial data from SEC filings.

XBRL (eXtensible Business Reporting Language) is the standard for financial
reporting to the SEC. This module parses XBRL instance documents and extracts
key financial metrics.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

import structlog
from defusedxml.ElementTree import fromstring

from ..metrics import get_metrics

logger = structlog.get_logger()


# Common XBRL namespaces
XBRL_NAMESPACES = {
    "xbrl": "http://www.xbrl.org/2003/instance",
    "xlink": "http://www.w3.org/1999/xlink",
    "link": "http://www.xbrl.org/2003/linkbase",
    "us-gaap": "http://fasb.org/us-gaap/2023",
    "dei": "http://xbrl.sec.gov/dei/2023",
    "iso4217": "http://www.xbrl.org/2003/iso4217",
}


@dataclass
class FinancialFact:
    """A single XBRL financial fact."""

    concept: str  # e.g., "us-gaap:Revenues"
    value: Any
    unit: str | None = None  # e.g., "USD", "shares"
    context_ref: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    dimensions: dict[str, str] = field(default_factory=dict)


@dataclass
class FinancialStatement:
    """Represents a financial statement (Balance Sheet, Income Statement, etc.)."""

    statement_type: str  # BalanceSheet, IncomeStatement, CashFlow, etc.
    period_end: datetime | None = None
    period_start: datetime | None = None
    facts: list[FinancialFact] = field(default_factory=list)

    def get_fact(self, concept_pattern: str) -> FinancialFact | None:
        """Get a fact by concept name pattern."""
        for fact in self.facts:
            if concept_pattern.lower() in fact.concept.lower():
                return fact
        return None


@dataclass
class ParsedXBRL:
    """Complete parsed XBRL document."""

    entity: str | None = None
    document_type: str | None = None  # 10-K, 10-Q, etc.
    document_period: datetime | None = None
    fiscal_year: int | None = None
    fiscal_period: str | None = None  # Q1, Q2, Q3, FY

    # Financial statements
    balance_sheet: FinancialStatement | None = None
    income_statement: FinancialStatement | None = None
    cash_flow_statement: FinancialStatement | None = None

    # Key metrics (extracted for quick access)
    key_metrics: dict[str, Any] = field(default_factory=dict)

    # All facts
    all_facts: list[FinancialFact] = field(default_factory=list)

    # Raw parsed data for advanced queries
    raw_contexts: dict[str, dict] = field(default_factory=dict)
    raw_units: dict[str, str] = field(default_factory=dict)


class XBRLParser:
    """Parser for XBRL instance documents.

    Extracts structured financial data from SEC filing XBRL files.
    """

    # Key concept mappings for common financial metrics
    CONCEPT_MAPPINGS = {
        # Revenue/Sales
        "revenue": [
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "SalesRevenueNet",
        ],
        "net_income": ["NetIncomeLoss", "ProfitLoss", "NetIncome"],
        "gross_profit": ["GrossProfit"],
        "operating_income": ["OperatingIncomeLoss"],
        "ebitda": ["EBITDA"],
        # Balance Sheet
        "total_assets": ["Assets"],
        "total_liabilities": ["Liabilities"],
        "stockholders_equity": ["StockholdersEquity", "ShareholdersEquity"],
        "cash_and_equivalents": ["CashAndCashEquivalentsAtCarryingValue", "CashAndCashEquivalents"],
        "total_debt": ["LongTermDebt", "DebtAndCapitalLeaseObligations"],
        # Cash Flow
        "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
        "free_cash_flow": ["FreeCashFlow"],
        "capital_expenditures": [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "CapitalExpenditures",
        ],
        # Per Share
        "earnings_per_share": ["EarningsPerShareBasic", "EarningsPerShareDiluted"],
        "shares_outstanding": [
            "CommonStockSharesOutstanding",
            "EntityCommonStockSharesOutstanding",
        ],
    }

    def __init__(self):
        self.logger = logger

    def parse(self, xbrl_xml: str) -> ParsedXBRL:
        """Parse XBRL XML content.

        Args:
            xbrl_xml: Raw XBRL XML string

        Returns:
            ParsedXBRL with structured financial data
        """
        try:
            # P1-20 FIX: Use defusedxml.fromstring to prevent XXE attacks
            root = fromstring(xbrl_xml)

            # Extract contexts (define periods and dimensions)
            contexts = self._extract_contexts(root)

            # Extract units
            units = self._extract_units(root)

            # Extract facts
            facts = self._extract_facts(root, contexts, units)

            # Build financial statements
            result = self._build_financial_statements(facts)

            # Extract entity info
            result.entity = self._extract_entity(root)
            result.document_type = self._extract_document_type(root)
            result.raw_contexts = contexts
            result.raw_units = units
            result.all_facts = facts

            # Extract key metrics
            result.key_metrics = self._extract_key_metrics(facts)

            self.logger.info(
                "XBRL parsed successfully",
                entity=result.entity,
                facts_count=len(facts),
                document_type=result.document_type,
            )

            return result

        except ET.ParseError:
            self.logger.error("XBRL XML parse error", error_code="XBRL_PARSE_ERROR")
            return ParsedXBRL()
        except Exception:
            self.logger.error("XBRL parsing failed", error_code="XBRL_PARSING_ERROR")
            return ParsedXBRL()

    def _extract_contexts(self, root: ET.Element) -> dict[str, dict]:
        """Extract context definitions from XBRL."""
        contexts = {}

        # Find all context elements (can be in different namespaces)
        context_elements = root.findall(".//{http://www.xbrl.org/2003/instance}context")
        if not context_elements:
            # Try without namespace
            context_elements = root.findall(".//context")

        for ctx in context_elements:
            ctx_id = ctx.get("id")
            if not ctx_id:
                continue

            context_data = {"id": ctx_id}

            # Extract period
            period = ctx.find(".//{http://www.xbrl.org/2003/instance}period")
            if period is None:
                period = ctx.find(".//period")

            if period is not None:
                # Instant date (for balance sheet items)
                instant = period.find(".//{http://www.xbrl.org/2003/instance}instant")
                if instant is None:
                    instant = period.find(".//instant")

                if instant is not None and instant.text:
                    context_data["instant"] = self._parse_date(instant.text)

                # Duration period
                start = period.find(".//{http://www.xbrl.org/2003/instance}startDate")
                end = period.find(".//{http://www.xbrl.org/2003/instance}endDate")

                if start is None:
                    start = period.find(".//startDate")
                if end is None:
                    end = period.find(".//endDate")

                if start is not None and start.text:
                    context_data["start_date"] = self._parse_date(start.text)
                if end is not None and end.text:
                    context_data["end_date"] = self._parse_date(end.text)
                if end is not None and end.text:
                    context_data["instant"] = self._parse_date(end.text)

            # Extract entity identifier
            entity = ctx.find(".//{http://www.xbrl.org/2003/instance}entity")
            if entity is None:
                entity = ctx.find(".//entity")

            if entity is not None:
                identifier = entity.find(".//{http://www.xbrl.org/2003/instance}identifier")
                if identifier is None:
                    identifier = entity.find(".//identifier")
                if identifier is not None and identifier.text:
                    context_data["entity"] = identifier.text

            # Extract dimensions (segment data)
            segment = ctx.find(".//{http://www.xbrl.org/2003/instance}segment")
            if segment is None:
                segment = ctx.find(".//segment")

            if segment is not None:
                dimensions = {}
                for dim in segment:
                    dim_name = dim.tag.split("}")[-1] if "}" in dim.tag else dim.tag
                    dimensions[dim_name] = dim.text or ""
                context_data["dimensions"] = dimensions

            contexts[ctx_id] = context_data

        return contexts

    def _extract_units(self, root: ET.Element) -> dict[str, str]:
        """Extract unit definitions from XBRL."""
        units = {}

        unit_elements = root.findall(".//{http://www.xbrl.org/2003/instance}unit")
        if not unit_elements:
            unit_elements = root.findall(".//unit")

        for unit in unit_elements:
            unit_id = unit.get("id")
            if not unit_id:
                continue

            # Simple measure
            measure = unit.find(".//{http://www.xbrl.org/2003/instance}measure")
            if measure is None:
                measure = unit.find(".//measure")

            if measure is not None and measure.text:
                units[unit_id] = measure.text
            else:
                # Divide (e.g., per share)
                divide = unit.find(".//{http://www.xbrl.org/2003/instance}divide")
                if divide is None:
                    divide = unit.find(".//divide")

                if divide is not None:
                    units[unit_id] = "ratio"

        return units

    def _extract_facts(
        self, root: ET.Element, contexts: dict[str, dict], units: dict[str, str]
    ) -> list[FinancialFact]:
        """Extract all facts from XBRL."""
        facts = []

        # Iterate through all elements with contextRef (these are facts)
        for elem in root.iter():
            context_ref = elem.get("contextRef")
            if not context_ref:
                continue

            # Skip context and unit definitions
            tag_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag_name in ["context", "unit"]:
                continue

            # Get value
            value_text = elem.text
            if not value_text:
                continue

            # Parse value
            value = self._parse_value(value_text)

            # Get context info
            ctx = contexts.get(context_ref, {})

            # Get unit
            unit_ref = elem.get("unitRef")
            unit = units.get(unit_ref) if unit_ref else None

            # Get decimals/scale info
            decimals = elem.get("decimals")
            scale = 0
            if decimals and decimals != "INF":
                try:
                    scale = int(decimals)
                except ValueError:
                    logger.warning(
                        "xbrl_decimals_parse_failed",
                        concept=tag_name,
                        decimals_value=decimals,
                        context_ref=context_ref,
                        fallback="skipping_fact",
                    )
                    metrics = get_metrics()
                    if metrics:
                        metrics.increment_errors(error_type="xbrl_parse_fallback", component="xbrl_parser")
                    continue

            # Apply scale if needed
            if scale != 0 and isinstance(value, (int, float, Decimal)):
                value = value * (10**scale)

            fact = FinancialFact(
                concept=tag_name,
                value=value,
                unit=unit,
                context_ref=context_ref,
                period_start=ctx.get("start_date"),
                period_end=ctx.get("end_date"),
                dimensions=ctx.get("dimensions", {}),
            )

            facts.append(fact)

        return facts

    def _build_financial_statements(self, facts: list[FinancialFact]) -> ParsedXBRL:
        """Organize facts into financial statements."""
        result = ParsedXBRL()

        # Categorize facts by statement type
        balance_facts = []
        income_facts = []
        cash_flow_facts = []

        for fact in facts:
            concept_lower = fact.concept.lower()

            # Balance sheet indicators
            if any(
                x in concept_lower
                for x in ["asset", "liabilit", "equity", "cash", "inventory", "receivable"]
            ):
                balance_facts.append(fact)
            # Income statement indicators
            elif any(
                x in concept_lower
                for x in ["revenue", "income", "expense", "profit", "loss", "ebit", "cost"]
            ):
                income_facts.append(fact)
            # Cash flow indicators
            elif any(
                x in concept_lower
                for x in ["cashflow", "cash.flow", "operating", "investing", "financing"]
            ):
                cash_flow_facts.append(fact)

        # Build statements
        if balance_facts:
            result.balance_sheet = self._build_statement("BalanceSheet", balance_facts)

        if income_facts:
            result.income_statement = self._build_statement("IncomeStatement", income_facts)

        if cash_flow_facts:
            result.cash_flow_statement = self._build_statement("CashFlowStatement", cash_flow_facts)

        return result

    def _build_statement(
        self, statement_type: str, facts: list[FinancialFact]
    ) -> FinancialStatement:
        """Build a single financial statement from facts."""
        # Find the most recent period
        latest_fact = max(
            (f for f in facts if f.period_end),
            key=lambda f: f.period_end or datetime.min,
            default=None,
        )

        period_end = latest_fact.period_end if latest_fact else None
        period_start = latest_fact.period_start if latest_fact else None

        return FinancialStatement(
            statement_type=statement_type,
            period_end=period_end,
            period_start=period_start,
            facts=facts,
        )

    def _extract_key_metrics(self, facts: list[FinancialFact]) -> dict[str, Any]:
        """Extract commonly used financial metrics."""
        metrics = {}

        for metric_name, concept_patterns in self.CONCEPT_MAPPINGS.items():
            for pattern in concept_patterns:
                matching_facts = [f for f in facts if pattern.lower() in f.concept.lower()]

                if matching_facts:
                    # Get the most recent value
                    latest = max(
                        matching_facts, key=lambda f: f.period_end or datetime.min, default=None
                    )

                    if latest:
                        metrics[metric_name] = {
                            "value": latest.value,
                            "unit": latest.unit,
                            "period_end": latest.period_end.isoformat()
                            if latest.period_end
                            else None,
                            "concept": latest.concept,
                        }
                        break

        return metrics

    def _extract_entity(self, root: ET.Element) -> str | None:
        """Extract entity identifier from DEI."""
        # Try to find entity central index key
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if "EntityCentralIndexKey" in tag or "EntityRegistrantName" in tag:
                if elem.text:
                    return elem.text
        raise XBRLParseError(f"Invalid XBRL date: {date_str}")

    def _extract_document_type(self, root: ET.Element) -> str | None:
        """Extract document type from DEI."""
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if "DocumentType" in tag:
                if elem.text:
                    return elem.text
        return None

    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse date string to datetime."""
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    def _parse_value(self, value: str) -> Any:
        """Parse a value string to appropriate type."""
        # Try integer
        try:
            return int(value)
        except ValueError:
            logger.debug("xbrl_value_parse_fallback", target_type="int", value_preview=value[:50] if len(value) > 50 else value)
            metrics = get_metrics()
            if metrics:
                metrics.increment_errors(error_type="xbrl_value_parse_fallback", component="xbrl_parser")

        # Try decimal
        try:
            return Decimal(value)
        except Exception:
            logger.debug("xbrl_value_parse_fallback", target_type="decimal", value_preview=value[:50] if len(value) > 50 else value)
            metrics = get_metrics()
            if metrics:
                metrics.increment_errors(error_type="xbrl_value_parse_fallback", component="xbrl_parser")

        # Return as string
        return value

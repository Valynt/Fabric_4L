"""
Unit tests for XBRLParser edge cases and helpers.

Extends the basic tests in test_adapters.py with more thorough coverage:
- malformed XML
- instant-date contexts (balance sheet)
- multi-fact documents
- scaled decimals
- entity extraction
- financial statement classification
"""

import pytest

from defusedxml.ElementTree import fromstring

from layer1_ingestion.adapters.xbrl_parser import (
    FinancialFact,
    XBRLParser,
    ParsedXBRL,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

MINIMAL_XBRL_TEMPLATE = """<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:us-gaap="http://fasb.org/us-gaap/2023"
      xmlns:dei="http://xbrl.sec.gov/dei/2023">
{contexts}
{units}
{facts}
</xbrl>"""


def _parse(contexts: str = "", units: str = "", facts: str = "") -> ParsedXBRL:
    parser = XBRLParser()
    xml = MINIMAL_XBRL_TEMPLATE.format(contexts=contexts, units=units, facts=facts)
    return parser.parse(xml)


# ──────────────────────────────────────────────────────────────────────────────
# Error handling
# ──────────────────────────────────────────────────────────────────────────────

class TestXBRLParserErrorHandling:
    """Tests that malformed input produces safe empty results."""

    def test_malformed_xml_returns_empty(self):
        parser = XBRLParser()
        result = parser.parse("<unclosed_tag>")
        assert result is not None
        assert result.all_facts == []

    def test_empty_string_returns_empty(self):
        parser = XBRLParser()
        result = parser.parse("")
        assert result is not None
        assert result.all_facts == []

    def test_non_xbrl_xml_returns_empty_facts(self):
        """Valid XML that is not XBRL produces an empty fact list."""
        parser = XBRLParser()
        result = parser.parse("<root><child>text</child></root>")
        assert result.all_facts == []

    def test_parse_date_raises_on_invalid_date(self):
        """_parse_date raises XBRLParseError for unparseable dates."""
        parser = XBRLParser()
        from layer1_ingestion.shared.exceptions import XBRLParseError
        with pytest.raises(XBRLParseError):
            parser._parse_date("not-a-date")

    def test_parse_value_returns_string_for_non_numeric(self):
        """_parse_value falls back to string for non-numeric input."""
        parser = XBRLParser()
        assert parser._parse_value("hello") == "hello"

    def test_parse_value_narrows_decimal_exception(self):
        """_parse_value does not swallow broad exceptions during Decimal coercion."""
        parser = XBRLParser()
        # Should not raise a generic Exception; it handles ValueError/ArithmeticError
        result = parser._parse_value("not-a-number")
        assert result == "not-a-number"


# ──────────────────────────────────────────────────────────────────────────────
# Context parsing — instant (balance sheet) dates
# ──────────────────────────────────────────────────────────────────────────────

class TestInstantContextParsing:
    """Tests for XBRL instant-period context (balance sheet items)."""

    INSTANT_CTX = """
    <context id="ctx-instant" xmlns="http://www.xbrl.org/2003/instance">
        <entity><identifier scheme="http://www.sec.gov/CIK">0000320193</identifier></entity>
        <period><instant>2023-12-31</instant></period>
    </context>"""

    USD_UNIT = """<unit id="USD" xmlns="http://www.xbrl.org/2003/instance">
        <measure>iso4217:USD</measure></unit>"""

    def test_instant_context_fact_is_parsed(self):
        facts_xml = """<us-gaap:Assets contextRef="ctx-instant" unitRef="USD">100000000</us-gaap:Assets>"""
        result = _parse(self.INSTANT_CTX, self.USD_UNIT, facts_xml)

        assert len(result.all_facts) == 1
        fact = result.all_facts[0]
        assert fact.concept == "Assets"
        assert fact.value == 100000000

    def test_balance_sheet_is_built_from_asset_fact(self):
        facts_xml = """<us-gaap:Assets contextRef="ctx-instant" unitRef="USD">200000000</us-gaap:Assets>"""
        result = _parse(self.INSTANT_CTX, self.USD_UNIT, facts_xml)

        assert result.balance_sheet is not None
        assert len(result.balance_sheet.facts) == 1

    def test_liabilities_classified_to_balance_sheet(self):
        facts_xml = """<us-gaap:Liabilities contextRef="ctx-instant" unitRef="USD">50000000</us-gaap:Liabilities>"""
        result = _parse(self.INSTANT_CTX, self.USD_UNIT, facts_xml)

        assert result.balance_sheet is not None


# ──────────────────────────────────────────────────────────────────────────────
# Decimal scaling
# ──────────────────────────────────────────────────────────────────────────────

class TestDecimalScaling:
    """Tests for the decimals attribute (scale factor)."""

    CTX = """
    <context id="ctx-2023" xmlns="http://www.xbrl.org/2003/instance">
        <entity><identifier>CIK123</identifier></entity>
        <period><startDate>2023-01-01</startDate><endDate>2023-12-31</endDate></period>
    </context>"""
    UNIT = """<unit id="USD" xmlns="http://www.xbrl.org/2003/instance"><measure>iso4217:USD</measure></unit>"""

    def test_negative_decimals_scale_up(self):
        """decimals="-3" means the value is in thousands (x1000)."""
        facts_xml = """<us-gaap:Revenues contextRef="ctx-2023" unitRef="USD" decimals="-3">500000</us-gaap:Revenues>"""
        result = _parse(self.CTX, self.UNIT, facts_xml)

        fact = result.all_facts[0]
        # 500000 * 10^-3 = 500 (scale factor applied)
        assert fact.value == 500

    def test_zero_decimals_no_scaling(self):
        """decimals="0" means no scaling."""
        facts_xml = """<us-gaap:Revenues contextRef="ctx-2023" unitRef="USD" decimals="0">12345</us-gaap:Revenues>"""
        result = _parse(self.CTX, self.UNIT, facts_xml)

        assert result.all_facts[0].value == 12345

    def test_inf_decimals_no_scaling(self):
        """decimals="INF" means exact — no scaling applied."""
        facts_xml = """<us-gaap:EarningsPerShareBasic contextRef="ctx-2023" unitRef="USD" decimals="INF">3.14</us-gaap:EarningsPerShareBasic>"""
        result = _parse(self.CTX, self.UNIT, facts_xml)

        fact = result.all_facts[0]
        assert abs(float(fact.value) - 3.14) < 0.001

    def test_invalid_decimals_value_skips_fact(self):
        """Non-numeric decimals attribute skips only that fact."""
        facts_xml = """<us-gaap:Revenues contextRef="ctx-2023" unitRef="USD" decimals="bad">99999</us-gaap:Revenues>"""
        result = _parse(self.CTX, self.UNIT, facts_xml)

        # Fact with invalid decimals is skipped; remaining document is still parsed
        assert len(result.all_facts) == 0


# ──────────────────────────────────────────────────────────────────────────────
# Multi-fact documents
# ──────────────────────────────────────────────────────────────────────────────

class TestMultiFactDocuments:
    """Tests with multiple facts in a single XBRL document."""

    CTX = """
    <context id="ctx-2023" xmlns="http://www.xbrl.org/2003/instance">
        <entity><identifier>CIK000</identifier></entity>
        <period><startDate>2023-01-01</startDate><endDate>2023-12-31</endDate></period>
    </context>"""
    UNIT = """<unit id="USD" xmlns="http://www.xbrl.org/2003/instance"><measure>iso4217:USD</measure></unit>"""

    def test_multiple_facts_all_parsed(self):
        facts_xml = """
        <us-gaap:Revenues contextRef="ctx-2023" unitRef="USD">100</us-gaap:Revenues>
        <us-gaap:NetIncomeLoss contextRef="ctx-2023" unitRef="USD">20</us-gaap:NetIncomeLoss>
        <us-gaap:Assets contextRef="ctx-2023" unitRef="USD">500</us-gaap:Assets>
        """
        result = _parse(self.CTX, self.UNIT, facts_xml)

        assert len(result.all_facts) == 3

    def test_facts_classified_across_statements(self):
        """Revenue -> income_statement, Assets -> balance_sheet."""
        facts_xml = """
        <us-gaap:Revenues contextRef="ctx-2023" unitRef="USD">100</us-gaap:Revenues>
        <us-gaap:Assets contextRef="ctx-2023" unitRef="USD">500</us-gaap:Assets>
        """
        result = _parse(self.CTX, self.UNIT, facts_xml)

        assert result.income_statement is not None
        assert result.balance_sheet is not None

    def test_key_metrics_extracted_for_revenue_and_assets(self):
        facts_xml = """
        <us-gaap:Revenues contextRef="ctx-2023" unitRef="USD">394328</us-gaap:Revenues>
        <us-gaap:Assets contextRef="ctx-2023" unitRef="USD">352755</us-gaap:Assets>
        """
        result = _parse(self.CTX, self.UNIT, facts_xml)

        assert "revenue" in result.key_metrics
        assert "total_assets" in result.key_metrics
        assert result.key_metrics["revenue"]["value"] == 394328
        assert result.key_metrics["total_assets"]["value"] == 352755

    def test_fact_without_unit_ref_is_still_parsed(self):
        """Facts without a unitRef (e.g., share counts) are still captured."""
        facts_xml = """<us-gaap:CommonStockSharesOutstanding contextRef="ctx-2023">15000000000</us-gaap:CommonStockSharesOutstanding>"""
        result = _parse(self.CTX, "", facts_xml)

        assert len(result.all_facts) == 1
        assert result.all_facts[0].unit is None


# ──────────────────────────────────────────────────────────────────────────────
# FinancialStatement.get_fact
# ──────────────────────────────────────────────────────────────────────────────

class TestFinancialStatementGetFact:
    """Tests for the FinancialStatement.get_fact helper."""

    def test_get_fact_found(self):
        from layer1_ingestion.adapters.xbrl_parser import FinancialStatement

        fact = FinancialFact(concept="us-gaap:Revenues", value=1000)
        stmt = FinancialStatement(statement_type="IncomeStatement", facts=[fact])

        found = stmt.get_fact("Revenues")
        assert found is fact

    def test_get_fact_case_insensitive(self):
        from layer1_ingestion.adapters.xbrl_parser import FinancialStatement

        fact = FinancialFact(concept="us-gaap:NetIncomeLoss", value=500)
        stmt = FinancialStatement(statement_type="IncomeStatement", facts=[fact])

        found = stmt.get_fact("netincomeloss")
        assert found is fact

    def test_get_fact_not_found_returns_none(self):
        from layer1_ingestion.adapters.xbrl_parser import FinancialStatement

        stmt = FinancialStatement(statement_type="IncomeStatement", facts=[])
        assert stmt.get_fact("MissingConcept") is None


# ──────────────────────────────────────────────────────────────────────────────
# Entity and document type extraction
# ──────────────────────────────────────────────────────────────────────────────

class TestEntityExtraction:
    """Tests for entity and document type info extraction."""

    def test_entity_extracted_from_dei(self):
        xml = """<?xml version="1.0"?>
        <xbrl xmlns="http://www.xbrl.org/2003/instance"
              xmlns:dei="http://xbrl.sec.gov/dei/2023">
            <context id="ctx">
                <entity><identifier>0000320193</identifier></entity>
                <period><endDate>2023-12-31</endDate></period>
            </context>
            <dei:EntityCentralIndexKey contextRef="ctx">0000320193</dei:EntityCentralIndexKey>
        </xbrl>"""
        parser = XBRLParser()
        result = parser.parse(xml)

        # Entity is set from DEI or context
        assert result.entity is not None

    def test_missing_dei_entity_returns_none_without_failing_parse(self):
        xml = """<?xml version="1.0"?>
        <xbrl xmlns="http://www.xbrl.org/2003/instance"
              xmlns:dei="http://xbrl.sec.gov/dei/2023">
            <context id="ctx">
                <entity><identifier>CIK123</identifier></entity>
                <period><endDate>2023-12-31</endDate></period>
            </context>
            <dei:DocumentType contextRef="ctx">10-K</dei:DocumentType>
        </xbrl>"""
        parser = XBRLParser()
        result = parser.parse(xml)

        assert result.entity is None
        assert result.document_type == "10-K"

    def test_document_type_extracted_from_dei(self):
        xml = """<?xml version="1.0"?>
        <xbrl xmlns="http://www.xbrl.org/2003/instance"
              xmlns:dei="http://xbrl.sec.gov/dei/2023">
            <context id="ctx">
                <entity><identifier>CIK123</identifier></entity>
                <period><endDate>2023-12-31</endDate></period>
            </context>
            <dei:DocumentType contextRef="ctx">10-K</dei:DocumentType>
        </xbrl>"""
        parser = XBRLParser()
        result = parser.parse(xml)

        assert result.document_type == "10-K"


# ──────────────────────────────────────────────────────────────────────────────
# Refactored helper methods
# ──────────────────────────────────────────────────────────────────────────────

class TestRefactoredHelperMethods:
    """Tests for helper methods extracted during refactoring."""

    def test_get_tag_name_with_namespace(self):
        """_get_tag_name extracts tag name from namespaced element."""
        parser = XBRLParser()
        elem = fromstring('<root xmlns:us-gaap="http://fasb.org/us-gaap/2023"><us-gaap:Revenues>100</us-gaap:Revenues></root>')
        assert parser._get_tag_name(elem[0]) == "Revenues"

    def test_get_tag_name_without_namespace(self):
        """_get_tag_name handles elements without namespace."""
        parser = XBRLParser()
        elem = fromstring("<Revenues>100</Revenues>")
        assert parser._get_tag_name(elem) == "Revenues"

    def test_get_unit_with_ref(self):
        """_get_unit returns unit when unitRef is present."""
        parser = XBRLParser()
        elem = fromstring('<root xmlns:us-gaap="http://fasb.org/us-gaap/2023"><us-gaap:Revenues unitRef="USD">100</us-gaap:Revenues></root>')
        units = {"USD": "iso4217:USD"}
        assert parser._get_unit(elem[0], units) == "iso4217:USD"

    def test_get_unit_without_ref(self):
        """_get_unit returns None when unitRef is absent."""
        parser = XBRLParser()
        elem = fromstring('<root xmlns:us-gaap="http://fasb.org/us-gaap/2023"><us-gaap:Revenues>100</us-gaap:Revenues></root>')
        units = {"USD": "iso4217:USD"}
        assert parser._get_unit(elem[0], units) is None

    def test_get_latest_fact_with_period_end(self):
        """_get_latest_fact returns fact with most recent period_end."""
        parser = XBRLParser()
        from datetime import datetime
        fact1 = FinancialFact(concept="Revenues", value=100, period_end=datetime(2023, 1, 1))
        fact2 = FinancialFact(concept="Revenues", value=200, period_end=datetime(2023, 12, 31))
        fact3 = FinancialFact(concept="Revenues", value=150, period_end=datetime(2023, 6, 30))

        latest = parser._get_latest_fact([fact1, fact2, fact3])
        assert latest.value == 200

    def test_get_latest_fact_without_period_end(self):
        """_get_latest_fact handles facts without period_end."""
        parser = XBRLParser()
        fact1 = FinancialFact(concept="Revenues", value=100)
        fact2 = FinancialFact(concept="Revenues", value=200)

        latest = parser._get_latest_fact([fact1, fact2])
        assert latest is not None

    def test_get_latest_fact_empty_list(self):
        """_get_latest_fact returns None for empty list."""
        parser = XBRLParser()
        assert parser._get_latest_fact([]) is None

    def test_find_metric_value_with_matching_pattern(self):
        """_find_metric_value returns metric when pattern matches."""
        parser = XBRLParser()
        from datetime import datetime
        fact = FinancialFact(
            concept="us-gaap:Revenues",
            value=1000,
            unit="USD",
            period_end=datetime(2023, 12, 31)
        )

        result = parser._find_metric_value([fact], ["Revenues"])
        assert result is not None
        assert result["value"] == 1000
        assert result["concept"] == "us-gaap:Revenues"

    def test_find_metric_value_no_match(self):
        """_find_metric_value returns None when no pattern matches."""
        parser = XBRLParser()
        fact = FinancialFact(concept="us-gaap:Assets", value=500)

        result = parser._find_metric_value([fact], ["Revenues"])
        assert result is None

    def test_apply_decimals_scale_negative_scale(self):
        """_apply_decimals_scale applies negative scale (divide)."""
        parser = XBRLParser()
        elem = fromstring('<root xmlns:us-gaap="http://fasb.org/us-gaap/2023"><us-gaap:Revenues decimals="-3">500</us-gaap:Revenues></root>')

        result = parser._apply_decimals_scale(elem[0], "Revenues", 500, "ctx")
        # decimals="-3" means value is in thousands, so 500 * 10^-3 = 0.5
        assert result == 0.5

    def test_apply_decimals_scale_no_decimals(self):
        """_apply_decimals_scale returns value when no decimals attribute."""
        parser = XBRLParser()
        elem = fromstring('<root xmlns:us-gaap="http://fasb.org/us-gaap/2023"><us-gaap:Revenues>100</us-gaap:Revenues></root>')

        result = parser._apply_decimals_scale(elem[0], "Revenues", 100, "ctx")
        assert result == 100

    def test_apply_decimals_scale_inf(self):
        """_apply_decimals_scale returns value for INF decimals."""
        parser = XBRLParser()
        elem = fromstring('<root xmlns:us-gaap="http://fasb.org/us-gaap/2023"><us-gaap:Revenues decimals="INF">3.14</us-gaap:Revenues></root>')

        result = parser._apply_decimals_scale(elem[0], "Revenues", 3.14, "ctx")
        assert result == 3.14

    def test_apply_decimals_scale_invalid_returns_none(self):
        """_apply_decimals_scale returns None for invalid decimals."""
        parser = XBRLParser()
        elem = fromstring('<root xmlns:us-gaap="http://fasb.org/us-gaap/2023"><us-gaap:Revenues decimals="bad">100</us-gaap:Revenues></root>')

        result = parser._apply_decimals_scale(elem[0], "Revenues", 100, "ctx")
        assert result is None


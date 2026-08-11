"""Static security regression tests: defusedxml is required for XML parsing.

These tests analyze source code directly — no runtime dependencies.
They fail if standard xml.etree.ElementTree is used for XBRL parsing.
"""

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
XBRL_PARSER_PY = (
    REPO_ROOT
    / "services"
    / "layer1-ingestion"
    / "src"
    / "layer1_ingestion"
    / "adapters"
    / "xbrl_parser.py"
)


class TestDefusedxmlRequired:
    """P1-20: defusedxml must be used for all XML parsing to prevent XXE."""

    @pytest.mark.security
    def test_xbrl_parser_imports_defusedxml(self):
        """xbrl_parser.py must import from defusedxml, not xml.etree."""
        source = XBRL_PARSER_PY.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Must import from defusedxml
        has_defusedxml_import = False
        has_xml_etree_import = False

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "defusedxml" in node.module:
                    has_defusedxml_import = True
                if node.module and node.module.startswith("xml.etree"):
                    has_xml_etree_import = True

        assert has_defusedxml_import, (
            "xbrl_parser.py must import from defusedxml for XXE prevention"
        )
        assert not has_xml_etree_import, (
            "xbrl_parser.py must not import from xml.etree — use defusedxml instead"
        )

    @pytest.mark.security
    def test_xbrl_parser_uses_defusedxml_fromstring(self):
        """XBRLParser.parse must call defusedxml.fromstring, not ET.fromstring."""
        source = XBRL_PARSER_PY.read_text(encoding="utf-8")

        # Must use defusedxml's fromstring
        assert "from defusedxml.ElementTree import fromstring" in source, (
            "xbrl_parser.py must import defusedxml.fromstring"
        )

        # Must call fromstring in parse method
        assert "fromstring(xbrl_xml)" in source, (
            "xbrl_parser.py must call defusedxml.fromstring(xbrl_xml)"
        )

    @pytest.mark.security
    def test_no_et_fromstring_in_xbrl_parser(self):
        """xbrl_parser.py must not call xml.etree.ElementTree.fromstring directly."""
        source = XBRL_PARSER_PY.read_text(encoding="utf-8")

        banned = [
            "ET.fromstring",
            "ElementTree.fromstring",
            "xml.etree.ElementTree.fromstring",
        ]

        lines = source.splitlines()
        for i, line in enumerate(lines):
            for pattern in banned:
                assert pattern not in line, (
                    f"Line {i + 1}: banned xml.etree.fromstring usage: {line.strip()}"
                )

    @pytest.mark.security
    def test_defusedxml_blocks_xxe_at_runtime(self):
        """Verify defusedxml actually blocks XXE payloads."""
        try:
            from defusedxml.ElementTree import fromstring
        except ImportError:
            pytest.skip("defusedxml not installed")

        xxe_payload = """<?xml version="1.0"?>
        <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
        <root>&xxe;</root>
        """

        # defusedxml should raise on XXE
        with pytest.raises(Exception):
            fromstring(xxe_payload)

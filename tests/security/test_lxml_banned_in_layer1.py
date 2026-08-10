"""Static security regression tests: lxml parser is banned in Layer 1 ingestion.

These tests analyze source code directly — no runtime dependencies.
They fail if lxml is ever used as a BeautifulSoup parser in Layer 1.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_EXTRACTOR_PY = (
    REPO_ROOT
    / "services"
    / "layer1-ingestion"
    / "src"
    / "layer1_ingestion"
    / "post_processor"
    / "content_extractor.py"
)


class TestLxmlBannedInLayer1:
    """P1-20: lxml parser must never be used in Layer 1 content extraction."""

    @pytest.mark.security
    def test_content_extractor_never_uses_lxml_parser(self):
        """content_extractor.py must not pass 'lxml' to BeautifulSoup."""
        source = CONTENT_EXTRACTOR_PY.read_text(encoding="utf-8")

        # Ban lxml as parser argument
        banned_patterns = [
            '"lxml"',
            "'lxml'",
            '"lxml-xml"',
            "'lxml-xml'",
        ]

        lines = source.splitlines()
        for i, line in enumerate(lines):
            for pattern in banned_patterns:
                assert pattern not in line, (
                    f"Line {i + 1}: banned lxml parser usage: {line.strip()}"
                )

    @pytest.mark.security
    def test_content_extractor_uses_html_parser(self):
        """content_extractor.py must use html.parser for BeautifulSoup."""
        source = CONTENT_EXTRACTOR_PY.read_text(encoding="utf-8")

        # Must have html.parser usage
        assert '"html.parser"' in source or "'html.parser'" in source, (
            "content_extractor.py must use html.parser for XXE prevention"
        )

    @pytest.mark.security
    def test_beautifulsoup_calls_use_safe_parser(self):
        """Every BeautifulSoup call must use html.parser."""
        import ast

        source = CONTENT_EXTRACTOR_PY.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check if this is a BeautifulSoup call
                func = node.func
                is_bs4_call = False
                if isinstance(func, ast.Name) and func.id == "BeautifulSoup":
                    is_bs4_call = True
                elif isinstance(func, ast.Attribute) and func.attr == "BeautifulSoup":
                    is_bs4_call = True

                if is_bs4_call and len(node.args) >= 2:
                    # Second arg is the parser
                    parser_arg = node.args[1]
                    if isinstance(parser_arg, ast.Constant) and isinstance(
                        parser_arg.value, str
                    ):
                        assert parser_arg.value == "html.parser", (
                            f"BeautifulSoup uses parser '{parser_arg.value}' — "
                            f"must use 'html.parser' for XXE prevention"
                        )

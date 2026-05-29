"""Regression tests for P1-20: XXE prevention in content extraction.

These tests verify that BeautifulSoup uses html.parser instead of lxml
to prevent XXE attacks.
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open

from bs4 import BeautifulSoup
from layer1_ingestion.post_processor.content_extractor import ContentExtractor


class TestXXEPrevention:
    """Test that XXE is prevented in HTML parsing."""

    def test_content_extractor_uses_html_parser(self):
        """ContentExtractor must use html.parser, not lxml."""
        # Read the source file to verify the fix
        import inspect
        import layer1_ingestion.post_processor.content_extractor as module

        source = inspect.getsource(module)

        # Should have html.parser
        assert 'html.parser' in source, "Must use html.parser for XXE prevention"

        # Should NOT have lxml as parser
        assert '"lxml"' not in source, "Must NOT use lxml parser (XXE risk)"
        assert "'lxml'" not in source, "Must NOT use lxml parser (XXE risk)"

    def test_beautifulsoup_html_parser_no_xxe(self):
        """BeautifulSoup with html.parser should not resolve external entities."""
        # XXE payload that tries to read /etc/passwd
        xxe_payload = """<?xml version="1.0" encoding="ISO-8859-1"?>
        <!DOCTYPE foo [
          <!ENTITY xxe SYSTEM "file:///etc/passwd">
        ]>
        <html><body>&xxe;</body></html>"""

        soup = BeautifulSoup(xxe_payload, "html.parser")

        # html.parser should not expand external entities
        # The entity reference should remain as text or be stripped
        body_text = soup.body.get_text() if soup.body else ""
        # Should not contain actual /etc/passwd content
        assert "root:" not in body_text, "XXE vulnerability detected"

    def test_extractor_handles_malicious_html(self):
        """ContentExtractor should safely handle potentially malicious HTML."""
        extractor = ContentExtractor()

        xxe_html = """<!DOCTYPE html [
          <!ENTITY xxe SYSTEM "file:///etc/passwd">
        ]>
        <html>
        <head><title>Test</title></head>
        <body><p>&xxe;</p></body>
        </html>"""

        # Should not raise or expose file contents
        result = extractor.extract(html=xxe_html, url="http://test.com")

        # Verify no sensitive data leaked
        assert result is not None
        if hasattr(result, 'text'):
            assert "root:" not in result.text, "XXE data leaked in result"

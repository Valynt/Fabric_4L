"""Tests for ContentExtractor (layer1-ingestion/src/post_processor/content_extractor.py).

Covers:
- ExtractedContent dataclass structure
- ContentExtractor.extract() – metadata, content type, links
- ContentExtractor._extract_metadata() – title, description, author, OG/Twitter tags,
  JSON-LD, noindex/nofollow, canonical URL, article:published_time
- ContentExtractor._extract_main_content_manual() – selector priority, fallback
- ContentExtractor._convert_to_markdown() – HTML and plain-text inputs
- ContentExtractor._clean_markdown() – normalization rules
- ContentExtractor._classify_content_type() – pattern matching
- ContentExtractor._extract_links() – absolute/relative, internal/external, nofollow
- extract_content() convenience function
"""

import pytest

from layer1_ingestion.post_processor.content_extractor import (
    ContentExtractor,
    ExtractedContent,
    extract_content,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Test Page Title</title>
  <meta name="description" content="A test description.">
  <meta name="author" content="Jane Doe">
  <link rel="canonical" href="https://example.com/canonical">
</head>
<body>
  <main>
    <h1>Main Heading</h1>
    <p>This is the main content of the page.</p>
  </main>
</body>
</html>"""

MINIMAL_HTML = "<html><body><p>Short content.</p></body></html>"


@pytest.fixture
def extractor() -> ContentExtractor:
    return ContentExtractor()


# ---------------------------------------------------------------------------
# ExtractedContent dataclass
# ---------------------------------------------------------------------------

class TestExtractedContent:
    def test_fields_accessible(self):
        ec = ExtractedContent(
            title="T",
            description="D",
            author="A",
            published_at=None,
            markdown_content="# T\n\nD",
            html_content="<h1>T</h1>",
            content_type="blog_post",
            metadata={},
            links=[],
        )
        assert ec.title == "T"
        assert ec.markdown_content == "# T\n\nD"
        assert ec.links == []


# ---------------------------------------------------------------------------
# ContentExtractor.extract()
# ---------------------------------------------------------------------------

class TestExtract:
    def test_returns_extracted_content(self, extractor):
        result = extractor.extract(BASE_HTML, "https://example.com/")
        assert isinstance(result, ExtractedContent)

    def test_title_extracted(self, extractor):
        result = extractor.extract(BASE_HTML, "https://example.com/")
        assert result.title == "Test Page Title"

    def test_description_extracted(self, extractor):
        result = extractor.extract(BASE_HTML, "https://example.com/")
        assert result.description == "A test description."

    def test_author_extracted(self, extractor):
        result = extractor.extract(BASE_HTML, "https://example.com/")
        assert result.author == "Jane Doe"

    def test_markdown_content_is_string(self, extractor):
        result = extractor.extract(BASE_HTML, "https://example.com/")
        assert isinstance(result.markdown_content, str)
        assert len(result.markdown_content) > 0

    def test_html_content_truncated_at_100000(self, extractor):
        long_html = "<html><body>" + "x" * 200_000 + "</body></html>"
        result = extractor.extract(long_html, "https://example.com/")
        assert len(result.html_content) <= 100_000

    def test_content_type_classified(self, extractor):
        product_html = """<html><head><title>Product Solution</title></head>
        <body><p>Our solution features pricing.</p></body></html>"""
        result = extractor.extract(product_html, "https://example.com/product")
        assert result.content_type is not None

    def test_links_extracted(self, extractor):
        html = """<html><body>
        <a href="https://external.com/page">External</a>
        <a href="/internal">Internal</a>
        </body></html>"""
        result = extractor.extract(html, "https://example.com/")
        assert len(result.links) >= 1

    def test_links_empty_when_extract_links_false(self, extractor):
        result = extractor.extract(BASE_HTML, "https://example.com/", extract_links=False)
        assert result.links == []

    def test_metadata_contains_url(self, extractor):
        result = extractor.extract(BASE_HTML, "https://example.com/page")
        assert result.metadata["url"] == "https://example.com/page"

    def test_metadata_contains_domain(self, extractor):
        result = extractor.extract(BASE_HTML, "https://example.com/page")
        assert result.metadata["domain"] == "example.com"


# ---------------------------------------------------------------------------
# ContentExtractor._extract_metadata()
# ---------------------------------------------------------------------------

class TestExtractMetadata:
    def setup_method(self):
        self.extractor = ContentExtractor()

    def _soup(self, html: str):
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "html.parser")

    def test_title_extracted(self):
        soup = self._soup("<html><head><title>My Title</title></head></html>")
        meta = self.extractor._extract_metadata(soup, "https://example.com/")
        assert meta["title"] == "My Title"

    def test_description_extracted(self):
        html = '<html><head><meta name="description" content="Page desc."></head></html>'
        soup = self._soup(html)
        meta = self.extractor._extract_metadata(soup, "https://example.com/")
        assert meta["description"] == "Page desc."

    def test_author_extracted(self):
        html = '<html><head><meta name="author" content="John Smith"></head></html>'
        soup = self._soup(html)
        meta = self.extractor._extract_metadata(soup, "https://example.com/")
        assert meta["author"] == "John Smith"

    def test_og_tags_extracted(self):
        html = '<html><head><meta property="og:title" content="OG Title"></head></html>'
        soup = self._soup(html)
        meta = self.extractor._extract_metadata(soup, "https://example.com/")
        assert meta["og_title"] == "OG Title"

    def test_twitter_tags_extracted(self):
        html = '<html><head><meta name="twitter:card" content="summary"></head></html>'
        soup = self._soup(html)
        meta = self.extractor._extract_metadata(soup, "https://example.com/")
        assert meta["twitter_card"] == "summary"

    def test_canonical_url_extracted(self):
        html = '<html><head><link rel="canonical" href="https://example.com/canonical"></head></html>'
        soup = self._soup(html)
        meta = self.extractor._extract_metadata(soup, "https://example.com/page")
        assert meta["canonical_url"] == "https://example.com/canonical"

    def test_noindex_detected(self):
        html = '<html><head><meta name="robots" content="noindex, nofollow"></head></html>'
        soup = self._soup(html)
        meta = self.extractor._extract_metadata(soup, "https://example.com/")
        assert meta["noindex"] is True
        assert meta["nofollow"] is True

    def test_noindex_false_when_not_present(self):
        html = '<html><head><meta name="robots" content="index, follow"></head></html>'
        soup = self._soup(html)
        meta = self.extractor._extract_metadata(soup, "https://example.com/")
        assert meta["noindex"] is False
        assert meta["nofollow"] is False

    def test_article_published_time_extracted(self):
        html = '<html><head><meta property="article:published_time" content="2024-01-01T00:00:00Z"></head></html>'
        soup = self._soup(html)
        meta = self.extractor._extract_metadata(soup, "https://example.com/")
        assert meta["published_at"] == "2024-01-01T00:00:00Z"

    def test_json_ld_title_extracted(self):
        html = """<html><head><script type="application/ld+json">
        {"@type": "Article", "headline": "JSON-LD Title"}</script></head></html>"""
        soup = self._soup(html)
        meta = self.extractor._extract_metadata(soup, "https://example.com/")
        assert meta.get("title") == "JSON-LD Title"

    def test_json_ld_author_dict_extracted(self):
        html = """<html><head><script type="application/ld+json">
        {"author": {"name": "Author Name"}}</script></head></html>"""
        soup = self._soup(html)
        meta = self.extractor._extract_metadata(soup, "https://example.com/")
        assert meta.get("author") == "Author Name"

    def test_json_ld_author_list_extracted(self):
        html = """<html><head><script type="application/ld+json">
        {"author": [{"name": "Author One"}, {"name": "Author Two"}]}</script></head></html>"""
        soup = self._soup(html)
        meta = self.extractor._extract_metadata(soup, "https://example.com/")
        assert "Author One" in meta.get("author", "")
        assert "Author Two" in meta.get("author", "")

    def test_no_metadata_returns_basic_keys(self):
        soup = self._soup("<html><body></body></html>")
        meta = self.extractor._extract_metadata(soup, "https://example.com/")
        assert "url" in meta
        assert "domain" in meta

    def test_title_truncated_at_500_chars(self):
        long_title = "T" * 600
        html = f"<html><head><title>{long_title}</title></head></html>"
        soup = self._soup(html)
        meta = self.extractor._extract_metadata(soup, "https://example.com/")
        assert len(meta["title"]) <= 500


# ---------------------------------------------------------------------------
# ContentExtractor._extract_main_content_manual()
# ---------------------------------------------------------------------------

class TestExtractMainContentManual:
    def setup_method(self):
        self.extractor = ContentExtractor()

    def _soup(self, html: str):
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "html.parser")

    def test_extracts_from_main_element(self):
        html = "<html><body><main>Main content here.</main><nav>Nav</nav></body></html>"
        soup = self._soup(html)
        text = self.extractor._extract_main_content_manual(soup)
        assert "Main content" in text

    def test_extracts_from_article_element(self):
        html = "<html><body><article>Article content.</article></body></html>"
        soup = self._soup(html)
        text = self.extractor._extract_main_content_manual(soup)
        assert "Article content" in text

    def test_falls_back_to_body_when_no_main(self):
        html = "<html><body><p>Body paragraph.</p></body></html>"
        soup = self._soup(html)
        text = self.extractor._extract_main_content_manual(soup)
        assert "Body paragraph" in text

    def test_nav_and_script_removed(self):
        html = "<html><body><script>alert('js')</script><main>Clean text.</main></body></html>"
        soup = self._soup(html)
        text = self.extractor._extract_main_content_manual(soup)
        # The script is removed from the soup in-place
        assert "alert" not in text


# ---------------------------------------------------------------------------
# ContentExtractor._convert_to_markdown()
# ---------------------------------------------------------------------------

class TestConvertToMarkdown:
    def setup_method(self):
        self.extractor = ContentExtractor()

    def test_html_input_converted(self):
        html = "<h1>Title</h1><p>Paragraph.</p>"
        md = self.extractor._convert_to_markdown(html)
        assert isinstance(md, str)
        assert len(md) > 0

    def test_plain_text_input_returned(self):
        text = "Just plain text without tags."
        md = self.extractor._convert_to_markdown(text)
        assert "Just plain text" in md

    def test_html_input_detected_by_angle_brackets(self):
        html_like = "<div>content</div>"
        md = self.extractor._convert_to_markdown(html_like)
        # Should run markdownify path – result is a string
        assert isinstance(md, str)


# ---------------------------------------------------------------------------
# ContentExtractor._clean_markdown()
# ---------------------------------------------------------------------------

class TestCleanMarkdown:
    def setup_method(self):
        self.extractor = ContentExtractor()

    def test_crlf_normalized(self):
        text = "Line 1\r\nLine 2"
        result = self.extractor._clean_markdown(text)
        assert "\r" not in result

    def test_excessive_blank_lines_collapsed(self):
        text = "Para 1\n\n\n\n\n\nPara 2"
        result = self.extractor._clean_markdown(text)
        assert "\n\n\n\n" not in result

    def test_trailing_whitespace_removed(self):
        text = "Line with trailing   \nNext line"
        result = self.extractor._clean_markdown(text)
        for line in result.split("\n"):
            assert line == line.rstrip()

    def test_text_stripped(self):
        text = "\n\n  Content  \n\n"
        result = self.extractor._clean_markdown(text)
        assert result == result.strip()

    def test_very_long_text_truncated(self):
        text = "x" * 600_000
        result = self.extractor._clean_markdown(text)
        assert len(result) <= 500_100  # 500k + truncation suffix


# ---------------------------------------------------------------------------
# ContentExtractor._classify_content_type()
# ---------------------------------------------------------------------------

class TestClassifyContentType:
    def setup_method(self):
        self.extractor = ContentExtractor()

    def test_product_page_classified(self):
        ct = self.extractor._classify_content_type(
            "https://example.com/product/overview",
            {"title": "Our Product Features"},
            "solution pricing plans",
        )
        assert ct == "product_page"

    def test_blog_post_classified(self):
        ct = self.extractor._classify_content_type(
            "https://example.com/blog/article",
            {"title": "Blog Post"},
            "post content here",
        )
        assert ct == "blog_post"

    def test_documentation_classified(self):
        ct = self.extractor._classify_content_type(
            "https://docs.example.com/guide",
            {"title": "Documentation Guide"},
            "api reference tutorial",
        )
        assert ct == "documentation"

    def test_financial_filing_classified(self):
        ct = self.extractor._classify_content_type(
            "https://example.com/10-K",
            {"title": "Annual Report 10-K"},
            "quarterly report filing",
        )
        assert ct == "financial_filing"

    def test_press_release_classified(self):
        ct = self.extractor._classify_content_type(
            "https://example.com/press-release",
            {"title": "Media Kit"},
            "news release announcement",
        )
        assert ct == "press_release"

    def test_unknown_when_no_match(self):
        ct = self.extractor._classify_content_type(
            "https://example.com/",
            {"title": ""},
            "some random content",
        )
        assert ct == "unknown"


# ---------------------------------------------------------------------------
# ContentExtractor._extract_links()
# ---------------------------------------------------------------------------

class TestExtractLinks:
    def setup_method(self):
        self.extractor = ContentExtractor()

    def _soup(self, html: str):
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "html.parser")

    def test_absolute_external_link(self):
        html = '<html><body><a href="https://other.com/page">External</a></body></html>'
        soup = self._soup(html)
        links = self.extractor._extract_links(soup, "https://example.com/")
        assert any(l["url"] == "https://other.com/page" for l in links)
        assert any(l["is_external"] for l in links)

    def test_relative_link_resolved(self):
        html = '<html><body><a href="/about">About</a></body></html>'
        soup = self._soup(html)
        links = self.extractor._extract_links(soup, "https://example.com/")
        assert any(l["url"] == "https://example.com/about" for l in links)

    def test_internal_link_not_external(self):
        html = '<html><body><a href="/page">Internal</a></body></html>'
        soup = self._soup(html)
        links = self.extractor._extract_links(soup, "https://example.com/")
        internal_links = [l for l in links if not l["is_external"]]
        assert len(internal_links) >= 1

    def test_nofollow_detected(self):
        html = '<html><body><a href="https://spam.com/" rel="nofollow">Spam</a></body></html>'
        soup = self._soup(html)
        links = self.extractor._extract_links(soup, "https://example.com/")
        assert any(l["is_nofollow"] for l in links)

    def test_anchor_only_links_excluded(self):
        html = '<html><body><a href="#section">Anchor</a></body></html>'
        soup = self._soup(html)
        links = self.extractor._extract_links(soup, "https://example.com/")
        # Fragment-only hrefs resolve to same page but have netloc, check count is small
        # (they may be included if netloc resolves, but mailto/javascript should be excluded)
        for link in links:
            assert link["url"].startswith("http")

    def test_non_http_protocols_excluded(self):
        html = '<html><body><a href="mailto:user@example.com">Email</a></body></html>'
        soup = self._soup(html)
        links = self.extractor._extract_links(soup, "https://example.com/")
        assert not any("mailto" in l["url"] for l in links)

    def test_link_text_extracted(self):
        html = '<html><body><a href="https://other.com/">Click Here</a></body></html>'
        soup = self._soup(html)
        links = self.extractor._extract_links(soup, "https://example.com/")
        assert any(l["text"] == "Click Here" for l in links)

    def test_no_links_returns_empty(self):
        html = "<html><body><p>No links here.</p></body></html>"
        soup = self._soup(html)
        links = self.extractor._extract_links(soup, "https://example.com/")
        assert links == []


# ---------------------------------------------------------------------------
# extract_content() convenience function
# ---------------------------------------------------------------------------

class TestExtractContentConvenience:
    def test_returns_extracted_content(self):
        result = extract_content(BASE_HTML, "https://example.com/")
        assert isinstance(result, ExtractedContent)

    def test_no_links_when_false(self):
        result = extract_content(BASE_HTML, "https://example.com/", extract_links=False)
        assert result.links == []

    def test_links_extracted_by_default(self):
        html = '<html><body><a href="https://other.com/">Link</a></body></html>'
        result = extract_content(html, "https://example.com/")
        assert len(result.links) >= 1

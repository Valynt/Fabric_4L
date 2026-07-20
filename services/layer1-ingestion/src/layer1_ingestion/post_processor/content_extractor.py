"""Content extraction and HTML-to-Markdown conversion.

Provides utilities for extracting clean content from HTML and converting
to Markdown format suitable for downstream processing.
"""

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import markdownify
import structlog
import trafilatura
from bs4 import BeautifulSoup

logger = structlog.get_logger()


@dataclass
class ExtractedContent:
    """Result of content extraction."""

    title: str | None
    description: str | None
    author: str | None
    published_at: str | None
    markdown_content: str
    html_content: str
    content_type: str | None
    metadata: dict[str, Any]
    links: list[dict[str, Any]]


class ContentExtractor:
    """Extract and clean content from HTML."""

    def __init__(self):
        self.content_type_patterns = {
            "product_page": [
                r"product",
                r"solution",
                r"feature",
                r"pricing",
            ],
            "press_release": [
                r"press.?release",
                r"news.?release",
                r"media.?kit",
            ],
            "blog_post": [
                r"blog",
                r"article",
                r"post",
            ],
            "documentation": [
                r"docs?",
                r"documentation",
                r"api.?reference",
                r"guide",
                r"tutorial",
            ],
            "financial_filing": [
                r"10-[KQ]",
                r"8-K",
                r"annual.?report",
                r"quarterly.?report",
            ],
        }

    def extract(self, html: str, url: str, extract_links: bool = True) -> ExtractedContent:
        """Extract clean content from HTML.

        Args:
            html: Raw HTML content
            url: Source URL
            extract_links: Whether to extract links from the page

        Returns:
            ExtractedContent with cleaned data
        """
        # P1-20 FIX: Use html.parser instead of lxml to prevent XXE
        soup = BeautifulSoup(html, "html.parser")

        # Extract metadata
        metadata = self._extract_metadata(soup, url)

        # Extract main content using trafilatura
        trafilatura_result = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            include_images=False,
            include_links=extract_links,
            output_format="xml",
            with_metadata=True,
        )

        if trafilatura_result:
            # Parse trafilatura XML output
            try:
                # P1-20 FIX: Use html.parser instead of lxml to prevent XXE
                traf_soup = BeautifulSoup(trafilatura_result, "html.parser")
                main_text = traf_soup.get_text(separator="\n", strip=True)
            except Exception:
                main_text = None
        else:
            main_text = None

        # Fallback to manual extraction if trafilatura fails
        if not main_text:
            main_text = self._extract_main_content_manual(soup)

        # Convert to Markdown
        markdown_content = self._convert_to_markdown(main_text or html, soup)

        # Classify content type
        content_type = self._classify_content_type(url, metadata, markdown_content)

        # Extract links if requested
        links = []
        if extract_links:
            links = self._extract_links(soup, url)

        return ExtractedContent(
            title=metadata.get("title"),
            description=metadata.get("description"),
            author=metadata.get("author"),
            published_at=metadata.get("published_at"),
            markdown_content=markdown_content,
            html_content=html[:100000],  # Limit stored HTML size
            content_type=content_type,
            metadata=metadata,
            links=links,
        )

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> dict[str, Any]:
        """Extract metadata from HTML head and structured data."""
        return self._build_metadata(soup, url)

    def _build_metadata(self, soup: BeautifulSoup, url: str) -> dict[str, Any]:
        """Build metadata from HTML head and structured data."""
        metadata = {
            "url": url,
            "domain": urlparse(url).netloc,
        }

        # Standard meta tags
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text(strip=True)[:500]

        description = soup.find("meta", attrs={"name": "description"})
        if description:
            metadata["description"] = description.get("content", "")[:1000]

        author = soup.find("meta", attrs={"name": "author"})
        if author:
            metadata["author"] = author.get("content", "")[:255]

        # Open Graph tags
        og_tags = soup.find_all("meta", property=re.compile(r"^og:"))
        for tag in og_tags:
            prop = tag.get("property", "").replace("og:", "")
            metadata[f"og_{prop}"] = tag.get("content", "")

        # Twitter Card tags
        twitter_tags = soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")})
        for tag in twitter_tags:
            name = tag.get("name", "").replace("twitter:", "")
            metadata[f"twitter_{name}"] = tag.get("content", "")

        # Article published time
        article_published = soup.find("meta", property="article:published_time") or soup.find(
            "meta", property="og:article:published_time"
        )
        if article_published:
            metadata["published_at"] = article_published.get("content", "")

        # Canonical URL
        canonical = soup.find("link", rel="canonical")
        if canonical:
            metadata["canonical_url"] = canonical.get("href", "")

        # JSON-LD structured data
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        metadata["structured_data"] = []
        for script in json_ld_scripts:
            try:
                import json

                data = json.loads(script.string)
                metadata["structured_data"].append(data)

                # Extract common fields from structured data
                if isinstance(data, dict):
                    if "headline" in data and not metadata.get("title"):
                        metadata["title"] = data["headline"]
                    if "description" in data and not metadata.get("description"):
                        metadata["description"] = data["description"]
                    if "author" in data:
                        if isinstance(data["author"], dict):
                            metadata["author"] = data["author"].get("name", "")
                        elif isinstance(data["author"], list):
                            metadata["author"] = ", ".join(
                                a.get("name", "") for a in data["author"] if isinstance(a, dict)
                            )
                    if "datePublished" in data and not metadata.get("published_at"):
                        metadata["published_at"] = data["datePublished"]
            except Exception:
                pass

        # Check for noindex
        robots_meta = soup.find("meta", attrs={"name": "robots"})
        if robots_meta:
            content = robots_meta.get("content", "").lower()
            metadata["noindex"] = "noindex" in content
            metadata["nofollow"] = "nofollow" in content

        return metadata

    def _extract_main_content_manual(self, soup: BeautifulSoup) -> str:
        """Fallback method to extract main content."""
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()

        # Try to find main content area
        main_content = None

        # Look for common content containers
        selectors = [
            "main",
            "article",
            '[role="main"]',
            ".content",
            ".main-content",
            "#content",
            "#main-content",
            ".post-content",
            ".entry-content",
            ".article-content",
        ]

        for selector in selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break

        # Fallback to body if no specific container found
        if not main_content:
            main_content = soup.body

        if main_content:
            return main_content.get_text(separator="\n", strip=True)

        return soup.get_text(separator="\n", strip=True)

    def _convert_to_markdown(self, text_or_html: str, soup: BeautifulSoup | None = None) -> str:
        """Convert HTML or text to clean Markdown."""
        # If input looks like HTML, convert it
        if "<" in text_or_html and ">" in text_or_html:
            try:
                # Use markdownify for HTML-to-Markdown
                md = markdownify.markdownify(
                    text_or_html,
                    heading_style="ATX",
                    bullets="-",
                    strip=["a", "img", "script", "style"],
                )

                # Clean up the markdown
                md = self._clean_markdown(md)
                return md
            except Exception:
                logger.warning("Markdown conversion failed", error_code="MARKDOWN_CONVERSION_ERROR")
                # Return text content as fallback
                if soup:
                    return soup.get_text(separator="\n", strip=True)
                return text_or_html

        # Input is already text
        return self._clean_markdown(text_or_html)

    def _clean_markdown(self, text: str) -> str:
        """Clean up Markdown formatting."""
        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove excessive blank lines
        text = re.sub(r"\n{4,}", "\n\n\n", text)

        # Fix common markdown issues
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

        # Remove trailing whitespace
        text = "\n".join(line.rstrip() for line in text.split("\n"))

        # Ensure code blocks are properly formatted
        text = re.sub(r"```\s*\n", "\n```\n", text)

        # Truncate if extremely long
        max_length = 500000  # 500KB
        if len(text) > max_length:
            text = text[:max_length] + "\n\n[Content truncated due to length]"

        return text.strip()

    def _classify_content_type(
        self, url: str, metadata: dict[str, Any], content: str
    ) -> str | None:
        """Classify the type of content."""
        url_lower = url.lower()
        combined_text = f"{url_lower} {metadata.get('title', '').lower()} {content[:1000].lower()}"

        scores = {}
        for content_type, patterns in self.content_type_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    score += 1
            if score > 0:
                scores[content_type] = score

        if scores:
            return max(scores, key=scores.get)

        return "unknown"

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> list[dict[str, Any]]:
        """Extract all links from the page."""
        from urllib.parse import urljoin, urlparse

        base_domain = urlparse(base_url).netloc
        links = []

        for a_tag in soup.find_all("a", href=True):
            href = str(a_tag["href"])
            absolute_url = urljoin(base_url, href)
            parsed = urlparse(absolute_url)

            # Skip non-HTTP protocols and fragments
            if parsed.scheme not in ("http", "https"):
                continue
            if not parsed.netloc:
                continue

            is_external = parsed.netloc != base_domain

            links.append(
                {
                    "url": absolute_url,
                    "text": a_tag.get_text(strip=True)[:200],
                    "title": a_tag.get("title", "")[:200],
                    "is_external": is_external,
                    "is_nofollow": "nofollow" in list(a_tag.get("rel") or []),
                }
            )

        return links


def extract_content(html: str, url: str, extract_links: bool = True) -> ExtractedContent:
    """Convenience function for content extraction."""
    extractor = ContentExtractor()
    return extractor.extract(html, url, extract_links)

from __future__ import annotations

import re
from html.parser import HTMLParser as StdlibHTMLParser
from typing import Any

from src.connectors.html.exceptions import HtmlParseError
from src.connectors.models import Document


_CONTENT_TAGS: frozenset[str] = frozenset(
    {
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "blockquote",
        "pre",
        "code",
        "td",
        "th",
        "dd",
        "dt",
        "figcaption",
        "q",
    }
)

_SECTION_TAGS: frozenset[str] = frozenset(
    {
        "article",
        "main",
        "section",
        "div",
    }
)

_EXCLUDED_TAGS: frozenset[str] = frozenset(
    {
        "script",
        "style",
        "nav",
        "header",
        "footer",
        "aside",
        "noscript",
        "iframe",
        "form",
        "input",
        "select",
        "textarea",
        "button",
        "canvas",
        "svg",
        "video",
        "audio",
        "img",
        "picture",
    }
)

_HEADING_TAGS: frozenset[str] = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})


class HtmlContentExtractor(StdlibHTMLParser):
    """SAX-style HTML parser that extracts clean text content."""

    def __init__(self) -> None:
        self._tag_stack: list[str] = []
        self._excluded_depth: int = 0
        self._text_parts: list[str] = []
        self._last_tag: str = ""
        self._started_content: bool = True
        super().__init__(convert_charrefs=True)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._tag_stack.append(tag)
        tag_lower = tag.lower()

        if tag_lower in _EXCLUDED_TAGS:
            self._excluded_depth += 1

        is_content = tag_lower in _CONTENT_TAGS or tag_lower in _SECTION_TAGS
        if is_content and self._excluded_depth == 0:
            if (
                self._text_parts
                and self._text_parts[-1]
                and not self._text_parts[-1].endswith("\n")
            ):
                self._text_parts.append("\n")

        self._last_tag = tag_lower

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in _EXCLUDED_TAGS and self._excluded_depth > 0:
            self._excluded_depth -= 1

        if self._tag_stack:
            self._tag_stack.pop()

        if tag_lower in _SECTION_TAGS and self._excluded_depth == 0:
            if self._text_parts and not self._text_parts[-1].endswith("\n"):
                self._text_parts.append("\n")

        if tag_lower in (
            "p",
            "li",
            "blockquote",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "dd",
            "dt",
            "figcaption",
        ):
            if self._excluded_depth == 0:
                self._text_parts.append("\n")

        self._last_tag = ""

    def handle_data(self, data: str) -> None:
        if self._excluded_depth > 0:
            return
        text = self._normalize_whitespace(data)
        if text:
            self._text_parts.append(text)

    def handle_entityref(self, name: str) -> None:
        if self._excluded_depth == 0:
            self._text_parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self._excluded_depth == 0:
            self._text_parts.append(f"&#{name};")

    def get_text(self) -> str:
        result = "".join(self._text_parts)
        result = re.sub(r"\n{3,}", "\n\n", result)
        result = result.strip()
        return result

    def reset(self) -> None:
        super().reset()
        self._tag_stack.clear()
        self._excluded_depth = 0
        self._text_parts.clear()
        self._last_tag = ""
        self._started_content = True

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        return re.sub(r"\s+", " ", text)


class HtmlMetadataExtractor:
    """Extracts metadata from HTML without parsing full content."""

    @staticmethod
    def extract_title(html: str) -> str | None:
        match = re.search(
            r"<title[^>]*>(.*?)</title>",
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            title = match.group(1).strip()
            title = re.sub(r"\s+", " ", title)
            return title if title else None
        return None

    @staticmethod
    def extract_canonical_url(html: str) -> str | None:
        match = re.search(
            r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
        match = re.search(
            r'<link[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']canonical["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def extract_meta_content(html: str, meta_name: str) -> str | None:
        pattern = re.compile(
            rf'<meta[^>]*name=["\']{re.escape(meta_name)}["\'][^>]*content=["\']([^"\']*)["\']',
            re.IGNORECASE,
        )
        match = pattern.search(html)
        if match:
            return match.group(1).strip() or None
        pattern = re.compile(
            rf'<meta[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']{re.escape(meta_name)}["\']',
            re.IGNORECASE,
        )
        match = pattern.search(html)
        return match.group(1).strip() if match else None

    @staticmethod
    def extract_meta_property(html: str, property_name: str) -> str | None:
        pattern = re.compile(
            rf'<meta[^>]*property=["\']{re.escape(property_name)}["\'][^>]*content=["\']([^"\']*)["\']',
            re.IGNORECASE,
        )
        match = pattern.search(html)
        if match:
            return match.group(1).strip() or None
        pattern = re.compile(
            rf'<meta[^>]*content=["\']([^"\']*)["\'][^>]*property=["\']{re.escape(property_name)}["\']',
            re.IGNORECASE,
        )
        match = pattern.search(html)
        return match.group(1).strip() if match else None

    @staticmethod
    def extract_language(html: str) -> str | None:
        match = re.search(r'<html[^>]*\slang=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if match:
            return match.group(1).split("-")[0].lower()
        return None

    @staticmethod
    def extract_description(html: str) -> str | None:
        return HtmlMetadataExtractor.extract_meta_content(html, "description")

    @staticmethod
    def extract_keywords(html: str) -> str | None:
        return HtmlMetadataExtractor.extract_meta_content(html, "keywords")

    @staticmethod
    def extract_publication_date(html: str) -> str | None:
        result = HtmlMetadataExtractor.extract_meta_content(html, "date")
        if result:
            return result
        result = HtmlMetadataExtractor.extract_meta_property(html, "article:published_time")
        if result:
            return result
        result = HtmlMetadataExtractor.extract_meta_property(html, "article:modified_time")
        return result

    @staticmethod
    def extract_links(html: str, base_url: str) -> list[str]:
        links: list[str] = []
        for match in re.finditer(
            r'<a[^>]*href=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        ):
            href = match.group(1).strip()
            if href and not href.startswith("#") and not href.startswith("javascript:"):
                links.append(href)
        return links

    @staticmethod
    def extract_all(html: str, source_url: str) -> dict[str, Any]:
        return {
            "title": HtmlMetadataExtractor.extract_title(html),
            "canonical_url": HtmlMetadataExtractor.extract_canonical_url(html),
            "language": HtmlMetadataExtractor.extract_language(html),
            "description": HtmlMetadataExtractor.extract_description(html),
            "keywords": HtmlMetadataExtractor.extract_keywords(html),
            "publication_date_str": HtmlMetadataExtractor.extract_publication_date(html),
            "discovered_links": HtmlMetadataExtractor.extract_links(html, source_url),
        }


class HtmlParser:
    """Orchestrates HTML parsing: metadata extraction + content extraction."""

    def __init__(self) -> None:
        self._extractor = HtmlContentExtractor()

    def parse(self, html: str, source_url: str, content_type: str = "") -> Document:
        if not html or not html.strip():
            raise HtmlParseError("Empty HTML content")

        try:
            metadata = HtmlMetadataExtractor.extract_all(html, source_url)

            self._extractor.reset()
            try:
                self._extractor.feed(html)
            except Exception as e:
                raise HtmlParseError(f"Failed to parse HTML: {e}") from e

            content = self._extractor.get_text()

            extra_meta: dict[str, Any] = {}
            if metadata.get("description"):
                extra_meta["description"] = metadata["description"]
            if metadata.get("keywords"):
                extra_meta["keywords"] = metadata["keywords"]
            if metadata.get("publication_date_str"):
                extra_meta["publication_date_str"] = metadata["publication_date_str"]

            return Document(
                authority_id="",
                source_url=source_url,
                canonical_url=metadata.get("canonical_url"),
                title=metadata.get("title"),
                summary=metadata.get("description"),
                content=content,
                content_type=content_type or "text/html",
                language=metadata.get("language"),
                document_type="web_page",
                metadata=extra_meta,
                discovered_links=metadata.get("discovered_links", []),
            )
        except HtmlParseError:
            raise
        except Exception as e:
            raise HtmlParseError(f"Unexpected error during HTML parsing: {e}") from e

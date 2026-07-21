from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from enum import StrEnum
from typing import Any
from xml.etree.ElementTree import ParseError, fromstring

from pydantic import BaseModel

from src.connectors.models import Document
from src.connectors.rss.exceptions import (
    FeedTooLargeError,
    InvalidXmlError,
    RssParseError,
    UnsupportedFeedFormatError,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ATOM_NS = "http://www.w3.org/2005/Atom"
CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"

DEFAULT_MAX_FEED_SIZE = 10 * 1024 * 1024
DEFAULT_MAX_ENTRIES = 500
DEFAULT_MAX_CONTENT_LENGTH = 100 * 1024

_SUPPORTED_FEED_TYPES: frozenset[str] = frozenset(
    {
        "application/rss+xml",
        "application/atom+xml",
        "application/xml",
        "text/xml",
    }
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class RssConfig(BaseModel, frozen=True):
    max_feed_size: int = DEFAULT_MAX_FEED_SIZE
    max_entries: int = DEFAULT_MAX_ENTRIES
    max_content_length: int = DEFAULT_MAX_CONTENT_LENGTH


# ---------------------------------------------------------------------------
# Feed type detection
# ---------------------------------------------------------------------------


class FeedType(StrEnum):
    RSS = "rss"
    ATOM = "atom"


# ---------------------------------------------------------------------------
# Safe XML parsing
# ---------------------------------------------------------------------------


_DOCTYPE_PATTERN = re.compile(r"<!DOCTYPE[^>]*>", re.IGNORECASE | re.DOTALL)


def _parse_xml_safe(xml_content: str | bytes) -> Any:
    """Parse XML with XXE protection.

    Strips DOCTYPE declarations (which contain entity definitions) to
    prevent entity expansion attacks (billion laughs) and external entity
    resolution.  Python's standard-library ElementTree never resolves
    external entities, but internal entity definitions inside DOCTYPE can
    still cause denial-of-service via exponential expansion.
    """
    try:
        if isinstance(xml_content, bytes):
            xml_content = xml_content.decode("utf-8", errors="replace")
        clean = _DOCTYPE_PATTERN.sub("", xml_content)
        return fromstring(clean)
    except ParseError as e:
        raise InvalidXmlError(f"Malformed XML in feed: {e}") from e
    except Exception as e:
        raise InvalidXmlError(f"XML parsing failed: {e}") from e


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------


def _parse_rss_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str.strip())
    except (ValueError, TypeError, OverflowError):
        return None


def _parse_atom_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        cleaned = date_str.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Content sanitization
# ---------------------------------------------------------------------------

_SCRIPT_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_STYLE_PATTERN = re.compile(r"<style[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
_NOSCRIPT_PATTERN = re.compile(r"<noscript[^>]*>.*?</noscript>", re.IGNORECASE | re.DOTALL)
_IFRAME_PATTERN = re.compile(r"<iframe[^>]*>.*?</iframe>", re.IGNORECASE | re.DOTALL)
_OBJECT_PATTERN = re.compile(r"<object[^>]*>.*?</object>", re.IGNORECASE | re.DOTALL)
_EMBED_PATTERN = re.compile(r"<embed[^>]*>.*?</embed>", re.IGNORECASE | re.DOTALL)


def _sanitize_html(html: str | None, max_length: int = DEFAULT_MAX_CONTENT_LENGTH) -> str:
    if not html:
        return ""
    if len(html) > max_length:
        html = html[:max_length]
    html = _SCRIPT_PATTERN.sub("", html)
    html = _STYLE_PATTERN.sub("", html)
    html = _NOSCRIPT_PATTERN.sub("", html)
    html = _IFRAME_PATTERN.sub("", html)
    html = _OBJECT_PATTERN.sub("", html)
    html = _EMBED_PATTERN.sub("", html)
    return html.strip()


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def _get_text(element: Any, tag: str) -> str | None:
    child = element.find(tag)
    if child is not None and child.text:
        text = child.text.strip()
        return text if text else None
    return None


def _get_text_ns(element: Any, namespace: str, local_tag: str) -> str | None:
    child = element.find(f"{{{namespace}}}{local_tag}")
    if child is not None and child.text:
        text = child.text.strip()
        return text if text else None
    return None


# ---------------------------------------------------------------------------
# RSS 2.0 parsing
# ---------------------------------------------------------------------------


def _parse_rss_channel_metadata(channel: Any) -> dict[str, Any]:
    return {
        "title": _get_text(channel, "title"),
        "description": _get_text(channel, "description"),
        "link": _get_text(channel, "link"),
        "language": _get_text(channel, "language"),
        "copyright": _get_text(channel, "copyright"),
        "managingEditor": _get_text(channel, "managingEditor"),
        "pubDate": _get_text(channel, "pubDate"),
        "lastBuildDate": _get_text(channel, "lastBuildDate"),
        "generator": _get_text(channel, "generator"),
        "categories": [
            cat.text.strip() for cat in channel.findall("category") if cat.text and cat.text.strip()
        ],
    }


def _parse_rss_item(
    item: Any, source_url: str, authority_id: str, max_content_length: int
) -> Document:
    title = _get_text(item, "title")
    link = _get_text(item, "link")
    description = _get_text(item, "description")
    content_encoded = _get_text_ns(item, CONTENT_NS, "encoded")
    pub_date = _parse_rss_date(_get_text(item, "pubDate"))
    guid = _get_text(item, "guid")
    author = _get_text(item, "author") or _get_text(item, "managingEditor")
    categories = [
        cat.text.strip() for cat in item.findall("category") if cat.text and cat.text.strip()
    ]

    content = content_encoded or description or ""
    sanitized = _sanitize_html(content, max_content_length)

    meta: dict[str, Any] = {}
    if guid:
        meta["guid"] = guid
    if author:
        meta["author"] = author
    if categories:
        meta["categories"] = categories

    return Document(
        authority_id=authority_id,
        source_url=link or source_url,
        canonical_url=link,
        title=title,
        summary=description[:500] if description else None,
        content=sanitized,
        content_type="text/html",
        publication_date=pub_date,
        document_type="regulatory_update",
        metadata=meta,
    )


def _parse_rss_feed(
    root: Any,
    source_url: str,
    authority_id: str,
    max_entries: int,
    max_content_length: int,
) -> list[Document]:
    channel = root.find("channel")
    if channel is None:
        raise RssParseError("RSS feed missing <channel> element")

    feed_meta = _parse_rss_channel_metadata(channel)
    log.debug(
        "RSS feed: title=%s, entries=%d, language=%s",
        feed_meta.get("title"),
        len(channel.findall("item")),
        feed_meta.get("language"),
    )

    documents: list[Document] = []
    for idx, item in enumerate(channel.findall("item")):
        if idx >= max_entries:
            break
        doc = _parse_rss_item(item, source_url, authority_id, max_content_length)
        documents.append(doc)

    return documents


# ---------------------------------------------------------------------------
# Atom parsing
# ---------------------------------------------------------------------------


def _parse_atom_feed_metadata(root: Any) -> dict[str, Any]:
    title_el = root.find(f"{{{ATOM_NS}}}title")
    subtitle_el = root.find(f"{{{ATOM_NS}}}subtitle")

    links = root.findall(f"{{{ATOM_NS}}}link")
    self_url = None
    alt_url = None
    for link_el in links:
        rel = link_el.get("rel", "alternate")
        href = link_el.get("href")
        if rel == "self" and href:
            self_url = href
        if rel == "alternate" and href:
            alt_url = href

    author_el = root.find(f"{{{ATOM_NS}}}author")
    author_name = None
    if author_el is not None:
        author_name = _get_text(author_el, f"{{{ATOM_NS}}}name")

    categories = [
        cat.get("term", "") for cat in root.findall(f"{{{ATOM_NS}}}category") if cat.get("term")
    ]

    return {
        "title": _get_text(root, f"{{{ATOM_NS}}}title") if title_el is not None else None,
        "subtitle": _get_text(root, f"{{{ATOM_NS}}}subtitle") if subtitle_el is not None else None,
        "self_url": self_url,
        "alternate_url": alt_url,
        "id": _get_text(root, f"{{{ATOM_NS}}}id"),
        "updated": _parse_atom_date(_get_text(root, f"{{{ATOM_NS}}}updated")),
        "rights": _get_text(root, f"{{{ATOM_NS}}}rights"),
        "generator": _get_text(root, f"{{{ATOM_NS}}}generator"),
        "author": author_name,
        "categories": categories,
    }


def _parse_atom_entry(
    entry: Any,
    feed_title: str | None,
    source_url: str,
    authority_id: str,
    max_content_length: int,
) -> Document:
    title = _get_text(entry, f"{{{ATOM_NS}}}title")

    links = entry.findall(f"{{{ATOM_NS}}}link")
    link = None
    for link_el in links:
        rel = link_el.get("rel", "alternate")
        href = link_el.get("href")
        if rel == "alternate" and href:
            link = href
            break
    if not link:
        for link_el in links:
            href = link_el.get("href")
            if href:
                link = href
                break

    summary = _get_text(entry, f"{{{ATOM_NS}}}summary")
    content_text = _get_text(entry, f"{{{ATOM_NS}}}content")
    published = _parse_atom_date(_get_text(entry, f"{{{ATOM_NS}}}published"))
    updated = _parse_atom_date(_get_text(entry, f"{{{ATOM_NS}}}updated"))
    entry_id = _get_text(entry, f"{{{ATOM_NS}}}id")

    author_el = entry.find(f"{{{ATOM_NS}}}author")
    author = None
    if author_el is not None:
        author = _get_text(author_el, f"{{{ATOM_NS}}}name")

    categories = [
        cat.get("term", "") for cat in entry.findall(f"{{{ATOM_NS}}}category") if cat.get("term")
    ]

    content = content_text or summary or ""
    sanitized = _sanitize_html(content, max_content_length)

    meta: dict[str, Any] = {}
    if entry_id:
        meta["guid"] = entry_id
    if author:
        meta["author"] = author
    if categories:
        meta["categories"] = categories

    return Document(
        authority_id=authority_id,
        source_url=link or source_url,
        canonical_url=link,
        title=title,
        summary=summary,
        content=sanitized,
        content_type="text/html",
        publication_date=published or updated,
        last_modified=updated,
        document_type="regulatory_update",
        metadata=meta,
    )


def _parse_atom_feed(
    root: Any,
    source_url: str,
    authority_id: str,
    max_entries: int,
    max_content_length: int,
) -> list[Document]:
    feed_meta = _parse_atom_feed_metadata(root)
    log.debug(
        "Atom feed: title=%s, entries=%d",
        feed_meta.get("title"),
        len(root.findall(f"{{{ATOM_NS}}}entry")),
    )

    documents: list[Document] = []
    for idx, entry in enumerate(root.findall(f"{{{ATOM_NS}}}entry")):
        if idx >= max_entries:
            break
        doc = _parse_atom_entry(
            entry,
            feed_meta.get("title"),
            source_url,
            authority_id,
            max_content_length,
        )
        documents.append(doc)

    return documents


# ---------------------------------------------------------------------------
# Detect feed type
# ---------------------------------------------------------------------------


def _detect_feed_type(root: Any) -> FeedType:
    tag = root.tag
    if tag == "rss":
        version = root.get("version", "")
        if version.startswith("2"):
            return FeedType.RSS
        raise UnsupportedFeedFormatError(
            f"Unsupported RSS version: {version} (only RSS 2.0 is supported)"
        )
    if tag == f"{{{ATOM_NS}}}feed":
        return FeedType.ATOM
    raise UnsupportedFeedFormatError(
        f"Unrecognized feed format: root tag '{tag}' "
        f"(expected 'rss' or '{{http://www.w3.org/2005/Atom}}feed')"
    )


# ---------------------------------------------------------------------------
# RSSParser
# ---------------------------------------------------------------------------


class RSSParser:
    """Parses RSS 2.0 and Atom feeds into Document models.

    Separated from RSSConnector for independent testability.
    Does not perform network I/O.
    """

    def __init__(self, config: RssConfig | None = None) -> None:
        self._config = config or RssConfig()

    @property
    def config(self) -> RssConfig:
        return self._config

    @staticmethod
    def is_supported_content_type(content_type: str) -> bool:
        base_type = content_type.split(";")[0].strip().lower()
        return base_type in _SUPPORTED_FEED_TYPES

    def parse(
        self,
        xml_content: str | bytes,
        source_url: str,
        authority_id: str,
    ) -> list[Document]:
        if isinstance(xml_content, str):
            if not xml_content.strip():
                raise RssParseError("Empty feed content")
            raw_size = len(xml_content.encode("utf-8"))
        else:
            if not xml_content.strip():
                raise RssParseError("Empty feed content")
            raw_size = len(xml_content)

        if raw_size > self._config.max_feed_size:
            raise FeedTooLargeError(
                f"Feed size ({raw_size} bytes) exceeds maximum ({self._config.max_feed_size} bytes)"
            )

        root = _parse_xml_safe(xml_content)

        feed_type = _detect_feed_type(root)

        log.debug("Detected feed type: %s for %s", feed_type.value, source_url)

        if feed_type == FeedType.RSS:
            documents = _parse_rss_feed(
                root,
                source_url,
                authority_id,
                self._config.max_entries,
                self._config.max_content_length,
            )
        else:
            documents = _parse_atom_feed(
                root,
                source_url,
                authority_id,
                self._config.max_entries,
                self._config.max_content_length,
            )

        if not documents:
            raise RssParseError("No entries found in feed")

        log.debug("Parsed %d entries from %s", len(documents), source_url)

        return documents

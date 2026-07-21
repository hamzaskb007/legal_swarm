from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any

from pydantic import BaseModel

from src.connectors.models import Document
from src.connectors.pdf.exceptions import (
    PdfCorruptedError,
    PdfEmptyError,
    PdfEncryptedError,
    PdfParseError,
    PdfTooLargeError,
    PdfTooManyPagesError,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MAX_PDF_SIZE = 50 * 1024 * 1024
DEFAULT_MAX_PAGES = 500
DEFAULT_MAX_TEXT_LENGTH = 500 * 1024

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class PdfConfig(BaseModel, frozen=True):
    max_pdf_size: int = DEFAULT_MAX_PDF_SIZE
    max_pages: int = DEFAULT_MAX_PAGES
    max_text_length: int = DEFAULT_MAX_TEXT_LENGTH


# ---------------------------------------------------------------------------
# PDF date parsing
# ---------------------------------------------------------------------------

_PDF_DATE_PATTERN = re.compile(
    r"^D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})"
    r"(?:([+-])(\d{2})'(\d{2})')?$"
)


def _parse_pdf_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        match = _PDF_DATE_PATTERN.match(date_str.strip())
        if not match:
            if date_str.strip().endswith("Z"):
                clean = date_str.strip().rstrip("Z")
                if clean.startswith("D:"):
                    clean = clean[2:]
                return datetime.strptime(clean, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
            return None
        year, month, day, hour, minute, second = map(int, match.groups()[:6])
        dt = datetime(year, month, day, hour, minute, second)
        tz_sign = match.group(7)
        if tz_sign:
            sign = 1 if tz_sign == "+" else -1
            tz_hours = int(match.group(8))
            tz_minutes = int(match.group(9))
            offset = timedelta(hours=sign * tz_hours, minutes=sign * tz_minutes)
            dt = dt.replace(tzinfo=timezone(offset))
        else:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# PDFParser
# ---------------------------------------------------------------------------


class PDFParser:
    """Extracts text and metadata from PDF documents.

    Separated from PDFConnector for independent testability.
    Does not perform network I/O.
    Uses PyMuPDF (fitz) for PDF processing.
    """

    def __init__(self, config: PdfConfig | None = None) -> None:
        self._config = config or PdfConfig()

    @property
    def config(self) -> PdfConfig:
        return self._config

    @staticmethod
    def is_supported_content_type(content_type: str) -> bool:
        base_type = content_type.split(";")[0].strip().lower()
        return base_type == "application/pdf"

    def parse(
        self,
        pdf_content: bytes,
        source_url: str,
        authority_id: str,
    ) -> Document:
        if not pdf_content:
            raise PdfEmptyError("Empty PDF content")

        content_size = len(pdf_content)
        if content_size > self._config.max_pdf_size:
            raise PdfTooLargeError(
                f"PDF size ({content_size} bytes) exceeds maximum "
                f"({self._config.max_pdf_size} bytes)"
            )

        try:
            import fitz
        except ImportError:
            raise PdfParseError("PyMuPDF (fitz) is not installed")

        doc: fitz.Document | None = None
        try:
            doc = fitz.open(stream=pdf_content, filetype="pdf")
        except fitz.FileDataError as e:
            raise PdfCorruptedError(f"Corrupted or invalid PDF: {e}") from e
        except Exception as e:
            raise PdfParseError(f"Failed to open PDF: {e}") from e

        try:
            if doc.is_encrypted or doc.needs_pass:
                raise PdfEncryptedError("PDF is encrypted or password-protected")

            metadata = doc.metadata or {}
            page_count = doc.page_count

            log.debug(
                "PDF: pages=%d, title=%s, source=%s",
                page_count,
                metadata.get("title"),
                source_url,
            )

            if page_count == 0:
                raise PdfEmptyError("PDF contains no pages")

            if page_count > self._config.max_pages:
                raise PdfTooManyPagesError(
                    f"PDF has {page_count} pages, exceeds maximum ({self._config.max_pages})"
                )

            title = metadata.get("title") or None
            author = metadata.get("author") or None
            subject = metadata.get("subject") or None
            creator = metadata.get("creator") or None
            producer = metadata.get("producer") or None
            creation_date = _parse_pdf_date(metadata.get("creationDate"))
            mod_date = _parse_pdf_date(metadata.get("modDate"))

            text_parts: list[str] = []
            total_length = 0
            remaining = self._config.max_text_length

            for page_num in range(page_count):
                page = doc[page_num]
                page_text = page.get_text("text")
                if not page_text or not page_text.strip():
                    continue
                if remaining > 0:
                    if len(page_text) > remaining:
                        page_text = page_text[:remaining]
                    text_parts.append(page_text)
                    total_length += len(page_text)
                    remaining = self._config.max_text_length - total_length
                else:
                    break

            content = "\n".join(text_parts)
            content = re.sub(r"[ \t]+", " ", content)
            content = re.sub(r"\n{3,}", "\n\n", content)
            content = content.strip()

            extra_meta: dict[str, Any] = {}
            if author:
                extra_meta["author"] = author
            if subject:
                extra_meta["subject"] = subject
            if creator:
                extra_meta["creator"] = creator
            if producer:
                extra_meta["producer"] = producer
            extra_meta["page_count"] = page_count

            return Document(
                authority_id=authority_id,
                source_url=source_url,
                title=title,
                summary=subject,
                content=content,
                content_type="application/pdf",
                publication_date=creation_date,
                last_modified=mod_date,
                document_type="regulatory_document",
                metadata=extra_meta,
            )

        except PdfEncryptedError:
            raise
        except PdfCorruptedError:
            raise
        except PdfEmptyError:
            raise
        except PdfTooManyPagesError:
            raise
        except PdfParseError:
            raise
        except Exception as e:
            raise PdfParseError(f"Unexpected error during PDF parsing: {e}") from e
        finally:
            if doc is not None:
                doc.close()

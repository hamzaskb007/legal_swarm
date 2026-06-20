from __future__ import annotations
from src.schema.schema import CitationRecord, SourceAuthority, SourceGovernanceRecord


class SourceGovernanceManager:
    def __init__(self):
        self._primary: list[CitationRecord] = []
        self._secondary: list[CitationRecord] = []
        self._tertiary: list[CitationRecord] = []
        self._seen_urls: set[str] = set()

    def add_citation(self, citation: CitationRecord) -> bool:
        if citation.source_url and citation.source_url in self._seen_urls:
            return False
        if citation.source_url:
            self._seen_urls.add(citation.source_url)
        if citation.authority == SourceAuthority.PRIMARY:
            self._primary.append(citation)
        elif citation.authority == SourceAuthority.SECONDARY:
            self._secondary.append(citation)
        else:
            self._tertiary.append(citation)
        return True

    def build(self) -> SourceGovernanceRecord:
        dominant = SourceAuthority.TERTIARY
        if self._primary:
            dominant = SourceAuthority.PRIMARY
        elif self._secondary:
            dominant = SourceAuthority.SECONDARY
        return SourceGovernanceRecord(
            primary_citations=list(self._primary),
            secondary_citations=list(self._secondary),
            tertiary_citations=list(self._tertiary),
            dominant_source=dominant,
        )

    def average_reliability(self) -> float:
        all_citations = self._primary + self._secondary + self._tertiary
        if not all_citations:
            return 0.0
        return sum(c.reliability_score for c in all_citations) / len(all_citations)

    def citation_count(self) -> int:
        return len(self._primary) + len(self._secondary) + len(self._tertiary)
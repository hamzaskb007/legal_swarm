from __future__ import annotations

EXACT_PARSER_MATCH_SCORE: int = 10
"""Awarded when the connector's declared parser types include the
authority's parser type.  Indicates the connector was designed for
this class of data source."""

CAPABILITY_MATCH_SCORE: int = 5
"""Awarded per capability the authority requires that the connector
also declares.  Reflects functional alignment between what the
authority offers and what the connector can consume."""

FULL_COMPATIBILITY_BONUS: int = 20
"""Awarded when the connector passes the full compatibility check
(parser + all capabilities).  Represents complete functional
alignment — the connector is verified to handle every aspect of
this authority's data profile."""

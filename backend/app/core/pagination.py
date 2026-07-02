"""Pagination bornée (anti-DoS sur les listes).

Un `limit` non plafonné laisse un client demander des pages arbitrairement grosses.
`clamp_limit` borne la taille de page ; `MAX_PAGE_SIZE` est le plafond dur.
"""

from __future__ import annotations

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500


def clamp_limit(limit: int | None) -> int:
    """Ramène `limit` dans [1, MAX_PAGE_SIZE] (défaut si None/invalide)."""
    if not limit or limit < 1:
        return DEFAULT_PAGE_SIZE
    return min(limit, MAX_PAGE_SIZE)


def clamp_offset(offset: int | None) -> int:
    return max(0, offset or 0)

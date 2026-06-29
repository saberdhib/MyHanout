"""Fêtes paramétrables impactant la demande (Aïd, Ramadan, fêtes locales...).

Le commerçant peut déclarer des périodes de forte/faible demande via une
configuration. Ici, un stub avec quelques fenêtres et un facteur multiplicatif.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FestivalWindow:
    name: str
    start: date
    end: date
    factor: float  # >1 = pic de demande, <1 = creux


# Fenêtres d'exemple (à remplacer par une config par commerçant en base).
DEFAULT_FESTIVALS: list[FestivalWindow] = [
    FestivalWindow("Aïd (exemple)", date(2026, 5, 27), date(2026, 5, 29), 1.8),
    FestivalWindow("Rentrée (exemple)", date(2026, 9, 1), date(2026, 9, 7), 1.2),
]


def festival_factor(day: date, festivals: list[FestivalWindow] | None = None) -> float:
    """Facteur multiplicatif lié aux fêtes pour une date donnée."""
    for window in festivals or DEFAULT_FESTIVALS:
        if window.start <= day <= window.end:
            return window.factor
    return 1.0

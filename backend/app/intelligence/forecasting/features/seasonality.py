"""Saisonnalité hebdomadaire (coefficients par jour de semaine)."""

from __future__ import annotations

from datetime import date

# Facteurs multiplicatifs indicatifs par jour (0=lundi ... 6=dimanche).
# Pics typiques d'un commerce de proximité en fin de semaine.
_WEEKDAY_FACTORS: dict[int, float] = {
    0: 0.90,
    1: 0.95,
    2: 1.00,
    3: 1.05,
    4: 1.25,  # vendredi
    5: 1.35,  # samedi
    6: 0.80,  # dimanche
}


def weekday_factor(day: date) -> float:
    """Coefficient de saisonnalité hebdomadaire pour une date donnée."""
    return _WEEKDAY_FACTORS.get(day.weekday(), 1.0)

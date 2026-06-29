"""Jours fériés (stub paramétrable).

Implémentation minimale par ensemble de dates. À terme, brancher la lib
`holidays` (dépendance optionnelle du groupe forecasting) selon le pays.
"""

from __future__ import annotations

from datetime import date

# Quelques dates fixes à titre d'exemple (à enrichir / régionaliser).
_FIXED_HOLIDAYS: set[tuple[int, int]] = {
    (1, 1),  # Jour de l'an
    (5, 1),  # Fête du travail
    (12, 25),  # Noël
}


def is_holiday(day: date) -> bool:
    """Indique si la date est un jour férié (approximation fixe)."""
    return (day.month, day.day) in _FIXED_HOLIDAYS

"""Règles d'**effectifs** lisibles et auditables (charge de travail → staff).

Fonction pure `suggest_staff(...)` : à partir de la demande prévue d'un jour et de
la capacité d'une personne, propose un effectif (jamais sous le plancher) et
l'explique par l'écart à la moyenne (« samedi +40 % → +1 personne »).

Aucune action autonome : suggestion (human-in-the-loop).
"""

from __future__ import annotations

import math

WEEKDAYS_FR = [
    "lundi",
    "mardi",
    "mercredi",
    "jeudi",
    "vendredi",
    "samedi",
    "dimanche",
]


def suggest_staff(
    *,
    predicted_demand: float,
    average_demand: float,
    units_per_staff_day: float,
    base_staff: int,
) -> tuple[int, int, float, str]:
    """Renvoie (effectif conseillé, delta vs plancher, écart % moyenne, explication)."""
    cap = units_per_staff_day if units_per_staff_day > 0 else 1.0
    suggested = (
        max(base_staff, math.ceil(predicted_demand / cap)) if predicted_demand > 0 else base_staff
    )
    delta = suggested - base_staff
    vs_avg = 0.0
    if average_demand > 0:
        vs_avg = round((predicted_demand - average_demand) / average_demand * 100, 0)

    if delta > 0:
        explanation = (
            f"Affluence prévue {predicted_demand:.0f} ({vs_avg:+.0f}% vs moyenne) → "
            f"prévoir {delta} personne(s) en plus ({suggested} au total)."
        )
    else:
        explanation = (
            f"Journée standard ({predicted_demand:.0f}, {vs_avg:+.0f}% vs moyenne) → "
            f"effectif de base ({base_staff}) suffisant."
        )
    return suggested, delta, vs_avg, explanation

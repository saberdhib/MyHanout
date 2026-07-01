"""Règles de **prix conseillé** lisibles et auditables (explicable, posture conseil).

Fonction pure `suggest_price(...)` : à partir du coût d'achat et d'une marge cible,
propose un prix (avec arrondi psychologique optionnel) et un verdict (monter / baisser
/ garder), en comparant à la marge actuelle.

Aucune action autonome : c'est une *suggestion* (human-in-the-loop).
"""

from __future__ import annotations

import math

from app.config import settings
from app.schemas.pricing import PriceDecision

_CHARM_ENDINGS = (0.49, 0.90, 0.95, 0.99)


def charm_round(price: float) -> float:
    """Arrondi psychologique : terminaison en ,49/,90/,95/,99 la plus proche."""
    if price < 1:
        return round(price, 2)
    base = float(math.floor(price))
    candidates: list[float] = [base + e for e in _CHARM_ENDINGS] + [base - 0.01, base + 0.99]
    best = min(candidates, key=lambda c: abs(c - price))
    return round(best, 2)


def suggest_price(
    *,
    product_id: int,
    current_price: float,
    unit_cost: float,
    target_margin_ratio: float | None = None,
    charm: bool | None = None,
) -> PriceDecision:
    """Prix conseillé selon marge cible + arrondi psychologique."""
    target = (
        settings.pricing_target_margin_ratio if target_margin_ratio is None else target_margin_ratio
    )
    charm = settings.pricing_charm_pricing if charm is None else charm
    target = min(max(target, 0.0), 0.95)  # borne raisonnable

    current_margin = (current_price - unit_cost) / current_price if current_price > 0 else 0.0
    raw_target_price = unit_cost / (1 - target) if target < 1 else current_price
    suggested = charm_round(raw_target_price) if charm else round(raw_target_price, 2)
    # Un prix conseillé ne descend jamais sous le coût.
    if suggested < unit_cost:
        suggested = round(unit_cost * 1.05, 2)
    target_margin = (suggested - unit_cost) / suggested if suggested > 0 else 0.0

    delta = round(suggested - current_price, 2)
    reasons = [
        f"coût {unit_cost:.2f}€, marge cible {target:.0%} → prix {raw_target_price:.2f}€",
    ]
    if charm:
        reasons.append(f"arrondi psychologique → {suggested:.2f}€")

    if abs(delta) < 0.05:
        action = "hold"
        explanation = (
            f"Prix cohérent : {current_price:.2f}€ tient déjà la marge cible "
            f"(~{current_margin:.0%}). Rien à changer."
        )
    elif delta > 0:
        action = "raise"
        explanation = (
            f"Monter à {suggested:.2f}€ (+{delta:.2f}) : marge actuelle {current_margin:.0%} "
            f"sous la cible {target:.0%} pour un coût de {unit_cost:.2f}€."
        )
    else:
        action = "lower"
        explanation = (
            f"Baisser à {suggested:.2f}€ ({delta:.2f}) : prix au-dessus du besoin de marge "
            f"(cible {target:.0%}), risque de freiner le volume."
        )

    # Confiance : plus le coût est fiable (>0) et l'écart modéré, plus on est sûr.
    confidence = 0.7 if unit_cost > 0 else 0.4
    return PriceDecision(
        product_id=product_id,
        current_price=round(current_price, 2),
        unit_cost=round(unit_cost, 2),
        current_margin=round(current_margin, 3),
        suggested_price=suggested,
        target_margin=round(target_margin, 3),
        action=action,
        delta=delta,
        confidence=confidence,
        explanation=explanation,
        reasons=reasons,
    )

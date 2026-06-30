"""Règles de **démarque** lisibles et auditables (cœur explicable, anti-gaspillage).

Fonction pure `decide_markdown(...)` : pour un lot périssable proche de la péremption,
décide s'il faut démarquer et de combien.

Modèle « fin de vie » (réaliste pour un commerce de proximité) :
- au rythme de vente actuel, on estime l'invendu (`leftover`) d'ici la péremption ;
- s'il n'y a pas d'invendu prévu → aucune démarque (le lot s'écoule au prix plein) ;
- sinon la démarque s'applique à cet **invendu à risque** (les unités qui finiraient à
  la poubelle, coût déjà engagé) : on cherche, via une élasticité-prix simplifiée, le
  **plus petit palier** qui récupère quasiment le maximum de cash possible.

Toute unité écoulée par la démarque est du cash récupéré (sinon = perte sèche).
Aucune action autonome : la décision est une *suggestion* (human-in-the-loop).
"""

from __future__ import annotations

from app.config import settings
from app.schemas.markdown import MarkdownDecision


def decide_markdown(
    *,
    product_id: int,
    quantity: float,
    days_to_expiry: int,
    avg_daily_demand: float,
    current_price: float,
    unit_cost: float,
    history_days: int = 30,
    tiers: list[int] | None = None,
    elasticity: float | None = None,
) -> MarkdownDecision | None:
    """Renvoie une décision de démarque explicable, ou `None` si inutile.

    `avg_daily_demand` : ventes/jour estimées (prévision ou historique).
    `unit_cost` : coût d'achat unitaire (sert au calcul de la perte évitée).
    """
    tiers = tiers or settings.markdown_tiers
    elasticity = settings.markdown_elasticity if elasticity is None else elasticity
    days = max(0, days_to_expiry)

    # Invendu prévu au prix plein d'ici la péremption (= unités à risque de perte).
    sellable_full = avg_daily_demand * days
    leftover = max(0.0, quantity - sellable_full)
    if leftover <= 0 or quantity <= 0:
        return None  # le lot s'écoule naturellement → pas de démarque

    baseline_loss = round(leftover * unit_cost, 2)  # perte si on ne fait rien (coût jeté)

    def recovered_for(tier: int) -> tuple[float, float, float]:
        """(cash récupéré, unités écoulées en plus, prix démarqué) pour un palier."""
        price_t = current_price * (1.0 - tier / 100.0)
        extra_daily = avg_daily_demand * elasticity * tier / 100.0  # surcroît de demande
        extra_cleared = min(leftover, extra_daily * days)
        return round(extra_cleared * price_t, 2), extra_cleared, round(price_t, 2)

    scored = [(tier, *recovered_for(tier)) for tier in tiers]
    best_value = max(v for _, v, _, _ in scored) if scored else 0.0
    if best_value <= 0:
        return None  # aucune démarque ne récupère de valeur

    # Plus petit palier atteignant ~95 % du meilleur cash récupérable (démarque douce).
    chosen, recovered_value, extra_cleared, suggested_price = next(
        (t, v, e, p) for (t, v, e, p) in scored if v >= 0.95 * best_value
    )

    avoided_loss = round(extra_cleared * unit_cost, 2)  # coût d'achat sauvé de la poubelle
    residual_waste = round(leftover - extra_cleared, 2)

    confidence = round(min(1.0, history_days / 30.0) * (1.0 - chosen / 200.0), 2)
    score = round(min(1.0, baseline_loss / 100.0) * (0.5 + 0.5 * confidence), 3)

    explanation = (
        f"Lot de {quantity:.0f} périme dans {days} j ; au rythme actuel "
        f"(~{avg_daily_demand:.1f}/j) ~{leftover:.0f} invendu(s) → perte ~{baseline_loss:.0f}€. "
        f"Démarque -{chosen}% (→ {suggested_price:.2f}€) pour écouler ~{extra_cleared:.0f} "
        f"unité(s) de plus et récupérer ~{recovered_value:.0f}€ (sinon perdus)."
    )
    reasons = [
        f"péremption dans {days} j",
        f"invendu prévu ~{leftover:.0f} (rythme {avg_daily_demand:.1f}/j)",
        f"palier -{chosen}% : récupère ~{recovered_value:.0f}€ (plus petit quasi-optimal)",
    ]
    if residual_waste > 0:
        reasons.append(f"~{residual_waste:.0f} unité(s) resteront invendues malgré la démarque")

    return MarkdownDecision(
        product_id=product_id,
        quantity_at_risk=round(quantity, 2),
        days_to_expiry=days,
        current_price=round(current_price, 2),
        suggested_price=suggested_price,
        discount_pct=chosen,
        expected_units_cleared=round(extra_cleared, 2),
        recovered_value=recovered_value,
        avoided_loss=avoided_loss,
        baseline_loss=baseline_loss,
        confidence=confidence,
        score=score,
        explanation=explanation,
        reasons=reasons,
        data_used={
            "quantity": round(quantity, 2),
            "days_to_expiry": days,
            "avg_daily_demand": round(avg_daily_demand, 3),
            "current_price": round(current_price, 2),
            "unit_cost": round(unit_cost, 2),
            "leftover_full_price": round(leftover, 2),
            "residual_waste": residual_waste,
            "elasticity": elasticity,
            "history_days": history_days,
        },
    )

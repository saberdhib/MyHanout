"""Règles de réassort **lisibles et auditables** (cœur explicable).

Fonction pure `decide(...)` : à partir de la demande prévue, du stock, des
signaux (génériques + métier du commerçant) et des contraintes produit, elle
renvoie une décision tracée (action, quantité, confiance, risque, score) avec
une **explication humaine** et la liste des règles déclenchées.

Aucune action autonome : la décision est une *suggestion* (human-in-the-loop).
"""

from __future__ import annotations

from app.config import settings
from app.schemas.dataplatform import RecoDecision


def _confidence(history_days: int, *, fallback: bool) -> float:
    """Plus l'historique est long, plus on est confiant ; fallback pénalisé."""
    base = min(1.0, history_days / 60.0)
    return round(base * (0.5 if fallback else 1.0), 2)


def decide(
    *,
    product_id: int,
    forecast_demand: float,
    current_stock: float,
    reorder_threshold: float,
    horizon_days: int,
    history_days: int,
    perishable: bool = False,
    shelf_life_days: int | None = None,
    avg_daily_demand: float | None = None,
    merchant_signal_boost: float = 0.0,
    seasonality_trend: float = 0.0,
) -> RecoDecision:
    """Applique les règles métier et renvoie une décision explicable.

    `merchant_signal_boost` : 0..1, agrège les signaux haussiers du commerçant
    (match, paie, braderie…) sur l'horizon. `seasonality_trend` : -1..1, tendance
    déduite (prévu vs moyenne historique).
    """
    reasons: list[str] = []
    daily = (
        avg_daily_demand
        if avg_daily_demand is not None
        else (forecast_demand / horizon_days if horizon_days else forecast_demand)
    )
    fallback = history_days < 14

    # Tampon de sécurité de base (incertitude).
    buffer_ratio = settings.reco_safety_buffer_ratio
    if seasonality_trend > 0:
        buffer_ratio += 0.10 * min(1.0, seasonality_trend)
        reasons.append("saisonnalité en hausse → stock cible relevé")
    if merchant_signal_boost > 0:
        buffer_ratio += 0.15 * min(1.0, merchant_signal_boost)
        reasons.append("signal commerçant haussier (match/paie/braderie) → tampon augmenté")

    buffer = forecast_demand * buffer_ratio
    target = forecast_demand + buffer
    projected_stock = current_stock - forecast_demand

    # Risque de rupture : fraction de la demande non couverte par le stock.
    risk_factor = 0.0
    if forecast_demand > 0:
        risk_factor = max(0.0, min(1.0, (forecast_demand - current_stock) / forecast_demand))

    coverage_days = (current_stock / daily) if daily > 0 else float("inf")

    # Périssable : on raccourcit l'horizon couvert (éviter la démarque).
    if perishable and shelf_life_days:
        max_cover = min(horizon_days, shelf_life_days)
        target = min(target, daily * max_cover)
        reasons.append(
            f"produit périssable → couverture plafonnée à {max_cover} j (anti-gaspillage)"
        )

    # Décision.
    if fallback:
        # Historique insuffisant → prudence : juste de quoi repasser le seuil.
        action = "order" if current_stock < reorder_threshold else "hold"
        qty = max(0.0, reorder_threshold - current_stock) if action == "order" else 0.0
        reasons.append("historique insuffisant (<14 j) → fallback conservateur")
        action_text = f"commande prudente de {qty:.0f}" if qty else "pas d’action"
        explanation = (
            f"Historique court : {action_text} "
            f"(stock {current_stock:.0f} vs seuil {reorder_threshold:.0f})."
        )
    elif coverage_days > settings.reco_overstock_days and current_stock > reorder_threshold:
        action = "reduce"
        qty = 0.0
        reasons.append(
            f"surstock : {coverage_days:.0f} j de couverture (> {settings.reco_overstock_days} j)"
        )
        explanation = (
            f"Stock élevé ({current_stock:.0f}, ~{coverage_days:.0f} j de couverture) : "
            "réduire la prochaine commande pour limiter la démarque."
        )
    elif risk_factor >= settings.reco_stockout_risk_threshold or projected_stock < 0:
        action = "order"
        qty = max(0.0, round(target - current_stock, 1))
        reasons.append(
            f"risque de rupture {risk_factor:.0%} (prévu {forecast_demand:.0f} > stock "
            f"{current_stock:.0f})"
        )
        explanation = (
            f"Commander ~{qty:.0f} : demande prévue {forecast_demand:.0f} sur {horizon_days} j, "
            f"stock {current_stock:.0f}, cible {target:.0f} (tampon inclus)."
        )
    else:
        action = "hold"
        qty = 0.0
        reasons.append("stock suffisant pour l'horizon")
        explanation = (
            f"Pas de commande nécessaire : stock {current_stock:.0f} couvre la demande prévue "
            f"{forecast_demand:.0f} sur {horizon_days} j."
        )

    confidence = _confidence(history_days, fallback=fallback)
    # Score de priorité (tri du dashboard) : risque pondéré par la confiance + signaux.
    if action == "order":
        score = round(risk_factor * (0.5 + 0.5 * confidence) + 0.1 * merchant_signal_boost, 3)
    elif action == "reduce":
        score = round(min(1.0, coverage_days / (settings.reco_overstock_days * 2)), 3)
    else:
        score = 0.0

    return RecoDecision(
        product_id=product_id,
        action=action,
        suggested_quantity=qty,
        horizon_days=horizon_days,
        confidence=confidence,
        risk_factor=round(risk_factor, 3),
        score=score,
        explanation=explanation,
        reasons=reasons,
        data_used={
            "forecast_demand": round(forecast_demand, 2),
            "current_stock": round(current_stock, 2),
            "reorder_threshold": round(reorder_threshold, 2),
            "avg_daily_demand": round(daily, 3),
            "coverage_days": (None if coverage_days == float("inf") else round(coverage_days, 1)),
            "buffer_ratio": round(buffer_ratio, 3),
            "merchant_signal_boost": round(merchant_signal_boost, 3),
            "seasonality_trend": round(seasonality_trend, 3),
            "history_days": history_days,
        },
    )

"""Règles de **planification de production** lisibles et auditables (explicable).

Fonction pure `plan_production(...)` : pour un produit fini fabriqué en magasin,
décide combien produire d'ici l'horizon = couvrir la demande prévue moins le stock
déjà disponible, arrondi au **rendement** d'une fournée (on ne produit pas une
demi-fournée).

Aucune action autonome : la décision est une *suggestion* (human-in-the-loop).
"""

from __future__ import annotations

import math

from app.schemas.recipe import ProductionDecision


def plan_production(
    *,
    product_id: int,
    forecast_demand: float,
    current_stock: float,
    yield_quantity: float,
    horizon_days: int,
    history_days: int = 30,
) -> ProductionDecision:
    """Applique les règles et renvoie une décision de production explicable."""
    yield_q = yield_quantity if yield_quantity and yield_quantity > 0 else 1.0
    net_need = max(0.0, forecast_demand - current_stock)
    batches = math.ceil(net_need / yield_q) if net_need > 0 else 0
    suggested_quantity = round(batches * yield_q, 2)

    confidence = round(min(1.0, history_days / 30.0), 2)

    if net_need <= 0:
        explanation = (
            f"Stock suffisant ({current_stock:.0f}) pour la demande prévue "
            f"{forecast_demand:.0f} sur {horizon_days} j : aucune production nécessaire."
        )
        reasons = ["stock couvre la demande de l'horizon"]
    else:
        explanation = (
            f"Produire ~{suggested_quantity:.0f} ({batches} fournée(s) de {yield_q:.0f}) : "
            f"demande prévue {forecast_demand:.0f} sur {horizon_days} j, stock "
            f"{current_stock:.0f} → besoin net {net_need:.0f}."
        )
        reasons = [
            f"demande prévue {forecast_demand:.0f} > stock {current_stock:.0f}",
            f"arrondi à {batches} fournée(s) de {yield_q:.0f}",
        ]

    return ProductionDecision(
        product_id=product_id,
        forecast_demand=round(forecast_demand, 2),
        current_stock=round(current_stock, 2),
        net_need=round(net_need, 2),
        batches=float(batches),
        suggested_quantity=suggested_quantity,
        horizon_days=horizon_days,
        confidence=confidence,
        explanation=explanation,
        reasons=reasons,
        data_used={
            "forecast_demand": round(forecast_demand, 2),
            "current_stock": round(current_stock, 2),
            "yield_quantity": yield_q,
            "history_days": history_days,
        },
    )

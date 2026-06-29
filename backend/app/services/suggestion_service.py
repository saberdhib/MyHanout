"""Service de suggestion de commande (déclenché par le commerçant, explicable).

Réutilise le `ForecastModel` existant. Pour chaque produit :
  quantité suggérée = demande prévue (horizon) + tampon de sécurité − stock courant.
Chaque ligne porte son EXPLICATION (prévision, stock, délai, confiance).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product
from app.repositories.sale import SaleRepository
from app.repositories.stock import StockRepository
from app.schemas.order import SuggestionLine, SuggestionOut
from app.services.forecast_service import forecast_product

# Tampon de sécurité : fraction de la demande prévue (incertitude + aléa week-end).
_SAFETY_BUFFER_RATIO = 0.15

_HORIZON_KEYWORDS = {
    "demain": 1,
    "today": 1,
    "aujourd'hui": 1,
    "semaine": 7,
    "semaine prochaine": 7,
    "week": 7,
}


def resolve_horizon(horizon_days: int | None, horizon: str | None) -> int:
    """Traduit un horizon (int ou mot-clé) en nombre de jours."""
    if horizon_days:
        return max(1, horizon_days)
    if horizon:
        return _HORIZON_KEYWORDS.get(horizon.strip().lower(), 7)
    return 7


def _confidence_from_history(history_days: int) -> float:
    """Heuristique : plus l'historique est long, plus on est confiant."""
    return round(min(1.0, history_days / 60.0), 2)


async def suggest_orders(
    session: AsyncSession,
    *,
    horizon_days: int | None = None,
    horizon: str | None = None,
    product_ids: list[int] | None = None,
) -> SuggestionOut:
    days = resolve_horizon(horizon_days, horizon)
    stock_repo = StockRepository(session)
    sale_repo = SaleRepository(session)

    query = select(Product).options(selectinload(Product.supplier))
    if product_ids:
        query = query.where(Product.id.in_(product_ids))
    products = list((await session.scalars(query)).all())

    lines: list[SuggestionLine] = []
    model_name = "naive"
    for product in products:
        forecast = await forecast_product(session, product.id, horizon_days=days)
        model_name = forecast.model
        predicted = round(sum(p.yhat for p in forecast.points), 2)
        current_stock = await stock_repo.total_quantity(product.id)
        buffer = round(predicted * _SAFETY_BUFFER_RATIO, 2)
        suggested = max(0.0, round(predicted + buffer - current_stock, 2))

        history = await sale_repo.daily_history(product.id)
        lead_time = product.supplier.lead_time_days if product.supplier else 1

        # On ne suggère que ce qui a un intérêt (qté > 0).
        if suggested <= 0 and predicted <= 0:
            continue

        explanation = (
            f"{suggested:g} {product.unit} de « {product.name} » : "
            f"demande prévue {predicted:g} sur {days} j "
            f"+ tampon {buffer:g} − stock actuel {current_stock:g} "
            f"(délai fournisseur {lead_time} j)."
        )
        lines.append(
            SuggestionLine(
                product_id=product.id,
                product_name=product.name,
                unit=product.unit,
                suggested_quantity=suggested,
                predicted_demand=predicted,
                safety_buffer=buffer,
                current_stock=current_stock,
                lead_time_days=lead_time,
                confidence=_confidence_from_history(len(history)),
                explanation=explanation,
            )
        )

    return SuggestionOut(
        horizon_days=days,
        generated_for=date.today(),
        model=model_name,
        lines=lines,
    )

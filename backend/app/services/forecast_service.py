"""Service forecast : lit l'historique de ventes et produit une prévision.

Prouve le pipeline bout-en-bout (data -> modèle -> API).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.intelligence.forecasting import (
    ForecastResult,
    HistoryPoint,
    get_forecast_model,
)
from app.repositories.sale import SaleRepository


async def forecast_product(
    session: AsyncSession,
    product_id: int,
    *,
    horizon_days: int | None = None,
    model_name: str | None = None,
) -> ForecastResult:
    """Construit l'historique journalier et renvoie une prévision."""
    repo = SaleRepository(session)
    rows = await repo.daily_history(product_id)
    history = [
        HistoryPoint(ds=ds if isinstance(ds, date) else date.fromisoformat(str(ds)), y=y)
        for ds, y in rows
    ]
    model = get_forecast_model(model_name)
    return model.predict(
        history,
        horizon_days=horizon_days or settings.forecast_horizon_days,
        product_id=product_id,
    )

"""Endpoints prévisions (lecture)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.schemas.forecast import ForecastOut
from app.services.forecast_service import forecast_product

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


@router.get("/{product_id}", response_model=ForecastOut)
async def get_forecast(
    product_id: int,
    horizon_days: int = Query(default=14, ge=1, le=90),
    model: str | None = Query(default=None, description="naive|prophet|lgbm"),
    session: AsyncSession = Depends(get_db),
    _: object = Depends(require_permission("forecasts")),
) -> ForecastOut:
    """Prévision de demande pour un produit (sur l'historique de ventes seed)."""
    result = await forecast_product(
        session, product_id, horizon_days=horizon_days, model_name=model
    )
    return ForecastOut.model_validate(result.model_dump())

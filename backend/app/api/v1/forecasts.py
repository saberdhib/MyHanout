"""Endpoints prévisions (lecture)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.intelligence.forecasting.correlation import analyze_factors, cross_product
from app.schemas.forecast import ForecastOut
from app.schemas.insights import CrossProductReport, FactorReport
from app.services.forecast_service import forecast_product

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


@router.get("/{product_id}/factors", response_model=FactorReport)
async def product_factors(
    product_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
    session: AsyncSession = Depends(get_db),
    _: object = Depends(require_permission("forecasts")),
) -> FactorReport:
    """Facteurs externes corrélés à la demande (météo, vacances, carburant, foot…).

    Classés par force de corrélation, avec un verdict honnête
    (corrélation / coïncidence) et l'avertissement corrélation ≠ causalité.
    """
    return await analyze_factors(
        session, product_id=product_id, date_from=date_from, date_to=date_to
    )


@router.get("/{product_id}/cross-product", response_model=CrossProductReport)
async def product_relations(
    product_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
    session: AsyncSession = Depends(get_db),
    _: object = Depends(require_permission("forecasts")),
) -> CrossProductReport:
    """Produits substituts / compléments (effets croisés via co-ventes)."""
    return await cross_product(session, product_id=product_id, date_from=date_from, date_to=date_to)


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

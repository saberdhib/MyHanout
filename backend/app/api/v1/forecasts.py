"""Endpoints prévisions (lecture)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.intelligence.forecasting.correlation import analyze_factors, cross_product
from app.models.base import PipelineTrigger
from app.schemas.dataplatform import PipelineRunOut
from app.schemas.forecast import BacktestModelOut, BacktestOut, ForecastOut
from app.schemas.insights import CrossProductReport, FactorReport
from app.services import pipeline_service
from app.services.forecast_service import backtest_product, forecast_product

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


@router.post("/recompute", response_model=PipelineRunOut)
async def recompute(
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("forecasts")),
) -> PipelineRunOut:
    """Relance le calcul des prévisions + recommandations (job `recommend` tracé)."""
    run = await pipeline_service.run_job(
        session, "recommend", trigger=PipelineTrigger.MERCHANT, user_id=user.id
    )
    from app.api.v1.pipelines import _out

    return _out(run)


@router.get("/{product_id}/backtest", response_model=BacktestOut)
async def product_backtest(
    product_id: int,
    horizon_days: int = 7,
    folds: int = 3,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> BacktestOut:
    """Backtest walk-forward : MAE/MAPE par modèle sur l'historique réel + verdict honnête.

    Compare une baseline plate, le naïf saisonnier, et Prophet/LGBM s'ils sont installés.
    Montre si un modèle avancé bat vraiment le naïf (ou reste à installer).
    """
    report = await backtest_product(session, product_id, horizon_days=horizon_days, folds=folds)
    return BacktestOut(
        product_id=report.product_id,
        horizon_days=report.horizon_days,
        folds=report.folds,
        history_points=report.history_points,
        results=[
            BacktestModelOut(
                model=r.model,
                available=r.available,
                mae=r.mae,
                mape=r.mape,
                n_points=r.n_points,
                note=r.note,
            )
            for r in report.results
        ],
        best_model=report.best_model,
        verdict=report.verdict,
    )


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

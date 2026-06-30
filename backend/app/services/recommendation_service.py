"""Service de recommandations : rassemble les entrées, applique le moteur, persiste.

Entrées croisées (différenciateur MyHanout) :
- demande prévue (service ML isolé ou in-process, avec `model_version`),
- stock courant + seuil,
- **signaux métier du commerçant** (match, paie, braderie…) sur l'horizon,
- saisonnalité déduite (prévu vs moyenne historique).

Chaque reco persistée référence son `pipeline_run_id` + `model_version` (traçabilité)
et porte son explication + les données utilisées (audit).
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.tenancy import get_current_org
from app.intelligence.forecasting.service_client import get_forecast_service_client
from app.intelligence.recommendation.engine import decide
from app.models.base import RecommendationStatus
from app.models.external_signal import ExternalSignal
from app.models.product import Product
from app.models.recommendation import Recommendation
from app.repositories.sale import SaleRepository
from app.repositories.stock import StockRepository
from app.schemas.dataplatform import RecoDecision, SimulateResult


async def _stock_for(stock_repo: StockRepository, product_id: int) -> tuple[float, float]:
    """(quantité courante, seuil de réassort) agrégés pour un produit."""
    stocks = await stock_repo.list_for_product(product_id)
    qty = float(sum(float(s.quantity) for s in stocks))
    threshold = float(max((float(s.reorder_threshold) for s in stocks), default=0.0))
    return qty, threshold


async def _merchant_boost(session: AsyncSession, *, horizon_days: int, today: date) -> float:
    """Fraction de jours de l'horizon portant un signal métier haussier (0..1)."""
    end = today + timedelta(days=horizon_days)
    rows = await session.execute(
        select(ExternalSignal.signal_date).where(
            ExternalSignal.signal_date >= today,
            ExternalSignal.signal_date <= end,
            ExternalSignal.value > 0,
        )
    )
    days = {r[0] for r in rows}
    return round(min(1.0, len(days) / max(1, horizon_days)), 3)


async def _inputs_for_product(
    session: AsyncSession,
    product: Product,
    *,
    horizon_days: int,
    stock_repo: StockRepository,
    sale_repo: SaleRepository,
    merchant_boost: float,
    today: date,
) -> dict:
    client = get_forecast_service_client()
    fc = await client.predict_product(
        session, product.id, horizon_days=horizon_days, model_name=None
    )
    forecast_demand = float(sum(p.yhat for p in fc.points))

    history = await sale_repo.daily_history(product.id)
    history_days = len(history)
    hist_daily = sum(float(y) for _, y in history) / history_days if history_days else 0.0
    forecast_daily = forecast_demand / horizon_days if horizon_days else forecast_demand
    seasonality_trend = 0.0
    if hist_daily > 0:
        seasonality_trend = max(-1.0, min(1.0, (forecast_daily - hist_daily) / hist_daily))

    qty, threshold = await _stock_for(stock_repo, product.id)
    return {
        "forecast_demand": forecast_demand,
        "current_stock": qty,
        "reorder_threshold": threshold,
        "history_days": history_days,
        "perishable": bool(product.perishable),
        "shelf_life_days": product.shelf_life_days,
        "avg_daily_demand": forecast_daily,
        "merchant_signal_boost": merchant_boost,
        "seasonality_trend": seasonality_trend,
        "model_version": client.model_version(),
    }


async def compute_recommendations(
    session: AsyncSession,
    *,
    horizon_days: int | None = None,
    product_ids: list[int] | None = None,
    persist: bool = False,
    pipeline_run_id: int | None = None,
    today: date | None = None,
) -> list[RecoDecision]:
    """Calcule (et optionnellement persiste) les recommandations triées par score."""
    horizon = horizon_days or settings.forecast_horizon_days
    today = today or date.today()
    stock_repo = StockRepository(session)
    sale_repo = SaleRepository(session)

    query = select(Product).options(selectinload(Product.supplier))
    if product_ids:
        query = query.where(Product.id.in_(product_ids))
    products = list((await session.scalars(query)).all())

    boost = await _merchant_boost(session, horizon_days=horizon, today=today)

    if persist:
        # On remplace le jeu de recos "suggested" précédent (on garde l'historique
        # accepted/dismissed). NB : un DELETE ORM n'est PAS filtré par le garde-fou
        # (event SELECT only) → on filtre l'organisation EXPLICITEMENT (sécurité).
        org_id = get_current_org()
        if org_id is not None:
            await session.execute(
                delete(Recommendation).where(
                    Recommendation.organization_id == org_id,
                    Recommendation.status == RecommendationStatus.SUGGESTED,
                )
            )

    decisions: list[RecoDecision] = []
    for product in products:
        inp = await _inputs_for_product(
            session,
            product,
            horizon_days=horizon,
            stock_repo=stock_repo,
            sale_repo=sale_repo,
            merchant_boost=boost,
            today=today,
        )
        model_version = inp.pop("model_version")
        decision = decide(product_id=product.id, horizon_days=horizon, **inp)
        decisions.append(decision)
        if persist:
            session.add(
                Recommendation(
                    product_id=product.id,
                    pipeline_run_id=pipeline_run_id,
                    model_version=model_version,
                    action=decision.action,
                    suggested_quantity=decision.suggested_quantity,
                    horizon_days=decision.horizon_days,
                    confidence=decision.confidence,
                    risk_factor=decision.risk_factor,
                    score=decision.score,
                    explanation=decision.explanation,
                    data_used=json.dumps(decision.data_used, ensure_ascii=False),
                )
            )
    if persist:
        await session.flush()

    decisions.sort(key=lambda d: d.score, reverse=True)
    return decisions


async def simulate_order(
    session: AsyncSession,
    *,
    product_id: int,
    quantity: float,
    horizon_days: int | None = None,
    today: date | None = None,
) -> SimulateResult:
    """« Et si je commande X ? » → impact projeté sur rupture / surstock."""
    horizon = horizon_days or settings.forecast_horizon_days
    today = today or date.today()
    stock_repo = StockRepository(session)
    sale_repo = SaleRepository(session)
    client = get_forecast_service_client()

    fc = await client.predict_product(session, product_id, horizon_days=horizon, model_name=None)
    forecast_demand = float(sum(p.yhat for p in fc.points))
    daily = forecast_demand / horizon if horizon else forecast_demand
    current, _ = await _stock_for(stock_repo, product_id)
    _ = sale_repo  # cohérence d'API (historique déjà reflété dans le forecast)

    projected = current + quantity - forecast_demand
    stockout_risk = 0.0
    if forecast_demand > 0:
        stockout_risk = max(
            0.0, min(1.0, (forecast_demand - (current + quantity)) / forecast_demand)
        )
    coverage = ((current + quantity) / daily) if daily > 0 else float("inf")

    if projected < 0:
        verdict = f"rupture probable (manque ~{abs(projected):.0f})"
    elif coverage > settings.reco_overstock_days:
        verdict = f"surstock (~{coverage:.0f} j de couverture)"
    else:
        verdict = "équilibré"
    explanation = (
        f"Commande {quantity:.0f} : stock projeté {projected:.0f} après une demande prévue "
        f"{forecast_demand:.0f} sur {horizon} j → {verdict}."
    )
    return SimulateResult(
        product_id=product_id,
        ordered_quantity=quantity,
        horizon_days=horizon,
        forecast_demand=round(forecast_demand, 1),
        current_stock=round(current, 1),
        projected_stock=round(projected, 1),
        stockout_risk=round(stockout_risk, 3),
        overstock_days=(0.0 if coverage == float("inf") else round(coverage, 1)),
        explanation=explanation,
    )

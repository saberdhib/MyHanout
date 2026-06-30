"""Endpoints recommandations : liste explicable + simulation de commande."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.models.product import Product
from app.models.recommendation import Recommendation
from app.schemas.common import ListResponse
from app.schemas.dataplatform import RecommendationOut, SimulateRequest, SimulateResult
from app.services.recommendation_service import compute_recommendations, simulate_order

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=ListResponse[RecommendationOut])
async def list_recommendations(
    status: str | None = None,
    live: bool = Query(default=False, description="Recalcule à la volée au lieu de lire la base"),
    limit: int = Query(default=100, ge=1, le=300),
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> ListResponse[RecommendationOut]:
    """Recommandations persistées (ou recalculées si `live=true`), triées par priorité."""
    names: dict[int, str] = {}
    if live:
        decisions = await compute_recommendations(session, persist=False)
        pids = [d.product_id for d in decisions]
        if pids:
            for pid, name in await session.execute(
                select(Product.id, Product.name).where(Product.id.in_(pids))
            ):
                names[pid] = name
        items = [
            RecommendationOut(
                id=0,
                product_id=d.product_id,
                product_name=names.get(d.product_id),
                action=d.action,
                suggested_quantity=d.suggested_quantity,
                horizon_days=d.horizon_days,
                confidence=d.confidence,
                risk_factor=d.risk_factor,
                score=d.score,
                status="suggested",
                model_version="live",
                explanation=d.explanation,
            )
            for d in decisions
        ]
        return ListResponse(items=items, total=len(items))

    stmt = select(Recommendation).order_by(Recommendation.score.desc()).limit(limit)
    if status:
        stmt = stmt.where(Recommendation.status == status)
    rows = list((await session.scalars(stmt)).all())
    pids = [r.product_id for r in rows]
    if pids:
        for pid, name in await session.execute(
            select(Product.id, Product.name).where(Product.id.in_(pids))
        ):
            names[pid] = name
    items = [
        RecommendationOut(
            id=r.id,
            product_id=r.product_id,
            product_name=names.get(r.product_id),
            action=r.action,
            suggested_quantity=r.suggested_quantity,
            horizon_days=r.horizon_days,
            confidence=r.confidence,
            risk_factor=r.risk_factor,
            score=r.score,
            status=str(r.status),
            model_version=r.model_version,
            pipeline_run_id=r.pipeline_run_id,
            explanation=r.explanation,
        )
        for r in rows
    ]
    return ListResponse(items=items, total=len(items))


@router.post("/simulate", response_model=SimulateResult)
async def simulate(
    body: SimulateRequest,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> SimulateResult:
    """« Et si je commande X ? » → impact projeté sur rupture / surstock / couverture."""
    return await simulate_order(
        session,
        product_id=body.product_id,
        quantity=body.quantity,
        horizon_days=body.horizon_days,
    )

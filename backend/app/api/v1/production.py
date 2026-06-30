"""Endpoints production en magasin : plan (live), scan (persiste), confirmer/écarter."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.exceptions import NotFoundError
from app.core.security import CurrentUser
from app.models.base import ProductionStatus
from app.models.product import Product
from app.models.recipe import ProductionPlan
from app.schemas.recipe import ProductionPlanOut, ProductionPlanResult
from app.services.production_service import compute_production, set_status

router = APIRouter(prefix="/production", tags=["production"])


@router.get("/plan", response_model=ProductionPlanResult)
async def get_plan(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> ProductionPlanResult:
    """Plan de production du jour (calculé à la volée) + besoins ingrédients."""
    return await compute_production(session, persist=False)


@router.post("/scan", response_model=ProductionPlanResult)
async def scan_plan(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> ProductionPlanResult:
    """Recalcule et persiste le plan de production (snapshot à valider)."""
    result = await compute_production(session, persist=True)
    await session.commit()
    return result


def _out(row: ProductionPlan, name: str | None) -> ProductionPlanOut:
    return ProductionPlanOut(
        id=row.id,
        product_id=row.product_id,
        product_name=name,
        recipe_id=row.recipe_id,
        plan_date=row.plan_date.isoformat() if row.plan_date else None,
        horizon_days=row.horizon_days,
        forecast_demand=row.forecast_demand,
        current_stock=row.current_stock,
        suggested_quantity=row.suggested_quantity,
        batches=row.batches,
        confidence=row.confidence,
        status=str(row.status),
        model_version=row.model_version,
        explanation=row.explanation,
    )


@router.post("/{plan_id}/confirm", response_model=ProductionPlanOut)
async def confirm_plan(
    plan_id: int,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> ProductionPlanOut:
    """Confirme un plan de production (human-in-the-loop)."""
    row = await set_status(session, plan_id, ProductionStatus.CONFIRMED)
    if row is None:
        raise NotFoundError("Plan de production introuvable")
    await session.commit()
    name = await session.scalar(select(Product.name).where(Product.id == row.product_id))
    return _out(row, name)


@router.post("/{plan_id}/dismiss", response_model=ProductionPlanOut)
async def dismiss_plan(
    plan_id: int,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> ProductionPlanOut:
    """Écarte un plan de production (human-in-the-loop)."""
    row = await set_status(session, plan_id, ProductionStatus.DISMISSED)
    if row is None:
        raise NotFoundError("Plan de production introuvable")
    await session.commit()
    name = await session.scalar(select(Product.name).where(Product.id == row.product_id))
    return _out(row, name)

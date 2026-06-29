"""Endpoints MLOps : métriques d'erreur + réentraînement."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.services.mlops_service import aggregate_metrics, retrain

router = APIRouter(prefix="/mlops", tags=["mlops"])


@router.get("/metrics")
async def metrics(
    product_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> dict:
    """Agrégats de qualité de prévision (MAE/MAPE) par produit/modèle."""
    return {"metrics": await aggregate_metrics(session, product_id)}


@router.post("/retrain")
async def trigger_retrain(
    product_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> dict:
    """Réentraîne le modèle (recalcule la baseline) et versionne."""
    return await retrain(session, product_id)

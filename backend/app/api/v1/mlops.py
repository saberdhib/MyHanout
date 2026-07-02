"""Endpoints MLOps : métriques d'erreur + registre de modèles + réentraînement."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.models.model_artifact import ModelArtifact, RetrainTrigger
from app.services import model_registry_service
from app.services.mlops_service import aggregate_metrics

router = APIRouter(prefix="/mlops", tags=["mlops"])


def _artifact_out(a: ModelArtifact) -> dict:
    return {
        "id": a.id,
        "product_id": a.product_id,
        "model_name": a.model_name,
        "version": a.version,
        "baseline": a.baseline,
        "n_observations": a.n_observations,
        "mae": a.mae,
        "mape": a.mape,
        "trigger": str(a.trigger),
        "active": a.active,
        "artifact_uri": a.artifact_uri,
        "trained_at": a.trained_at.isoformat() if a.trained_at else None,
    }


@router.get("/metrics")
async def metrics(
    product_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> dict:
    """Agrégats de qualité de prévision (MAE/MAPE) par produit/modèle."""
    return {"metrics": await aggregate_metrics(session, product_id)}


@router.get("/models")
async def models(
    product_id: int | None = Query(default=None),
    active_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> dict:
    """Registre des modèles versionnés (traçabilité MLOps)."""
    rows = await model_registry_service.list_models(session, product_id, active_only=active_only)
    return {"models": [_artifact_out(a) for a in rows]}


@router.post("/retrain")
async def trigger_retrain(
    product_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> dict:
    """Réentraîne (recalcule la baseline) et **versionne** dans le registre.

    `product_id` fourni → ce produit ; sinon tout le catalogue du commerce.
    """
    if product_id is not None:
        arts = [
            await model_registry_service.retrain_product(
                session, product_id, trigger=RetrainTrigger.MANUAL
            )
        ]
    else:
        arts = await model_registry_service.retrain_all(session, trigger=RetrainTrigger.MANUAL)
    return {"retrained": len(arts), "models": [_artifact_out(a) for a in arts]}

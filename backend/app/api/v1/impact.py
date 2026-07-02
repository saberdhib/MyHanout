"""Endpoint tableau d'impact (ROI en euros) — valeur consolidée produite par l'outil."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.schemas.impact import ImpactView
from app.services.impact_service import compute_impact

router = APIRouter(prefix="/impact", tags=["impact"])


@router.get("", response_model=ImpactView)
async def impact(
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> ImpactView:
    """Impact estimé de l'outil sur la période (euros gagnés/révélés + temps gagné)."""
    return await compute_impact(session, days=days)

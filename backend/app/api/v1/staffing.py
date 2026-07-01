"""Endpoint Effectifs : plan de personnel dérivé de l'affluence prévue."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.schemas.staffing import StaffingPlan
from app.services.staffing_service import compute_staffing

router = APIRouter(prefix="/staffing", tags=["staffing"])


@router.get("/plan", response_model=StaffingPlan)
async def plan(
    horizon_days: int = Query(default=7, ge=1, le=31),
    base_staff: int | None = Query(default=None, ge=0, le=50),
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> StaffingPlan:
    """Effectif conseillé par jour sur l'horizon (pics d'affluence = renfort)."""
    return await compute_staffing(session, horizon_days=horizon_days, base_staff=base_staff)

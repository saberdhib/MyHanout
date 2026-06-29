"""Endpoints agents : évaluation du routage."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import require_permission
from app.core.security import CurrentUser
from app.intelligence.agents.evaluation import RoutingReport, evaluate_routing

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/eval", response_model=RoutingReport)
async def agents_eval(
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> RoutingReport:
    """Précision de routage des agents sur le golden set (observabilité IA)."""
    return evaluate_routing()

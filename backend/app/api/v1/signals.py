"""Endpoint signaux externes (météo + tendances) — compagnon du quotidien."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.security import CurrentUser
from app.intelligence.signals import SignalsBundle, get_signals

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=SignalsBundle)
async def signals(_: CurrentUser = Depends(get_current_user)) -> SignalsBundle:
    """Météo + tendances du moment (mock keyless), pour enrichir les recommandations."""
    return get_signals()

"""Endpoints relance client : segments (aperçu) + envoi ciblé (human-in-the-loop)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.schemas.reengagement import SegmentsResponse, SendResult
from app.services import reengagement_service

router = APIRouter(prefix="/reengagement", tags=["reengagement"])


@router.get("/segments", response_model=SegmentsResponse)
async def segments(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> SegmentsResponse:
    """Aperçu des segments de relance (aucun envoi)."""
    return await reengagement_service.build_segments(session)


@router.post("/send", response_model=SendResult)
async def send(
    segment: str,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("orders")),
) -> SendResult:
    """Envoie la relance aux clients opt-in du segment (validation humaine requise)."""
    try:
        return await reengagement_service.send_campaign(session, segment, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

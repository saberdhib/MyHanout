"""Endpoint Bilan hebdomadaire : consulter + envoyer sur WhatsApp."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.schemas.report import WeeklyReport
from app.services.report_service import compute_weekly_report, send_weekly_report

router = APIRouter(prefix="/report", tags=["report"])


@router.get("/weekly", response_model=WeeklyReport)
async def weekly(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("finance")),
) -> WeeklyReport:
    """Bilan de la semaine écoulée (CA, marge, top ventes, actions)."""
    return await compute_weekly_report(session)


@router.post("/weekly/send", response_model=WeeklyReport)
async def send(
    to: str = "demo",
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("finance")),
) -> WeeklyReport:
    """Pousse le bilan sur WhatsApp (mock par défaut / numéro du commerce)."""
    report = await send_weekly_report(session, to=to)
    await session.commit()
    return report

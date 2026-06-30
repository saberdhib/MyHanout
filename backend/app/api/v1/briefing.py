"""Endpoints briefing du matin : consulter, générer, envoyer, cocher une tâche."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.exceptions import NotFoundError
from app.core.security import CurrentUser
from app.models.briefing import DailyBriefing
from app.schemas.briefing import BriefingItemOut, BriefingOut
from app.services.briefing_service import (
    compute_briefing,
    latest_briefing,
    mark_item_done,
    send_briefing,
)

router = APIRouter(prefix="/briefing", tags=["briefing"])


def _out(b: DailyBriefing) -> BriefingOut:
    return BriefingOut(
        id=b.id,
        briefing_date=b.briefing_date.isoformat() if b.briefing_date else None,
        summary=b.summary,
        total_items=b.total_items,
        total_value=b.total_value,
        status=str(b.status),
        items=[
            BriefingItemOut(
                id=i.id,
                category=i.category,
                priority=i.priority,
                title=i.title,
                detail=i.detail,
                action=i.action,
                value=i.value,
                entity_type=i.entity_type,
                entity_id=i.entity_id,
                done=i.done,
            )
            for i in sorted(b.items, key=lambda x: (x.priority, -x.value))
        ],
    )


@router.get("", response_model=BriefingOut | None)
async def get_briefing(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> BriefingOut | None:
    """Dernier briefing du matin (tâches du jour priorisées)."""
    b = await latest_briefing(session)
    return _out(b) if b else None


@router.post("/generate", response_model=BriefingOut)
async def generate_briefing(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> BriefingOut:
    """Consolide les agents (alertes, réassort, démarque, production) en un briefing."""
    b = await compute_briefing(session, persist=True)
    await session.commit()
    return _out(b)


@router.post("/{briefing_id}/send", response_model=BriefingOut)
async def push_briefing(
    briefing_id: int,
    to: str = "demo",
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> BriefingOut:
    """Pousse le briefing sur WhatsApp/Slack (mock par défaut)."""
    b = await send_briefing(session, briefing_id, to=to)
    if b is None:
        raise NotFoundError("Briefing introuvable")
    await session.commit()
    return _out(b)


@router.post("/items/{item_id}/done", status_code=204)
async def complete_item(
    item_id: int,
    done: bool = True,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> None:
    """Coche/décoche une tâche du jour (human-in-the-loop)."""
    ok = await mark_item_done(session, item_id, done)
    if not ok:
        raise NotFoundError("Tâche introuvable")
    await session.commit()

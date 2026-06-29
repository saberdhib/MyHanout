"""Endpoints saisie de fin de journée."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.models.daily_entry import DailyEntry
from app.schemas.common import ListResponse
from app.schemas.daily_entry import DailyEntryIn, DailyEntryOut
from app.services.daily_entry_service import upsert_daily_entry

router = APIRouter(prefix="/daily-entries", tags=["daily-entries"])


@router.get("", response_model=ListResponse[DailyEntryOut])
async def list_entries(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> ListResponse[DailyEntryOut]:
    rows = list(
        (
            await session.scalars(
                select(DailyEntry).order_by(DailyEntry.entry_date.desc()).limit(200)
            )
        ).all()
    )
    items = [DailyEntryOut.model_validate(r) for r in rows]
    return ListResponse(items=items, total=len(items))


@router.post("", response_model=DailyEntryOut)
async def create_entry(
    body: DailyEntryIn,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("stocks")),
) -> DailyEntryOut:
    """Saisie/correction de fin de journée (idempotent par produit+date, audité)."""
    entry = await upsert_daily_entry(
        session,
        product_id=body.product_id,
        entry_date=body.entry_date,
        quantity_ordered=body.quantity_ordered,
        stock_remaining=body.stock_remaining,
        source=body.source,
        user_id=user.id,
    )
    return DailyEntryOut.model_validate(entry)

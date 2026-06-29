"""Service saisie de fin de journée (idempotent par produit+date) + MLOps hook.

À chaque saisie, on enregistre/met à jour l'entrée, puis on évalue l'écart
prévu/réel (boucle MLOps, cf. mlops_service).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.logging import get_logger
from app.models.base import DailyEntrySource
from app.models.daily_entry import DailyEntry

log = get_logger(__name__)


async def upsert_daily_entry(
    session: AsyncSession,
    *,
    product_id: int,
    entry_date: date,
    quantity_ordered: float,
    stock_remaining: float,
    source: DailyEntrySource = DailyEntrySource.DASHBOARD,
    user_id: int | None = None,
) -> DailyEntry:
    """Crée ou met à jour la saisie du jour (idempotent par produit+date)."""
    existing = await session.scalar(
        select(DailyEntry).where(
            DailyEntry.product_id == product_id, DailyEntry.entry_date == entry_date
        )
    )
    action = "daily_entry.update" if existing else "daily_entry.create"
    if existing:
        existing.quantity_ordered = quantity_ordered
        existing.stock_remaining = stock_remaining
        existing.source = source
        entry = existing
    else:
        entry = DailyEntry(
            product_id=product_id,
            entry_date=entry_date,
            quantity_ordered=quantity_ordered,
            stock_remaining=stock_remaining,
            source=source,
            created_by_id=user_id,
        )
        session.add(entry)
    await session.flush()

    # Boucle MLOps : mesure l'écart prévu/réel dès qu'une saisie arrive.
    from app.services.mlops_service import evaluate_entry

    await evaluate_entry(session, entry)

    await record_audit(
        session,
        action=action,
        user_id=user_id,
        resource="daily_entry",
        resource_id=entry.id,
        detail=f"product={product_id} date={entry_date} source={source.value}",
    )
    log.info("daily_entry.saved", product_id=product_id, date=str(entry_date))
    return entry

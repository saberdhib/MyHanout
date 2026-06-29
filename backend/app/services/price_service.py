"""Historique des prix : enregistrement + lecture (courbe d'évolution)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import PriceKind
from app.models.pricing import PriceHistory


async def record_price(
    session: AsyncSession,
    *,
    product_id: int,
    kind: PriceKind,
    price: float,
    source: str = "manual",
    effective_at: datetime | None = None,
) -> PriceHistory:
    """Ajoute un point de prix s'il diffère du dernier connu (évite le bruit)."""
    last = await session.scalar(
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id, PriceHistory.kind == kind)
        .order_by(PriceHistory.effective_at.desc())
        .limit(1)
    )
    if last is not None and float(last.price) == float(price):
        return last  # pas de changement → pas de doublon
    entry = PriceHistory(
        product_id=product_id,
        kind=kind,
        price=price,
        effective_at=effective_at or datetime.now(UTC),
        source=source,
    )
    session.add(entry)
    await session.flush()
    return entry


async def price_history(
    session: AsyncSession, *, product_id: int, kind: PriceKind | None = None
) -> list[PriceHistory]:
    stmt = select(PriceHistory).where(PriceHistory.product_id == product_id)
    if kind is not None:
        stmt = stmt.where(PriceHistory.kind == kind)
    stmt = stmt.order_by(PriceHistory.effective_at.asc())
    return list((await session.scalars(stmt)).all())

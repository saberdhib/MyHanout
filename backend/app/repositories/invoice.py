"""Repository factures."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.invoice import Invoice
from app.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    model = Invoice

    async def list_with_lines(self, *, limit: int = 100, offset: int = 0) -> list[Invoice]:
        result = await self.session.scalars(
            select(Invoice)
            .options(selectinload(Invoice.lines))
            .order_by(Invoice.issue_date.desc().nullslast())
            .limit(limit)
            .offset(offset)
        )
        return list(result.all())

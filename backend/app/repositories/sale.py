"""Repository ventes (sert l'historique au forecasting)."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models.sale import Sale
from app.repositories.base import BaseRepository


class SaleRepository(BaseRepository[Sale]):
    model = Sale

    async def daily_history(self, product_id: int) -> list[tuple]:
        """Renvoie [(jour, quantité totale)] trié, pour un produit donné."""
        day = func.date(Sale.sold_at)
        rows = await self.session.execute(
            select(day.label("ds"), func.sum(Sale.quantity).label("y"))
            .where(Sale.product_id == product_id)
            .group_by(day)
            .order_by(day)
        )
        return [(r.ds, float(r.y)) for r in rows.all()]

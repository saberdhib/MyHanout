"""Repository stocks."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.models.stock import Stock
from app.repositories.base import BaseRepository


class StockRepository(BaseRepository[Stock]):
    model = Stock

    async def total_quantity(self, product_id: int) -> float:
        """Quantité totale en stock pour un produit (tous lots confondus)."""
        value = await self.session.scalar(
            select(func.coalesce(func.sum(Stock.quantity), 0)).where(Stock.product_id == product_id)
        )
        return float(value or 0)

    async def list_for_product(self, product_id: int) -> list[Stock]:
        """Tous les lots de stock d'un produit (pour agrégation reco/snapshot)."""
        result = await self.session.scalars(select(Stock).where(Stock.product_id == product_id))
        return list(result.all())

    async def list_with_product(self, *, limit: int = 100, offset: int = 0) -> list[Stock]:
        result = await self.session.scalars(
            select(Stock).options(joinedload(Stock.product)).limit(limit).offset(offset)
        )
        return list(result.all())

    async def list_low_stock(self) -> list[Stock]:
        """Stocks sous le seuil de réassort."""
        result = await self.session.scalars(
            select(Stock)
            .options(joinedload(Stock.product))
            .where(Stock.quantity <= Stock.reorder_threshold)
        )
        return list(result.all())

    async def list_expiring(self, *, within_days: int = 7) -> list[Stock]:
        """Stocks périssables proches de la péremption."""
        limit_date = date.today() + timedelta(days=within_days)
        result = await self.session.scalars(
            select(Stock)
            .options(joinedload(Stock.product))
            .where(Stock.expiry_date.is_not(None), Stock.expiry_date <= limit_date)
        )
        return list(result.all())

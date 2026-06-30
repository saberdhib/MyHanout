"""Repository produits."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models.product import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    model = Product

    async def get_by_sku(self, sku: str) -> Product | None:
        return await self.session.scalar(select(Product).where(Product.sku == sku))

    async def list_all(
        self, *, family: str | None = None, search: str | None = None
    ) -> list[Product]:
        """Liste les produits (filtre optionnel par famille / recherche nom-sku)."""
        stmt = select(Product).order_by(Product.family, Product.name)
        if family:
            stmt = stmt.where(Product.family == family)
        if search:
            like = f"%{search.lower()}%"
            stmt = stmt.where(
                func.lower(Product.name).like(like) | func.lower(Product.sku).like(like)
            )
        return list((await self.session.scalars(stmt)).all())

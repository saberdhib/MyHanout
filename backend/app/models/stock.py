"""État des stocks (par produit, éventuellement par lot/péremption)."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.tenant import TenantMixin

if TYPE_CHECKING:
    from app.models.product import Product


class Stock(Base, TenantMixin, TimestampMixin):
    __tablename__ = "stock"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)

    quantity: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Seuil de réassort : déclenche une alerte STOCK_LOW.
    reorder_threshold: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    # Date de péremption du lot (nullable pour le non-périssable).
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    product: Mapped[Product] = relationship(back_populates="stocks")

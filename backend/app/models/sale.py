"""Historique des ventes (base du forecasting)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.tenant import TenantMixin

if TYPE_CHECKING:
    from app.models.product import Product


class Sale(Base, TenantMixin, TimestampMixin):
    __tablename__ = "sale"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)

    quantity: Mapped[float] = mapped_column(Numeric(10, 2))
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2))
    total: Mapped[float] = mapped_column(Numeric(12, 2))
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    # Référence ticket côté caisse (POS) : garantit l'idempotence de l'ingestion.
    external_ref: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    product: Mapped[Product] = relationship(back_populates="sales")

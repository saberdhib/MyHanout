"""Saisie de fin de journée — la donnée d'or qui nourrit le ML.

Le commerçant déclare, par produit et par jour : la quantité réellement commandée
et le stock restant en fin de journée. Idempotent par (produit, date).
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.base import DailyEntrySource
from app.models.tenant import TenantMixin

if TYPE_CHECKING:
    from app.models.product import Product


class DailyEntry(Base, TenantMixin, TimestampMixin):
    __tablename__ = "daily_entry"
    __table_args__ = (
        UniqueConstraint("product_id", "entry_date", name="uq_daily_entry_product_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    entry_date: Mapped[date] = mapped_column(Date, index=True)

    # Quantité réellement commandée ce jour-là.
    quantity_ordered: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    # Stock restant constaté en fin de journée.
    stock_remaining: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    source: Mapped[DailyEntrySource] = mapped_column(
        Enum(DailyEntrySource, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=DailyEntrySource.MANUAL,
    )
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)

    product: Mapped[Product] = relationship()

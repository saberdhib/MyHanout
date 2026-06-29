"""Fournisseurs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.invoice import Invoice
    from app.models.order import Order
    from app.models.product import Product


class Supplier(Base, TimestampMixin):
    __tablename__ = "supplier"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Délai de paiement contractuel (jours).
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30)

    products: Mapped[list[Product]] = relationship(back_populates="supplier")
    invoices: Mapped[list[Invoice]] = relationship(back_populates="supplier")
    orders: Mapped[list[Order]] = relationship(back_populates="supplier")

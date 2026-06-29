"""Fournisseurs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.tenant import TenantMixin

if TYPE_CHECKING:
    from app.models.invoice import Invoice
    from app.models.order import Order
    from app.models.product import Product


class Supplier(Base, TenantMixin, TimestampMixin):
    __tablename__ = "supplier"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Délai de paiement contractuel (jours).
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30)
    # Délai de livraison indicatif (jours) — utilisé par la suggestion de commande.
    lead_time_days: Mapped[int] = mapped_column(Integer, default=1)
    # Mode de commande préféré (whatsapp_auto | draft | record_only).
    default_order_mode: Mapped[str] = mapped_column(String(32), default="record_only")

    products: Mapped[list[Product]] = relationship(back_populates="supplier")
    invoices: Mapped[list[Invoice]] = relationship(back_populates="supplier")
    orders: Mapped[list[Order]] = relationship(back_populates="supplier")

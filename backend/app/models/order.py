"""Commandes de réassort + lignes (action sensible : human-in-the-loop)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.base import OrderStatus

if TYPE_CHECKING:
    from app.models.supplier import Supplier


class Order(Base, TimestampMixin):
    __tablename__ = "order"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("supplier.id"), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=OrderStatus.DRAFT,
    )
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    # Human-in-the-loop : une commande proposée par un agent doit être validée.
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    # Trace de l'agent ayant proposé la commande (explicabilité).
    proposed_by_agent: Mapped[str | None] = mapped_column(nullable=True)

    supplier: Mapped[Supplier | None] = relationship(back_populates="orders")
    lines: Mapped[list[OrderLine]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderLine(Base, TimestampMixin):
    __tablename__ = "order_line"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("order.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"))

    quantity: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    order: Mapped[Order] = relationship(back_populates="lines")

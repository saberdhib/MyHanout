"""Réservations client (click & collect) — le client réserve, le commerçant prépare.

Cycle human-in-the-loop : `pending` (demandée) → `confirmed` (validée) → `ready`
(prête, le client est notifié) → `collected` (récupérée) | `cancelled`. À la
récupération, les points de fidélité peuvent être crédités (si client connu).

Tenant (`TenantMixin`). Le client peut être connu (`customer_id`) ou de passage
(nom/téléphone libres).
"""

from __future__ import annotations

import enum
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.tenant import TenantMixin


class ReservationStatus(enum.StrEnum):
    PENDING = "pending"  # demandée par le client, à valider
    CONFIRMED = "confirmed"  # validée par le commerçant (dispo confirmée)
    READY = "ready"  # prête à récupérer (client notifié)
    COLLECTED = "collected"  # récupérée (clôturée)
    CANCELLED = "cancelled"


class Reservation(Base, TenantMixin, TimestampMixin):
    __tablename__ = "reservation"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customer.id"), nullable=True, index=True
    )
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(
            ReservationStatus,
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=ReservationStatus.PENDING,
        index=True,
    )
    pickup_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    # Points de fidélité crédités à la récupération (idempotence : one-shot).
    loyalty_credited: Mapped[bool] = mapped_column(default=False)

    lines: Mapped[list[ReservationLine]] = relationship(
        back_populates="reservation",
        cascade="all, delete-orphan",
        order_by="ReservationLine.id",
    )


class ReservationLine(Base, TenantMixin, TimestampMixin):
    __tablename__ = "reservation_line"

    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_id: Mapped[int] = mapped_column(ForeignKey("reservation.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(10, 2), default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    line_total: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    reservation: Mapped[Reservation] = relationship(back_populates="lines")

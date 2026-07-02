"""Support & mises à jour (Lot 3).

- `SupportTicket` / `SupportMessage` : **TENANT** (héritent de `TenantMixin`). Le commerçant
  ne voit que ses propres tickets (garde-fou) ; l'opérateur plateforme (`current_org=None`)
  les voit **tous** — même mécanisme, deux points de vue.
- `ReleaseNote` : **GLOBAL** (non tenant) — changelog produit publié par MyHanout, visible
  par tous les commerces.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.tenant import TenantMixin


class TicketStatus(enum.StrEnum):
    OPEN = "open"  # ouvert par le commerçant, à traiter
    PENDING = "pending"  # en attente d'une réponse du commerçant
    RESOLVED = "resolved"  # résolu par le support
    CLOSED = "closed"  # clôturé


class TicketPriority(enum.StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ReleaseCategory(enum.StrEnum):
    FEATURE = "feature"
    IMPROVEMENT = "improvement"
    FIX = "fix"


def _enum(e: type[enum.Enum]) -> Enum:
    return Enum(e, native_enum=False, values_callable=lambda x: [m.value for m in x])


class SupportTicket(Base, TenantMixin, TimestampMixin):
    __tablename__ = "support_ticket"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[TicketStatus] = mapped_column(
        _enum(TicketStatus), default=TicketStatus.OPEN, index=True
    )
    priority: Mapped[TicketPriority] = mapped_column(
        _enum(TicketPriority), default=TicketPriority.NORMAL
    )
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    # Opérateur plateforme assigné (user_id d'un PlatformAdmin), nullable.
    assigned_admin_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)

    messages: Mapped[list[SupportMessage]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="SupportMessage.id",
    )


class SupportMessage(Base, TenantMixin, TimestampMixin):
    __tablename__ = "support_message"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("support_ticket.id"), index=True)
    author_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    # « merchant » (le commerçant) ou « platform » (le support MyHanout).
    author_kind: Mapped[str] = mapped_column(String(16), default="merchant")
    body: Mapped[str] = mapped_column(Text)

    ticket: Mapped[SupportTicket] = relationship(back_populates="messages")


class ReleaseNote(Base, TimestampMixin):
    """Note de version (changelog produit). Globale : publiée par MyHanout."""

    __tablename__ = "release_note"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[ReleaseCategory] = mapped_column(
        _enum(ReleaseCategory), default=ReleaseCategory.FEATURE
    )
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)

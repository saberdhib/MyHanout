"""Événements métier / alertes (ruptures, péremptions, échéances...)."""

from __future__ import annotations

from sqlalchemy import Boolean, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.base import EventType


class Event(Base, TimestampMixin):
    __tablename__ = "event"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[EventType] = mapped_column(
        Enum(EventType, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        index=True,
    )
    severity: Mapped[str] = mapped_column(String(16), default="info")  # info|warning|critical
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Référence générique vers l'entité concernée.
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Payload JSON sérialisé (détails de l'alerte).
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)

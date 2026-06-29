"""État de conversation WhatsApp persisté (machine à états multi-messages)."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversation"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Numéro de téléphone WhatsApp du commerçant (identifiant de session).
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    # État courant : idle | awaiting_order_confirmation | ...
    state: Mapped[str] = mapped_column(String(48), default="idle")
    # Contexte sérialisé (JSON) : suggestion en cours, lignes ajustées, etc.
    context: Mapped[str | None] = mapped_column(Text, nullable=True)

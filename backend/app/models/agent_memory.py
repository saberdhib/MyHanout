"""Mémoire d'agent : historique de tours conversationnels (tenant-scopé).

Permet à un agent de se souvenir des échanges récents avec un interlocuteur
(par `subject` : téléphone WhatsApp, user, etc.), au sein d'une organisation.
"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.tenant import TenantMixin


class AgentMemory(Base, TenantMixin, TimestampMixin):
    __tablename__ = "agent_memory"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent: Mapped[str] = mapped_column(String(64), index=True)
    # Interlocuteur (numéro WhatsApp, id user, ...).
    subject: Mapped[str] = mapped_column(String(128), index=True)
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
